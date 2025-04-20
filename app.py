import streamlit as st
import pandas as pd
import pyodbc
import datetime
import numpy as np

# Get connection details from user input
st.sidebar.header("SQL Server Connection")
use_windows_auth = st.sidebar.checkbox("Use Windows Authentication")
DB_SERVER = st.sidebar.text_input("Server")
DB_DATABASE = st.sidebar.text_input("Database")

if not use_windows_auth:
    DB_USERNAME = st.sidebar.text_input("Username")
    DB_PASSWORD = st.sidebar.text_input("Password", type="password")
else:
    DB_USERNAME = ""
    DB_PASSWORD = ""

# SQL Server connection
@st.cache_resource
def get_connection():
    if use_windows_auth:
        conn_str = (
            f"DRIVER={{ODBC Driver 17 for SQL Server}};"
            f"SERVER={DB_SERVER};DATABASE={DB_DATABASE};Trusted_Connection=yes;"
        )
    else:
        conn_str = (
            f"DRIVER={{ODBC Driver 17 for SQL Server}};"
            f"SERVER={DB_SERVER};DATABASE={DB_DATABASE};"
            f"UID={DB_USERNAME};PWD={DB_PASSWORD}"
        )
    return pyodbc.connect(conn_str)

# Retrieve existing tables
def get_existing_tables():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE='BASE TABLE'")
    tables = [row[0] for row in cursor.fetchall()]
    cursor.close()
    return tables

# Map pandas dtypes to SQL types
def map_dtype_to_sql(dtype):
    if pd.api.types.is_integer_dtype(dtype):
        return "INT"
    elif pd.api.types.is_float_dtype(dtype):
        return "FLOAT"
    elif pd.api.types.is_bool_dtype(dtype):
        return "BIT"
    elif pd.api.types.is_datetime64_any_dtype(dtype):
        return "DATETIME"
    else:
        return "VARCHAR(255)"

# Create SQL table from DataFrame
def create_table_from_df(df, table_name):
    columns_sql = ",\n".join([
        f"[{col}] {map_dtype_to_sql(dtype)}"
        for col, dtype in df.dtypes.items()
    ])
    create_sql = f"CREATE TABLE [{table_name}] (\n{columns_sql}\n);"
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(create_sql)
    conn.commit()
    cursor.close()

# Insert data into SQL table
def insert_data(df, table_name):
    # Replace empty strings with NaN
    df.replace("", np.nan, inplace=True)

    # Automatically detect float columns and clean them
    float_cols = df.select_dtypes(include=["float", "int"]).columns
    for col in float_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # Replace NaN with None
    df = df.where(pd.notnull(df), None)

    conn = get_connection()
    cursor = conn.cursor()
    for index, row in df.iterrows():
        try:
            placeholders = ', '.join(['?'] * len(row))
            sql = f"INSERT INTO [{table_name}] VALUES ({placeholders})"
            cursor.execute(sql, tuple(row))
        except Exception as e:
            st.error(f"Error inserting row {index + 1}: {e}\nRow content: {row.to_dict()}")
            raise e
    conn.commit()
    cursor.close()

# Validate schema against existing table
def validate_schema_match(df, table_name):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(f"SELECT COLUMN_NAME, DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = '{table_name}'")
    sql_columns = cursor.fetchall()
    sql_types = {col[0]: col[1].upper() for col in sql_columns}
    for col in df.columns:
        expected_sql_type = sql_types.get(col)
        actual_type = map_dtype_to_sql(df[col].dtype)
        if expected_sql_type and expected_sql_type not in actual_type:
            return False, f"Type mismatch for column '{col}': SQL={expected_sql_type}, Excel={actual_type}"
    return True, "Schema matches"

# Streamlit UI
st.title(":floppy_disk: Upload Excel to SQL Server")

mode = st.radio("Select mode", ["Standard Mode", "Fast Mode"])

uploaded_file = st.file_uploader("Upload Excel file", type=["xlsx"])

df = None

if uploaded_file:
    xl = pd.ExcelFile(uploaded_file)
    sheet_name = xl.sheet_names[0] if mode == "Fast Mode" else st.selectbox("Select sheet", xl.sheet_names)
    df = xl.parse(sheet_name)
    st.success("Excel loaded successfully")

    st.write(f"**Rows:** {df.shape[0]} | **Columns:** {df.shape[1]}")
    st.dataframe(df)

    default_table = uploaded_file.name.replace(".xlsx", "").replace(" ", "_")
    table_name = st.text_input("Enter table name", default_table)

    if st.button("Confirm and Upload to SQL Server"):
        existing_tables = get_existing_tables()

        if table_name in existing_tables and mode != "Fast Mode":
            st.warning(f"Table {table_name} already exists")
            action = st.radio("Select action", ["Drop and recreate the existing table", "Cancel"])
            if action == "Drop and recreate the existing table":
                conn = get_connection()
                cursor = conn.cursor()
                cursor.execute(f"DROP TABLE IF EXISTS [{table_name}]")
                conn.commit()
                cursor.close()
            else:
                st.stop()

        elif table_name in existing_tables and mode == "Fast Mode":
            st.stop()

        if table_name not in existing_tables:
            try:
                create_table_from_df(df, table_name)
                st.success("Table created successfully")
            except Exception as e:
                st.error(f"Error creating table: {e}")
                st.stop()

        if table_name in existing_tables:
            valid, msg = validate_schema_match(df, table_name)
            if not valid:
                st.error(msg)
                st.stop()

        try:
            insert_data(df, table_name)
            st.success(f"{len(df)} rows loaded into table {table_name}")
        except Exception as e:
            st.error(f"Error inserting data: {e}")
