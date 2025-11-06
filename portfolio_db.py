# File: portfolio_db.py
# --- UPDATED ---

import sqlite3
import datetime

DATABASE_NAME = "virtual_portfolio.db"
INITIAL_CASH = 100000.00

def initialize_database():
    """Sets up the SQLite database and tables if they don't exist."""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Account (
            id INTEGER PRIMARY KEY,
            cash_balance REAL NOT NULL
        )
    """)
    
    cursor.execute("SELECT COUNT(*) FROM Account")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO Account (id, cash_balance) VALUES (?, ?)", (1, INITIAL_CASH))

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Holdings (
            symbol TEXT PRIMARY KEY,
            quantity REAL NOT NULL,
            average_price REAL NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            type TEXT NOT NULL, 
            quantity REAL NOT NULL,
            price REAL NOT NULL,
            timestamp TEXT NOT NULL
        )
    """)
    
    # --- NEW TABLE FOR WATCHLIST ---
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Watchlist (
            symbol TEXT PRIMARY KEY
        )
    """)

    conn.commit()
    conn.close()

def get_cash_balance():
    """Retrieves the current virtual cash balance."""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT cash_balance FROM Account WHERE id = 1")
    balance = cursor.fetchone()[0]
    conn.close()
    return balance

def update_cash_balance(amount):
    """Adds (or subtracts) a value to the cash balance."""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE Account SET cash_balance = cash_balance + ? WHERE id = 1", (amount,))
    conn.commit()
    conn.close()

def add_virtual_cash(amount):
    """Adds a positive amount of cash to the account (e.g., 'Add Funds')."""
    if amount <= 0:
        return False, "Amount must be positive."
    update_cash_balance(amount)
    log_transaction("CASH", "DEPOSIT", 1, amount)
    return True, f"Successfully added ${amount:,.2f}."

def log_transaction(symbol, type, quantity, price):
    """Records any transaction in the history table."""
    timestamp = datetime.datetime.now().isoformat()
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO Transactions (symbol, type, quantity, price, timestamp) 
        VALUES (?, ?, ?, ?, ?)
    """, (symbol, type, quantity, price, timestamp))
    conn.commit()
    conn.close()

def get_holdings():
    """Retrieves all current stock holdings."""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT symbol, quantity, average_price FROM Holdings")
    holdings = [{"symbol": r[0], "quantity": r[1], "avg_price": r[2]} for r in cursor.fetchall()]
    conn.close()
    return holdings

def get_transactions():
    """Retrieves all historical transactions."""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT symbol, type, quantity, price, timestamp FROM Transactions ORDER BY id DESC")
    transactions = [{"symbol": r[0], "type": r[1], "quantity": r[2], "price": r[3], "timestamp": r[4]} for r in cursor.fetchall()]
    conn.close()
    return transactions

def update_holding(symbol, quantity_change, price):
    """Updates stock holdings based on a trade. Handles Buy, Sell, and avg. price calc."""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT quantity, average_price FROM Holdings WHERE symbol = ?", (symbol,))
    result = cursor.fetchone()

    if result:
        current_qty, current_avg_price = result
        new_qty = current_qty + quantity_change
        if new_qty < 0:
            conn.close()
            raise ValueError(f"Insufficient quantity to sell. You only have {current_qty}.")
        if quantity_change > 0:
            total_cost_old = current_qty * current_avg_price
            cost_new_shares = quantity_change * price
            new_avg_price = (total_cost_old + cost_new_shares) / new_qty
        elif new_qty == 0:
            new_avg_price = 0
        else:
            new_avg_price = current_avg_price
        if new_qty > 0:
            cursor.execute("UPDATE Holdings SET quantity = ?, average_price = ? WHERE symbol = ?", (new_qty, new_avg_price, symbol))
        else:
            cursor.execute("DELETE FROM Holdings WHERE symbol = ?", (symbol,))
    elif quantity_change > 0:
        cursor.execute("INSERT INTO Holdings (symbol, quantity, average_price) VALUES (?, ?, ?)", (symbol, quantity_change, price))
    else:
        conn.close()
        raise ValueError(f"Cannot sell {symbol}. You do not own this stock.")
    conn.commit()
    conn.close()

# --- NEW WATCHLIST FUNCTIONS ---

def get_watchlist():
    """Retrieves all symbols from the watchlist."""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT symbol FROM Watchlist ORDER BY symbol")
    symbols = [r[0] for r in cursor.fetchall()]
    conn.close()
    return symbols

def add_to_watchlist(symbol):
    """Adds a new symbol to the watchlist, ignoring duplicates."""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    # "INSERT OR IGNORE" prevents crashes on duplicate entries
    cursor.execute("INSERT OR IGNORE INTO Watchlist (symbol) VALUES (?)", (symbol,))
    conn.commit()
    conn.close()

def remove_from_watchlist(symbol):
    """Removes a symbol from the watchlist."""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM Watchlist WHERE symbol = ?", (symbol,))
    conn.commit()
    conn.close()