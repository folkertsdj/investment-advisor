import sqlite3
import os

def migrate():
    """
    Migrates stock data from stocks.txt to a new SQLite database.
    """
    db_file = 'portfolio.db'
    txt_file = 'stocks.txt'

    script_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(script_dir, db_file)
    txt_path = os.path.join(script_dir, txt_file)

    # Connect to SQLite database (creates the file if it doesn't exist)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create the stocks table if it doesn't exist
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS stocks (
            symbol TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            quantity REAL NOT NULL
        )
    ''')
    print("Table 'stocks' created or already exists.")

    # Read from stocks.txt and insert into the database
    try:
        with open(txt_path, 'r') as f:
            for line in f:
                parts = line.strip().split(',')
                if len(parts) >= 3:
                    symbol = parts[0]
                    name = parts[1]
                    quantity = float(parts[2])

                    # Use INSERT OR IGNORE to avoid errors on duplicate primary keys if run multiple times
                    cursor.execute("INSERT OR IGNORE INTO stocks (symbol, name, quantity) VALUES (?, ?, ?)",
                                   (symbol, name, quantity))

        conn.commit()
        print(f"Data successfully migrated from {txt_file} to {db_file}.")

    except FileNotFoundError:
        print(f"Error: {txt_file} not found. No data to migrate.")
    except Exception as e:
        print(f"An error occurred during migration: {e}")
        conn.rollback()

    finally:
        conn.close()
        print("Database connection closed.")

if __name__ == '__main__':
    migrate()
