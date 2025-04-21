import streamlit as st
import pandas as pd
import pyodbc
import numpy as np

# App title
st.title("Excel to SQL Uploader")

# Sidebar: SQL Server Connection
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

def insert_data(df, table_name):
    df.replace("", np.nan, inplace=True)
    df = df.where(pd.notnull(df), None)
    conn = get_connection()
    cursor = conn.cursor()
    for index, row in df.iterrows():
        try:
            placeholders = ', '.join(['?'] * len(row))
            sql = f"INSERT INTO [{table_name}] VALUES ({placeholders})"
            cursor.execute(sql, tuple(row))
        except Exception as e:
            st.error(f"Error inserting row {index + 1}: {e}")
            continue
    conn.commit()
    cursor.close()

# Select mode
mode = st.radio("Select mode", ["Fast Mode", "Standard Mode"])

# Upload Excel file
uploaded_file = st.file_uploader("Upload Excel file", type=["xlsx"])

if uploaded_file:
    xl = pd.ExcelFile(uploaded_file)
    sheet_name = xl.sheet_names[0] if mode == "Fast Mode" else st.selectbox("Select sheet", xl.sheet_names)
    df = xl.parse(sheet_name)

    # Display rows/columns
    st.write(f" Rows: {df.shape[0]} | Columns: {df.shape[1]}")
    st.dataframe(df)

    # Table name input
    default_table = uploaded_file.name.replace(".xlsx", "").replace(" ", "_")
    table_name = st.text_input("Enter table name", default_table)

    # Upload button
    if st.button("Upload to SQL Server"):
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(f"IF OBJECT_ID(N'{table_name}', N'U') IS NULL BEGIN EXEC('CREATE TABLE {table_name} (ID INT)') END")
            conn.commit()
            cursor.close()

            insert_data(df, table_name)
            st.success(f" Data uploaded to table `{table_name}` successfully!")
        except Exception as e:
            st.error(f" Error uploading data: {e}")