# File: market_data.py
# --- COMPLETE COMBINED CODE ---

import yfinance as yf
import pandas as pd
import csv
import sys  # Required for PyInstaller fix
import os   # Required for PyInstaller fix

# --- HELPER FUNCTION for PyInstaller ---
def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        # _MEIPASS not set, so we're in normal dev mode
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)
# --- END OF HELPER FUNCTION ---

def load_symbol_map(nse_file="nse_stocks.csv"):
    """
    Loads all stock symbols AND company names from the NSE CSV file.
    """
    symbol_map = {}
    
    # Use the helper function to find the file
    file_path_to_csv = resource_path(nse_file)
    
    try:
        # Use the new file_path_to_csv variable
        with open(file_path_to_csv, mode='r', encoding='utf-8') as file:
            reader = csv.reader(file)
            header = next(reader)
            symbol_col = header.index("SYMBOL")
            name_col = header.index("NAME OF COMPANY")
            
            for row in reader:
                try:
                    symbol = row[symbol_col].strip()
                    name = row[name_col].strip()
                    if symbol and name:
                        symbol_map[name] = f"{symbol}.NS"
                except IndexError:
                    continue
        print(f"Loaded {len(symbol_map)} symbols and names for auto-complete.")
        return symbol_map
        
    except FileNotFoundError:
        print(f"CRITICAL ERROR: {file_path_to_csv} not found. Auto-complete will not work.")
        print("Please make sure 'nse_stocks.csv' is in the same folder as main.py before building.")
        return {}
    except ValueError:
        print("CRITICAL ERROR: CSV file is missing 'SYMBOL' or 'NAME OF COMPANY' header.")
        return {}
    except Exception as e:
        print(f"Error loading symbols: {e}")
        return {}

def _clean_live_data(data):
    """
    Cleans incoming yfinance data to handle all known formats.
    """
    if data is None or data.empty:
        return None
        
    # 1. Flatten MultiIndex (tuple) columns if they exist
    if isinstance(data.columns, pd.MultiIndex):
        new_cols = []
        for col in data.columns:
            new_cols.append(col[0] if isinstance(col, tuple) else col)
        data.columns = new_cols
    
    # 2. Normalize all column names to lowercase strings
    data.columns = [str(col).lower() for col in data.columns]

    # 3. Rename to the format we need (TitleCase)
    rename_map = {'close': 'Close'}
    data = data.rename(columns=rename_map)

    # 4. Check if 'Close' column exists
    if 'Close' not in data.columns:
        return None
        
    # 5. Convert 'Close' to numeric
    data['Close'] = pd.to_numeric(data['Close'], errors='coerce')
    data = data.dropna(subset=['Close'])
    
    return data

def get_live_quote(symbol):
    """
    Fetches the live quote for a given stock symbol using yfinance.
    More robustly handles edge cases where < 2 days of data are returned.
    """
    try:
        data = yf.download(tickers=symbol, period="2d", interval="1d")
        
        # Clean the data first
        clean_data = _clean_live_data(data)
        
        if clean_data is not None and len(clean_data) >= 2:
            price = clean_data['Close'].iloc[-1]
            prev_close = clean_data['Close'].iloc[-2]
            change = price - prev_close
            
            return {
                "symbol": symbol,
                "price": float(price),
                "change": float(change)
            }
        
        # If < 2 rows, the iloc[-2] will fail.
        # So, we force the fallback method.
        raise Exception("Insufficient data from download, using fallback.")

    except Exception as e:
        # This 'except' block is our primary fallback
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            price = info.get('currentPrice') or info.get('regularMarketPrice')
            prev_close = info.get('previousClose')
            
            if price is None or prev_close is None:
                print(f"Error for {symbol}: Could not find price data in info dict.")
                return None
            
            change = price - prev_close
            return {
                "symbol": symbol,
                "price": float(price),
                "change": float(change)
            }
        except Exception as e2:
            print(f"yfinance fallback error for {symbol}: {e2}")
            return None

def get_historical_data(symbol, period="1y", interval="1d"):
    """
    Fetches historical stock data for the given period and interval.
    """
    try:
        data = yf.download(tickers=symbol, period=period, interval=interval) 
        if data.empty:
            print(f"No historical data found for {symbol} with period={period}, interval={interval}")
            return None
        return data
    except Exception as e:
        print(f"Error fetching historical data for {symbol}: {e}")
        return None