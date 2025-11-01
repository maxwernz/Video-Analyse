import pandas as pd
import sqlite3

# Load data from Excel/CSV
file_path = '/Users/max/Downloads/Stat Turnier Schriesheim/Vorlage-Tabelle 1.csv'  # Update with the path to your exported file
data = pd.read_csv(file_path)  # Use `pd.read_csv(file_path)` if it's a CSV
# Connect to SQLite database (or create it if it doesn’t exist)
db_path = 'user_data.db'
conn = sqlite3.connect(db_path)

# Create a table and insert data (table name here is 'csv_data')
data.to_sql('csv_data', conn, if_exists='replace', index=False)

# Commit and close the connection
conn.commit()
conn.close()

print("Data successfully stored in the database.")