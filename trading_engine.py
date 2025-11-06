# File: trading_engine.py
from portfolio_db import get_cash_balance, update_cash_balance, update_holding, log_transaction
from market_data import get_live_quote

def place_order(symbol, quantity, order_type):
    """Processes a BUY or SELL order."""
    if order_type not in ["BUY", "SELL"]:
        return False, "Invalid order type."
    
    if quantity <= 0:
        return False, "Quantity must be positive."

    # Step 1: Get the live market price
    quote = get_live_quote(symbol)
    if not quote:
        return False, f"Could not get live price for {symbol}. Check symbol or API key."
        
    price = quote["price"]
    total_cost = price * quantity
    current_cash = get_cash_balance()

    if order_type == "BUY":
        if total_cost > current_cash:
            return False, f"Insufficient cash. Need ${total_cost:,.2f}, have ${current_cash:,.2f}."
        
        try:
            update_holding(symbol, quantity, price)
            update_cash_balance(-total_cost) # Deduct cash
            log_transaction(symbol, "BUY", quantity, price)
            return True, f"Successfully BOUGHT {quantity} of {symbol} at ${price:,.2f}."
        except Exception as e:
            return False, f"Error during BUY: {e}"

    elif order_type == "SELL":
        try:
            update_holding(symbol, -quantity, price) # Quantity is negative for sell
            update_cash_balance(total_cost) # Add cash from sale
            log_transaction(symbol, "SELL", quantity, price)
            return True, f"Successfully SOLD {quantity} of {symbol} at ${price:,.2f}."
        except ValueError as e:
            return False, str(e) # Catches "Insufficient quantity"
        except Exception as e:
            return False, f"Error during SELL: {e}"

    return False, "Unknown error during trade execution."