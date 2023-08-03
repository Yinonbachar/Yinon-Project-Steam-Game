import os
import pandas as pd
from flask import Flask, render_template, request, redirect

app = Flask(__name__)

PAGE_SIZE = 20
uploaded_tables = {}  # Dictionary to store uploaded tables
table_path = os.path.expanduser("~/SteamGameFinal.csv")  # Set the initial table path


def load_table(table_name=None):
    """
    Load the table data from the CSV file or retrieve the uploaded table from the dictionary.

    :param table_name: The name of the uploaded table to retrieve (optional).
    :type table_name: str
    :return: The loaded or uploaded table data as a pandas DataFrame.
    :rtype: pd.DataFrame
    """
    global uploaded_tables
    try:
        if table_name:
            table_data = uploaded_tables[table_name]
        else:
            table_data = pd.read_csv(table_path)

        table_data.insert(0, 'ID', range(1, len(table_data) + 1))  # Add an ID column starting from 1
    except FileNotFoundError:
        table_data = pd.DataFrame()

    return table_data


def update_table(file):
    """
    Update the table with data from the uploaded CSV file.

    :param file: The uploaded CSV file.
    :type file: werkzeug.datastructures.FileStorage
    :return: The name of the uploaded table.
    :rtype: str
    """
    global uploaded_tables

    if file.filename.endswith('.csv'):
        new_data = pd.read_csv(file)
        new_data.insert(0, 'ID', range(1, len(new_data) + 1))  # Add an ID column starting from 1

        # Generate a unique name for the uploaded table
        table_name = f"table_{len(uploaded_tables) + 1}"
        uploaded_tables[table_name] = new_data.copy()  # Store the uploaded table in the dictionary

        return table_name


def format_number(x):
    """
    Format a numeric value as a string with two decimal places, if applicable.

    :param x: The input numeric value.
    :type x: int or float
    :return: The formatted numeric value as a string.
    :rtype: str
    """
    if isinstance(x, (int, float)):
        return f'{x:.2f}' if (x * 100) % 100 != 0 else f'{x:.0f}'
    return x


def clean_data(table_data):
    """
    Clean the numeric columns in the table_data by formatting them with two decimal places.

    :param table_data: The table data as a pandas DataFrame.
    :type table_data: pd.DataFrame
    :return: The cleaned table data.
    :rtype: pd.DataFrame
    """
    for col in table_data.columns:
        if pd.api.types.is_numeric_dtype(table_data[col]):
            table_data[col] = table_data[col].apply(format_number)
    return table_data


def paginate_table(table_data, page):
    """
    Paginate the table_data based on the given page number.

    :param table_data: The table data as a pandas DataFrame.
    :type table_data: pd.DataFrame
    :param page: The page number.
    :type page: int
    :return: The paginated table data.
    :rtype: pd.DataFrame
    """
    start_row = PAGE_SIZE * (page - 1)
    end_row = PAGE_SIZE * page
    return table_data.iloc[start_row:end_row]


def get_page_range(num_pages, page):
    """
    Get the range of page numbers to display in the pagination section.

    :param num_pages: The total number of pages.
    :type num_pages: int
    :param page: The current page number.
    :type page: int
    :return: The range of page numbers.
    :rtype: range
    """
    return range(max(1, page - 5), min(num_pages, page + 5) + 1)


@app.route('/')
def index():
    """
    Handle the main page request.

    :return: The rendered HTML template with the table data and pagination.
    :rtype: str
    """
    # Get the table name from the query string
    table_name = request.args.get('table')
    global uploaded_tables
    table_data = uploaded_tables.get(table_name) if table_name else load_table()

    # Clean the data to format numeric columns
    table_data_cleaned = clean_data(table_data)

    # Get the search term from the query string
    search_term = request.args.get('search', '')

    # Get all the column names
    columns = table_data_cleaned.columns.tolist()

    # Check if the user selected "All Columns"
    all_columns_selected = request.args.get('column', '') == 'select_all'
    selected_columns_value = request.args.get('selected_columns', '')  # Get the value of the selected_columns parameter

    # Initialize selected_columns with an empty list
    selected_columns = []

    # Check if "Select All" is selected and add all columns to selected_columns
    if all_columns_selected:
        selected_columns = columns
    else:
        # Get the list of selected columns
        selected_columns = request.args.getlist('column')

    # Filter the table_data based on the search_term and selected_columns
    table_data_filtered = table_data_cleaned
    if search_term:
        if all_columns_selected and search_term:
            filtered_rows = []
            for _, row in table_data_cleaned.iterrows():
                if any(search_term.lower() in str(cell).lower() for cell in row):
                    filtered_rows.append(row)
            table_data_filtered = pd.DataFrame(filtered_rows, columns=table_data_cleaned.columns)
        elif selected_columns:
            for col in selected_columns:
                if col in table_data_cleaned.columns:
                    table_data_filtered = table_data_filtered[
                        table_data_filtered[col].apply(lambda cell: search_term.lower() in str(cell).lower())
                    ]

    # Calculate the total number of rows and the number of pages for pagination
    total_rows = table_data_filtered.shape[0]
    num_pages = (total_rows + PAGE_SIZE - 1) // PAGE_SIZE
    page = int(request.args.get('page', 1))

    # Apply pagination to the filtered data
    table_data_paginated = paginate_table(table_data_filtered, page)

    # Calculate the range of page numbers to display in the pagination section
    page_range = get_page_range(num_pages, page)

    return render_template(
        'index.html',
        table_data=table_data_paginated,
        columns=columns,
        page=page,
        num_pages=num_pages,
        page_range=page_range,
        num_rows=total_rows,  # Pass the total number of rows to the template
        search_term=search_term,
        selected_columns=selected_columns,
        all_columns_selected=all_columns_selected,
        selected_columns_value=selected_columns_value  # Pass the value of selected_columns to the template
    )


@app.route('/upload', methods=['POST'])
def upload():
    """
    Handle the file upload request.

    :return: Redirect to the main page with the uploaded table or back to the main page if no file was uploaded.
    :rtype: werkzeug.wrappers.response.Response
    """
    file = request.files['csv_file']
    if file:
        # Update the table with the uploaded file
        table_name = update_table(file)
        # Redirect to the main page with the uploaded table
        return redirect(f'/?table={table_name}')
    # If no file was uploaded or there was an error, redirect to the main page
    return redirect('/')


@app.route('/restore_original', methods=['POST'])
def restore_original():
    """
    Handle the request to restore the original table data.

    :return: Redirect to the main page with the original table data.
    :rtype: werkzeug.wrappers.response.Response
    """
    global uploaded_tables
    # Load the original table_data from the CSV file
    table_data = load_table()
    uploaded_tables.clear()  # Clear all the uploaded tables
    return redirect('/')


if __name__ == '__main__':
    app.run()
