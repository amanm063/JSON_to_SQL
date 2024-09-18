import streamlit as st
from streamlit_extras.app_logo import add_logo
from streamlit_extras.colored_header import colored_header
from streamlit_extras.stoggle import stoggle
from streamlit_extras.let_it_rain import rain
import json
import sqlite3
import pandas as pd
import re
from io import StringIO
import tempfile
import os
import time
import random

# Set page config
st.set_page_config(page_title="JSON to SQLite Converter", page_icon="🔄", layout="wide")

# Function to generate random dark color
def random_dark_color():
    return "#{:02x}{:02x}{:02x}".format(random.randint(0, 100), random.randint(0, 100), random.randint(0, 100))

# Function to set dynamic dark background
def set_dynamic_dark_background():
    color1 = random_dark_color()
    color2 = random_dark_color()
    st.markdown(
        f"""
        <style>
        .stApp {{
            background: linear-gradient(to right, {color1}, {color2});
            transition: background 1s ease;
        }}
        </style>
        """,
        unsafe_allow_html=True
    )

# Custom CSS
st.markdown("""
<style>
    .stButton>button {
        background-color: #4CAF50;
        color: white;
    }
    .stCheckbox {
        color: white;
    }
    .stDataFrame {
        background-color: rgba(255, 255, 255, 0.1);
    }
    .stMarkdown {
        color: white;
    }
    .stSelectbox {
        color: white;
    }
</style>
""", unsafe_allow_html=True)

# Set initial background
set_dynamic_dark_background()

# Function to change background color
def change_background():
    set_dynamic_dark_background()
    st.rerun()

def sanitize_identifier(identifier):
    return re.sub(r'\W+', '_', identifier)

def create_tables_from_json(json_data, conn):
    cursor = conn.cursor()
    
    def create_table(table_name, columns):
        if not columns:
            return False

        columns_sql = [f'"{sanitize_identifier(col)}" {dtype}' for col, dtype in columns.items()]
        columns_sql.append("created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
        
        query = f'CREATE TABLE IF NOT EXISTS "{sanitize_identifier(table_name)}" ({", ".join(columns_sql)})'
        cursor.execute(query)
        return True

    def process_json_for_tables(data, table_name):
        if isinstance(data, list):
            if data and isinstance(data[0], dict):
                process_json_for_tables(data[0], table_name)
        elif isinstance(data, dict):
            columns = {k: get_sqlite_type(v) for k, v in data.items() if not isinstance(v, (dict, list))}
            create_table(table_name, columns)
            
            for key, value in data.items():
                new_table_name = f"{table_name}_{key}"
                if isinstance(value, (dict, list)):
                    process_json_for_tables(value, new_table_name)
    
    def get_sqlite_type(value):
        if isinstance(value, bool):
            return "BOOLEAN"
        elif isinstance(value, int):
            return "INTEGER"
        elif isinstance(value, float):
            return "REAL"
        else:
            return "TEXT"
    
    process_json_for_tables(json_data, "table")
    conn.commit()

def insert_data_from_json(json_data, conn):
    cursor = conn.cursor()
    
    def insert_data(table_name, data):
        columns = [col for col in data.keys() if not isinstance(data[col], (dict, list))]
        values = [data[col] for col in columns]
        
        if not columns:
            return None
        
        placeholders = ', '.join(['?' for _ in range(len(values))])
        sanitized_columns = [f'"{sanitize_identifier(col)}"' for col in columns]
        query = f'INSERT INTO "{sanitize_identifier(table_name)}" ({", ".join(sanitized_columns)}) VALUES ({placeholders})'
        
        try:
            cursor.execute(query, values)
            conn.commit()
            return cursor.lastrowid
        except sqlite3.Error as e:
            st.error(f"Error inserting data into {table_name}: {e}")
            return None

    def process_json(data, table_name):
        if isinstance(data, list):
            for item in data:
                process_json(item, table_name)
        elif isinstance(data, dict):
            new_id = insert_data(table_name, data)
            
            for key, value in data.items():
                new_table_name = f"{table_name}_{key}"
                if isinstance(value, (dict, list)):
                    process_json(value, new_table_name)
    
    process_json(json_data, "table")
    conn.commit()

def get_tables(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    return [table[0] for table in cursor.fetchall()]

def get_table_schema(conn, table_name):
    cursor = conn.cursor()
    cursor.execute(f'PRAGMA table_info("{sanitize_identifier(table_name)}");')
    return cursor.fetchall()

def get_table_data(conn, table_name, limit=100):
    cursor = conn.cursor()
    cursor.execute(f'SELECT * FROM "{sanitize_identifier(table_name)}" LIMIT {limit};')
    return cursor.fetchall()

def main():
    # Sidebar
    with st.sidebar:
        st.title("About")
        st.info("This app converts JSON to SQLite and allows you to explore the data.")
        st.title("Important")
        st.info("Please convert the app in dark mode for the best experience. I made it for dark mode only. You can change  it from the top right settings")
        st.subheader("Connect with me")
        cols = st.columns(3)
        cols[0].markdown("[![Github](https://img.icons8.com/material-outlined/48/000000/github.png)](https://github.com/amanm063)")
        cols[1].markdown("[![LinkedIn](https://img.icons8.com/color/48/000000/linkedin.png)](https://www.linkedin.com/in/amanmalik063/)")
        cols[2].markdown("[![Instagram](https://img.icons8.com/fluent/48/000000/instagram-new.png)](https://www.instagram.com/aman_mallk/)")
        
        if st.button("Change Background"):
            change_background()

    # Main content
    colored_header(label="JSON to SQLite Converter", description="Upload your JSON file and explore the data", color_name="light-blue-70")

    uploaded_file = st.file_uploader("Choose a JSON file", type="json")
    if uploaded_file is not None:
        # Read the file
        stringio = StringIO(uploaded_file.getvalue().decode("utf-8"))
        json_data = json.load(stringio)

        # Create a temporary file for the SQLite database
        temp_db_file = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        temp_db_file.close()
        conn = sqlite3.connect(temp_db_file.name)

        # Process the JSON data
        with st.spinner('Processing JSON data...'):
            create_tables_from_json(json_data, conn)
            insert_data_from_json(json_data, conn)
            time.sleep(1)  # Simulate longer processing time
        st.success("JSON data processed successfully!")
        rain(emoji="🎉", font_size=54, falling_speed=10, animation_length=0.7)

        # Get all tables
        tables = get_tables(conn)

        # Create checkboxes for table selection
        st.subheader("Select tables to view:")
        cols = st.columns(3)
        selected_tables = []
        for i, table in enumerate(tables):
            if cols[i % 3].checkbox(table, key=f"table_{i}"):
                selected_tables.append(table)

        # Display selected tables
        for table in selected_tables:
            colored_header(label=f"Table: {table}", description="", color_name="blue-green-70")

            # Display schema
            stoggle("Show Schema", f"""
            ```python
            {pd.DataFrame(get_table_schema(conn, table), columns=['ID', 'Name', 'Type', 'NotNull', 'DefaultValue', 'PK'])}
            ```
            """)

            # Display data
            st.write(f"Data (limited to 100 rows):")
            data = get_table_data(conn, table)
            if data:
                columns = [column[1] for column in get_table_schema(conn, table)]
                data_df = pd.DataFrame(data, columns=columns)
                st.dataframe(data_df, use_container_width=True)
            else:
                st.info("No data in this table.")

        # Provide download link for the SQLite database
        with open(temp_db_file.name, "rb") as file:
            btn = st.download_button(
                label="Download SQLite Database",
                data=file,
                file_name="json_to_sqlite.db",
                mime="application/octet-stream"
            )

        conn.close()
        os.unlink(temp_db_file.name)  # Delete the temporary file

if __name__ == "__main__":
    main()