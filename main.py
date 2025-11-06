# File: main.py
# --- UPDATED TO REDUCE INDICES BAR HEIGHT ---

import sys
import locale
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QTableWidget, QTableWidgetItem, QHeaderView,
    QLabel, QLineEdit, QPushButton, QGroupBox, QInputDialog, QMessageBox,
    QSplitter, QMenu, QCompleter
)
from PySide6.QtGui import QFont, QColor, QAction, QIcon
from PySide6.QtCore import Qt, QThread, Signal

# Import backend logic
from portfolio_db import (
    initialize_database, 
    add_virtual_cash, 
    get_cash_balance, 
    get_holdings, 
    get_transactions,
    get_watchlist,
    add_to_watchlist,
    remove_from_watchlist
)
from market_data import get_live_quote, load_symbol_map
from trading_engine import place_order
from chart_window import ChartWindow

# --- SET UP INR CURRENCY FORMATTING ---
try:
    locale.setlocale(locale.LC_MONETARY, 'en_IN.UTF-8')
except locale.Error:
    try:
        locale.setlocale(locale.LC_MONETARY, 'en_IN')
    except locale.Error:
        print("Warning: 'en_IN' locale not found. Using default currency formatting.")

def format_inr(value):
    return locale.currency(value, grouping=True, symbol=True)

# --- WORKER THREAD (Unchanged) ---
class RefreshWorker(QThread):
    data_fetched = Signal(str, object)
    calculations_complete = Signal(float, float)
    finished = Signal()
    def __init__(self, symbols):
        super().__init__()
        self.symbols = symbols
        self.all_data = {} 
    def run(self):
        total_value, total_pnl = 0.0, 0.0
        holdings_map = {h['symbol']: h for h in get_holdings()}
        for symbol in self.symbols:
            if self.isInterruptionRequested(): return
            quote = get_live_quote(symbol)
            if quote:
                self.all_data[symbol] = quote
                self.data_fetched.emit(symbol, quote)
                if symbol in holdings_map:
                    holding = holdings_map[symbol]
                    current_value = quote["price"] * holding["quantity"]
                    pnl = (quote["price"] - holding["avg_price"]) * holding["quantity"]
                    total_value += current_value
                    total_pnl += pnl
        self.calculations_complete.emit(total_value, total_pnl)
        self.finished.emit()

# --- STYLESHEET (Adjusted for smaller indices bar) ---
DARK_STYLESHEET = """
    QMainWindow {
        background-color: #1e1e1e;
    }
    QWidget {
        background-color: #1e1e1e;
        color: #f0f0f0;
        font-family: Arial;
        font-size: 13px;
    }
    
    /* --- INDICES BAR STYLE --- */
    QWidget#indices_bar {
        background-color: #000000;
        border-bottom: 1px solid #3c3f41;
        min-height: 30px; /* Set a minimum height */
        max-height: 30px; /* Set a maximum height to control it */
    }
    QLabel.index_name {
        font-weight: bold;
        color: #f0f0f0;
        padding-left: 10px;
        font-size: 12px; /* Slightly smaller font for compactness */
    }
    QLabel.index_price {
        font-weight: bold;
        font-size: 12px; /* Slightly smaller font for compactness */
    }
    QLabel.index_price_change { /* New class for the change labels */
        font-size: 12px; /* Slightly smaller font for compactness */
    }
    /* --- END INDICES BAR STYLE --- */

    QSplitter::handle {
        background-color: #3c3f41;
    }
    QSplitter::handle:horizontal { width: 3px; }
    
    QGroupBox, QTableWidget, QLineEdit {
        background-color: #2a2d34;
        border: 1px solid #3c3f41;
    }
    QTabWidget::pane {
        border-top: 1px solid #3c3f41;
        background-color: #2a2d34;
    }
    QTabBar::tab {
        background-color: #1e1e1e;
        color: #f0f0f0;
        padding: 8px 20px;
        border: 1px solid #1e1e1e;
        border-bottom: none;
    }
    QTabBar::tab:selected {
        background-color: #0078d7;
        color: white;
    }
    QHeaderView::section {
        background-color: #3c3f41;
        color: white;
        padding: 5px;
        border: 1px solid #3c3f41;
        font-weight: bold;
    }
    QLineEdit {
        padding: 6px;
        border-radius: 3px;
    }
    QPushButton {
        background-color: #0078d7;
        color: white;
        font-weight: bold;
        padding: 8px 12px;
        border: none;
        border-radius: 3px;
    }
    QPushButton:hover { background-color: #005a9e; }
    
    QPushButton#buy_button { background-color: #00c853; }
    QPushButton#buy_button:hover { background-color: #009624; }
    QPushButton#sell_button { background-color: #ff3d00; }
    QPushButton#sell_button:hover { background-color: #c30000; }
    
    QPushButton#refresh_button { background-color: #555; }
    QPushButton#refresh_button:hover { background-color: #666; }
    QPushButton#add_watchlist_button { background-color: #444; }
    QPushButton#add_watchlist_button:hover { background-color: #555; }

    QGroupBox {
        font-weight: bold;
        border-radius: 5px;
        margin-top: 10px;
        font-size: 14px;
    }
    QGroupBox::title {
        subcontrol-origin: margin;
        subcontrol-position: top left;
        padding: 0 5px;
        left: 10px;
    }
    QCompleter QAbstractItemView {
        background-color: #3c3c3c;
        color: #f0f0f0;
        border: 1px solid #555;
        selection-background-color: #0078d7;
    }
"""

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        initialize_database()
        
        self.symbol_map = load_symbol_map()
        self.company_names_list = list(self.symbol_map.keys())
        self.company_completer = QCompleter(self.company_names_list, self)
        self.company_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.company_completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self.company_completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        
        self.worker_thread = None 
        self.open_charts = []

        self.setWindowTitle("Virtual Trading Platform")
        self.setGeometry(100, 100, 1200, 800)
        
        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        main_layout.addWidget(self.create_indices_bar())
        
        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.main_splitter.addWidget(self.create_left_pane())
        self.main_splitter.addWidget(self.create_middle_pane())
        self.main_splitter.addWidget(self.create_right_pane())
        self.main_splitter.setSizes([300, 600, 300])
        
        main_layout.addWidget(self.main_splitter)
        
        self.setCentralWidget(main_widget)

        self.update_all_ui()

    # --- create_indices_bar (Adjusted for smaller height) ---
    def create_indices_bar(self):
        """Creates the top bar for Nifty 50 and Sensex."""
        indices_widget = QWidget()
        indices_widget.setObjectName("indices_bar") # For styling
        layout = QHBoxLayout(indices_widget)
        layout.setContentsMargins(0, 0, 0, 0) # Removed padding here
        layout.setSpacing(5) # Reduced spacing between elements
        
        # --- Nifty 50 ---
        nifty_label = QLabel("NIFTY 50")
        nifty_label.setProperty("class", "index_name")
        self.nifty_price_label = QLabel(format_inr(0))
        self.nifty_price_label.setProperty("class", "index_price")
        self.nifty_change_label = QLabel("(0.00%)")
        self.nifty_change_label.setProperty("class", "index_price_change") # New class
        
        layout.addWidget(nifty_label)
        layout.addWidget(self.nifty_price_label)
        layout.addWidget(self.nifty_change_label)
        layout.addSpacing(20) # Add space between indices

        # --- Sensex ---
        sensex_label = QLabel("SENSEX")
        sensex_label.setProperty("class", "index_name")
        self.sensex_price_label = QLabel(format_inr(0))
        self.sensex_price_label.setProperty("class", "index_price")
        self.sensex_change_label = QLabel("(0.00%)")
        self.sensex_change_label.setProperty("class", "index_price_change") # New class
        
        layout.addWidget(sensex_label)
        layout.addWidget(self.sensex_price_label)
        layout.addWidget(self.sensex_change_label)
        
        layout.addStretch() # Push all to the left
        return indices_widget

    def create_left_pane(self):
        pane = QWidget()
        layout = QVBoxLayout(pane)
        layout.setContentsMargins(5, 10, 5, 10)
        add_layout = QHBoxLayout()
        self.watchlist_input = QLineEdit()
        self.watchlist_input.setPlaceholderText("Add Company/Symbol...")
        self.watchlist_input.setCompleter(self.company_completer)
        self.company_completer.activated[str].connect(
            lambda name: self.on_completer_activated(name, self.watchlist_input)
        )
        add_layout.addWidget(self.watchlist_input)
        add_button = QPushButton(QIcon.fromTheme("list-add"), "")
        add_button.setObjectName("add_watchlist_button")
        add_button.clicked.connect(self.add_stock_to_watchlist)
        add_layout.addWidget(add_button)
        layout.addLayout(add_layout)
        self.watchlist_table = QTableWidget()
        self.watchlist_table.setColumnCount(4)
        self.watchlist_table.setHorizontalHeaderLabels(["Symbol", "Current Price", "Change (₹)", "% Change"])
        self.watchlist_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.watchlist_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.watchlist_table.customContextMenuRequested.connect(self.watchlist_context_menu)
        self.watchlist_table.cellDoubleClicked.connect(self.open_chart_window)
        self.watchlist_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.watchlist_table)
        return pane

    def create_middle_pane(self):
        tabs = QTabWidget()
        self.portfolio_table = QTableWidget()
        self.portfolio_table.setColumnCount(6)
        self.portfolio_table.setHorizontalHeaderLabels(["Symbol", "Quantity", "Avg. Price", "Current Price", "Total Value", "P&L"])
        self.portfolio_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.portfolio_table.cellDoubleClicked.connect(self.open_chart_window)
        self.portfolio_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        tabs.addTab(self.portfolio_table, QIcon.fromTheme("user-home"), "Portfolio")
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(5)
        self.history_table.setHorizontalHeaderLabels(["Timestamp", "Type", "Symbol", "Quantity", "Price"])
        self.history_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.history_table.setSortingEnabled(True)
        self.history_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        tabs.addTab(self.history_table, QIcon.fromTheme("document-properties"), "History")
        return tabs

    def create_right_pane(self):
        pane = QWidget()
        layout = QVBoxLayout(pane)
        layout.setContentsMargins(5, 10, 5, 10)
        self.refresh_button = QPushButton(QIcon.fromTheme("view-refresh"), " Refresh All Data")
        self.refresh_button.setObjectName("refresh_button")
        self.refresh_button.clicked.connect(self.trigger_refresh)
        layout.addWidget(self.refresh_button)
        layout.addWidget(self.create_account_area())
        layout.addWidget(self.create_trading_area())
        layout.addStretch()
        return pane
        
    def create_account_area(self):
        account_group = QGroupBox("Account")
        layout = QVBoxLayout(account_group)
        cash_layout = QHBoxLayout()
        cash_layout.addWidget(QLabel("Cash Balance:"))
        self.cash_display_label = QLabel(format_inr(0))
        self.cash_display_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        self.cash_display_label.setStyleSheet("color: #00c853;")
        cash_layout.addStretch()
        cash_layout.addWidget(self.cash_display_label)
        layout.addLayout(cash_layout)
        value_layout = QHBoxLayout()
        value_layout.addWidget(QLabel("Portfolio Value:"))
        self.total_value_label = QLabel(format_inr(0))
        self.total_value_label.setFont(QFont("Arial", 14))
        value_layout.addStretch()
        value_layout.addWidget(self.total_value_label)
        layout.addLayout(value_layout)
        pnl_layout = QHBoxLayout()
        pnl_layout.addWidget(QLabel("Total P&L:"))
        self.total_pnl_label = QLabel(format_inr(0))
        self.total_pnl_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        pnl_layout.addStretch()
        pnl_layout.addWidget(self.total_pnl_label)
        layout.addLayout(pnl_layout)
        self.add_funds_button = QPushButton(QIcon.fromTheme("list-add"), " Add Virtual Funds")
        self.add_funds_button.clicked.connect(self.add_funds_dialog)
        layout.addWidget(self.add_funds_button)
        return account_group
        
    def create_trading_area(self):
        trade_group = QGroupBox("Place an Order")
        layout = QVBoxLayout(trade_group)
        layout.addWidget(QLabel("Company Name/Symbol:"))
        self.symbol_input = QLineEdit()
        self.symbol_input.setPlaceholderText("e.g., Reliance Industries")
        self.symbol_input.setCompleter(self.company_completer)
        self.company_completer.activated[str].connect(
            lambda name: self.on_completer_activated(name, self.symbol_input)
        )
        layout.addWidget(self.symbol_input)
        layout.addWidget(QLabel("Quantity:"))
        self.qty_input = QLineEdit()
        self.qty_input.setPlaceholderText("e.g., 10")
        layout.addWidget(self.qty_input)
        button_layout = QHBoxLayout()
        self.buy_button = QPushButton("BUY")
        self.buy_button.setObjectName("buy_button")
        self.buy_button.clicked.connect(lambda: self.execute_trade("BUY"))
        button_layout.addWidget(self.buy_button)
        self.sell_button = QPushButton("SELL")
        self.sell_button.setObjectName("sell_button")
        self.sell_button.clicked.connect(lambda: self.execute_trade("SELL"))
        button_layout.addWidget(self.sell_button)
        layout.addLayout(button_layout)
        return trade_group
        
    def on_completer_activated(self, selected_name, line_edit_widget):
        if selected_name in self.symbol_map:
            symbol = self.symbol_map[selected_name]
            line_edit_widget.setText(symbol)

    def open_chart_window(self, row, column):
        table = self.sender()
        if not table: return
        symbol_item = table.item(row, 0)
        if not symbol_item: return
        symbol = symbol_item.text()
        for chart in self.open_charts:
            if chart.symbol == symbol:
                chart.activateWindow()
                return
        chart_win = ChartWindow(symbol, self)
        self.open_charts.append(chart_win)
        chart_win.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        chart_win.destroyed.connect(lambda: self.open_charts.remove(chart_win))
        chart_win.show()

    def add_funds_dialog(self):
        amount, ok = QInputDialog.getDouble(self, "Add Virtual Funds", "Enter amount to add (₹):", 10000.00, 0, 10000000, 2)
        if ok and amount > 0:
            success, message = add_virtual_cash(amount)
            if success:
                QMessageBox.information(self, "Success", message)
                self.update_all_ui()
            else:
                QMessageBox.warning(self, "Error", message)

    def execute_trade(self, order_type):
        symbol = self.symbol_input.text().upper()
        try:
            quantity = int(self.qty_input.text())
        except ValueError:
            QMessageBox.warning(self, "Input Error", "Quantity must be a valid number.")
            return
        if not symbol:
            QMessageBox.warning(self, "Input Error", "Symbol cannot be empty.")
            return
        if symbol not in self.symbol_map.values():
            QMessageBox.warning(self, "Input Error", f"'{symbol}' is not a valid symbol. Please select from the list.")
            return
        success, message = place_order(symbol, quantity, order_type)
        if success:
            QMessageBox.information(self, "Trade Successful", message)
            self.symbol_input.clear()
            self.qty_input.clear()
            self.update_all_ui()
        else:
            QMessageBox.critical(self, "Trade Failed", message)

    def update_all_ui(self):
        cash = get_cash_balance()
        self.cash_display_label.setText(format_inr(cash))
        self.populate_history_table()
        self.trigger_refresh()

    def trigger_refresh(self):
        if self.worker_thread and self.worker_thread.isRunning():
            return
        self.refresh_button.setText(" Refreshing...")
        self.refresh_button.setEnabled(False)
        holdings = get_holdings()
        watchlist = get_watchlist()
        
        symbols_to_fetch = set([h['symbol'] for h in holdings] + watchlist)
        symbols_to_fetch.add("^NSEI") # Nifty 50
        symbols_to_fetch.add("^BSESN") # Sensex
        
        self.clear_live_tables()
        self.worker_thread = RefreshWorker(list(symbols_to_fetch))
        self.worker_thread.data_fetched.connect(self.update_row_data)
        self.worker_thread.calculations_complete.connect(self.update_header_totals)
        self.worker_thread.finished.connect(self.on_refresh_finished)
        self.worker_thread.start()

    def clear_live_tables(self):
        self.watchlist_table.setRowCount(0)
        self.portfolio_table.setRowCount(0)

    def update_index_label(self, price_label, change_label, quote):
        price = quote["price"]
        change = quote["change"]
        percent_change = (change / (price - change)) * 100 if (price - change) != 0 else 0
        
        price_label.setText(f"{price:,.2f}")
        change_label.setText(f"{change:+.2f} ({percent_change:+.2f}%)")
        
        if change > 0:
            price_label.setStyleSheet("color: #00c853;")
            change_label.setStyleSheet("color: #00c853;")
        elif change < 0:
            price_label.setStyleSheet("color: #ff3d00;")
            change_label.setStyleSheet("color: #ff3d00;")
        else:
            price_label.setStyleSheet("color: #f0f0f0;")
            change_label.setStyleSheet("color: #f0f0f0;")

    def update_row_data(self, symbol, quote):
        if symbol == "^NSEI":
            self.update_index_label(self.nifty_price_label, self.nifty_change_label, quote)
            return
        elif symbol == "^BSESN":
            self.update_index_label(self.sensex_price_label, self.sensex_change_label, quote)
            return
            
        for row in range(self.watchlist_table.rowCount()):
            if self.watchlist_table.item(row, 0).text() == symbol:
                self.populate_watchlist_row(row, symbol, quote)
                break
        for row in range(self.portfolio_table.rowCount()):
            if self.portfolio_table.item(row, 0).text() == symbol:
                holding = get_holdings() 
                holding_data = next((h for h in holding if h['symbol'] == symbol), None)
                if holding_data:
                    self.populate_portfolio_row(row, holding_data, quote)
                break

    def on_refresh_finished(self):
        self.refresh_button.setText(" Refresh All Data")
        self.refresh_button.setEnabled(True)
        self.populate_portfolio_table()
        self.populate_watchlist_table()

    def update_header_totals(self, total_value, total_pnl):
        self.total_value_label.setText(f"Portfolio Value: {format_inr(total_value)}")
        self.total_pnl_label.setText(f"Total P&L: {format_inr(total_pnl)}")
        if total_pnl > 0:
            self.total_pnl_label.setStyleSheet("color: #00c853;")
        elif total_pnl < 0:
            self.total_pnl_label.setStyleSheet("color: #ff3d00;")
        else:
            self.total_pnl_label.setStyleSheet("color: #f0f0f0;")

    def populate_portfolio_table(self):
        self.portfolio_table.setRowCount(0)
        holdings = get_holdings()
        for row, item in enumerate(holdings):
            self.portfolio_table.insertRow(row)
            quote = None
            if self.worker_thread and self.worker_thread.all_data:
                quote = self.worker_thread.all_data.get(item["symbol"])
            self.populate_portfolio_row(row, item, quote)
            
    def populate_portfolio_row(self, row, item, quote):
        symbol, quantity, avg_price = item["symbol"], item["quantity"], item["avg_price"]
        if quote:
            current_price, current_value, pnl = quote["price"], quote["price"] * quantity, (quote["price"] - avg_price) * quantity
            current_price_str, current_value_str, pnl_str = format_inr(current_price), format_inr(current_value), format_inr(pnl)
            pnl_item = QTableWidgetItem(pnl_str)
            pnl_item.setForeground(QColor("#00c853") if pnl > 0 else (QColor("#ff3d00") if pnl < 0 else QColor("#f0f0f0")))
        else:
            current_price_str, current_value_str, pnl_str = "N/A", "N/A", "N/A"
            pnl_item = QTableWidgetItem(pnl_str)
        self.portfolio_table.setItem(row, 0, QTableWidgetItem(symbol))
        self.portfolio_table.setItem(row, 1, QTableWidgetItem(f"{quantity:,.0f}"))
        self.portfolio_table.setItem(row, 2, QTableWidgetItem(format_inr(avg_price)))
        self.portfolio_table.setItem(row, 3, QTableWidgetItem(current_price_str))
        self.portfolio_table.setItem(row, 4, QTableWidgetItem(current_value_str))
        self.portfolio_table.setItem(row, 5, pnl_item)
            
    def populate_history_table(self):
        self.history_table.setRowCount(0)
        transactions = get_transactions()
        for row, trans in enumerate(transactions):
            self.history_table.insertRow(row)
            self.history_table.setItem(row, 0, QTableWidgetItem(trans["timestamp"][:19]))
            self.history_table.setItem(row, 1, QTableWidgetItem(trans["type"]))
            self.history_table.setItem(row, 2, QTableWidgetItem(trans["symbol"]))
            self.history_table.setItem(row, 3, QTableWidgetItem(f"{trans['quantity']:,.0f}"))
            self.history_table.setItem(row, 4, QTableWidgetItem(format_inr(trans['price'])))

    def populate_watchlist_table(self):
        self.watchlist_table.setRowCount(0)
        symbols = get_watchlist()
        for row, symbol in enumerate(symbols):
            self.watchlist_table.insertRow(row)
            quote = None
            if self.worker_thread and self.worker_thread.all_data:
                quote = self.worker_thread.all_data.get(symbol)
            self.populate_watchlist_row(row, symbol, quote)

    def populate_watchlist_row(self, row, symbol, quote):
        symbol_item = QTableWidgetItem(symbol)
        if quote:
            price, change = quote["price"], quote["change"]
            percent_change = (change / (price - change)) * 100 if (price - change) != 0 else 0
            price_str, change_str, percent_str = f"{price:,.2f}", f"{change:+.2f}", f"{percent_change:+.2f}%"
            change_item, percent_item = QTableWidgetItem(change_str), QTableWidgetItem(percent_str)
            color = QColor("#00c853") if change > 0 else (QColor("#ff3d00") if change < 0 else QColor("#f0f0f0"))
            change_item.setForeground(color)
            percent_item.setForeground(color)
        else:
            price_str, change_str, percent_str = "N/A", "N/A", "N/A"
            change_item, percent_item = QTableWidgetItem(change_str), QTableWidgetItem(percent_str)
        self.watchlist_table.setItem(row, 0, symbol_item)
        self.watchlist_table.setItem(row, 1, QTableWidgetItem(price_str))
        self.watchlist_table.setItem(row, 2, change_item)
        self.watchlist_table.setItem(row, 3, percent_item)

    def add_stock_to_watchlist(self):
        text = self.watchlist_input.text().strip()
        if not text:
            QMessageBox.warning(self, "Input Error", "Input cannot be empty.")
            return
        symbol_to_add = None
        if text in self.symbol_map:
            symbol_to_add = self.symbol_map[text]
        elif text.upper() in self.symbol_map.values():
            symbol_to_add = text.upper()
        else:
            QMessageBox.warning(self, "Input Error", f"'{text}' is not a valid company name or symbol. Please select from the list.")
            return
        add_to_watchlist(symbol_to_add)
        self.watchlist_input.clear()
        self.trigger_refresh()
        
    def watchlist_context_menu(self, pos):
        selected_item = self.watchlist_table.itemAt(pos)
        if not selected_item: return
        row = selected_item.row()
        symbol = self.watchlist_table.item(row, 0).text()
        menu = QMenu()
        remove_action = QAction(QIcon.fromTheme("list-remove"), f" Remove '{symbol}'")
        remove_action.triggered.connect(lambda: self.remove_stock_from_watchlist(symbol))
        menu.addAction(remove_action)
        menu.exec(self.watchlist_table.mapToGlobal(pos))
        
    def remove_stock_from_watchlist(self, symbol):
        remove_from_watchlist(symbol)
        self.trigger_refresh()

# --- Main execution ---
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyleSheet(DARK_STYLESHEET)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())