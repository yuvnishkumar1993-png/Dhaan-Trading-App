import sqlite3
import pandas as pd
import logging

logging.basicConfig(
    filename='app_errors.log',
    level=logging.ERROR,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

DB_NAME = "dhan_platform.db"

def init_db():
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS watchlist (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id TEXT,
                symbol TEXT UNIQUE
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS trading_journal (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id TEXT,
                trade_date TEXT,
                stock_name TEXT,
                trade_type TEXT,
                notes TEXT
            )
        ''')
        conn.commit()
        conn.close()
    except Exception as e:
        logging.error(f"Database Init Error: {str(e)}")

def add_to_watchlist(client_id, symbol):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT OR IGNORE INTO watchlist (client_id, symbol) VALUES (?, ?)", (client_id, symbol.upper()))
        conn.commit()
        success = True
    except Exception as e:
        logging.error(f"Add Watchlist Error: {str(e)}")
        success = False
    conn.close()
    return success

def get_watchlist(client_id):
    try:
        conn = sqlite3.connect(DB_NAME)
        df = pd.read_sql_query("SELECT symbol FROM watchlist WHERE client_id = ?", conn, params=(client_id,))
        conn.close()
        return df['symbol'].tolist()
    except Exception as e:
        logging.error(f"Get Watchlist Error: {str(e)}")
        return []

def save_journal_entry(client_id, trade_date, stock_name, trade_type, notes):
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO trading_journal (client_id, trade_date, stock_name, trade_type, notes)
            VALUES (?, ?, ?, ?, ?)
        ''', (client_id, str(trade_date), stock_name.upper(), trade_type, notes))
        conn.commit()
        conn.close()
    except Exception as e:
        logging.error(f"Save Journal Error: {str(e)}")

def get_journal_entries(client_id):
    try:
        conn = sqlite3.connect(DB_NAME)
        df = pd.read_sql_query("SELECT trade_date, stock_name, trade_type, notes FROM trading_journal WHERE client_id = ?", conn, params=(client_id,))
        conn.close()
        return df
    except Exception as e:
        logging.error(f"Get Journal Error: {str(e)}")
        return pd.DataFrame()
