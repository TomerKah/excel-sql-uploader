import streamlit as st
import pandas as pd
import pyodbc
import numpy as np

st.title("Upload Excel to SQL Server")

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

uploaded_file = st.file_uploader("Upload Excel file", type=["xlsx"])
if uploaded_file:
    df = pd.read_excel(uploaded_file)
    st.dataframe(df)
    table_name = st.text_input("Enter table name", uploaded_file.name.replace(".xlsx", ""))
    if st.button("Upload to SQL Server"):
        insert_data(df, table_name)
        st.success("Data uploaded successfully")
