# File: chart_window.py
# --- UPDATED TO FIX X-AXIS TIME FORMAT ---

import sys
from PySide6.QtWidgets import QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QLabel, QPushButton
from PySide6.QtCore import QThread, Signal, Qt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import pandas as pd
import mplfinance as mpf  

from market_data import get_historical_data

# 1. Worker Thread (Unchanged)
class ChartDataWorker(QThread):
    data_ready = Signal(object) 
    def __init__(self, symbol, period, interval):
        super().__init__()
        self.symbol = symbol
        self.period = period
        self.interval = interval

    def run(self):
        data = get_historical_data(self.symbol, self.period, self.interval) 
        self.data_ready.emit(data)

# 2. Matplotlib Canvas Widget (Unchanged)
class MplCanvas(FigureCanvas):
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi, facecolor='#2b2b2b')
        super(MplCanvas, self).__init__(self.fig)
        self.setParent(parent)

# 3. Main Chart Window (Updated)
class ChartWindow(QMainWindow):
    def __init__(self, symbol, parent=None):
        super().__init__(parent)
        self.symbol = symbol
        self.current_period_label = "1 Year" # For the title
        
        self.setWindowTitle(f"Stock Chart: {self.symbol}")
        self.setGeometry(150, 150, 800, 600)
        self.setStyleSheet("background-color: #2b2b2b;")

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)

        self.layout.addLayout(self.create_button_layout())

        self.canvas = MplCanvas(self, width=8, height=6, dpi=100)
        self.layout.addWidget(self.canvas)
        
        self.loading_label = QLabel("Loading Chart Data...", self)
        self.loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.loading_label.setStyleSheet("color: white; font-size: 20px; background-color: transparent;")
        self.layout.addWidget(self.loading_label)

        self.loading_label.raise_()
        self.loading_label.setGeometry(0, 0, self.width(), self.height())

        self.load_new_period("1y", "1d", "1 Year (Daily)")
        
    def create_button_layout(self):
        button_layout = QHBoxLayout()
        
        # Updated labels to be shorter
        btn_1d = QPushButton("1D")
        btn_1d.clicked.connect(lambda: self.load_new_period("1d", "5m", "1 Day"))
        
        btn_5d = QPushButton("5D")
        btn_5d.clicked.connect(lambda: self.load_new_period("5d", "30m", "5 Day"))
        
        btn_1m = QPushButton("1M")
        btn_1m.clicked.connect(lambda: self.load_new_period("1mo", "1d", "1 Month"))
        
        btn_1y = QPushButton("1Y")
        btn_1y.clicked.connect(lambda: self.load_new_period("1y", "1d", "1 Year"))
        
        for btn in [btn_1d, btn_5d, btn_1m, btn_1y]:
            btn.setStyleSheet("background-color: #444; padding: 4px 10px; border-radius: 3px;")
            button_layout.addWidget(btn)
            
        button_layout.addStretch()
        return button_layout
        
    def resizeEvent(self, event):
        if hasattr(self, 'loading_label'):
            self.loading_label.setGeometry(0, 0, self.width(), self.height())
        super().resizeEvent(event)

    def load_new_period(self, period, interval, label):
        self.current_period_label = label
        
        self.loading_label.setText("Loading Chart Data...")
        self.loading_label.setVisible(True)
        self.loading_label.raise_()
        self.canvas.fig.clear()
        self.canvas.draw()
        
        self.worker = ChartDataWorker(self.symbol, period, interval)
        self.worker.data_ready.connect(self.plot_data)
        self.worker.start()

    def _clean_data_for_plotting(self, data):
        """(Unchanged from previous step)"""
        if data is None or data.empty:
            raise ValueError(f"No chart data found for {self.symbol}")

        if isinstance(data.columns, pd.MultiIndex):
            new_cols = []
            for col in data.columns:
                new_cols.append(col[0] if isinstance(col, tuple) else col)
            data.columns = new_cols
        
        data.columns = [str(col).lower() for col in data.columns]
        rename_map = {
            'open': 'Open', 'high': 'High', 'low': 'Low', 
            'close': 'Close', 'volume': 'Volume'
        }
        data = data.rename(columns=rename_map)

        ohlc_cols = ['Open', 'High', 'Low', 'Close']
        if not all(col in data.columns for col in ohlc_cols):
            raise ValueError(f"Data for {self.symbol} is missing required columns (O/H/L/C).")

        for col in ohlc_cols + ['Volume']:
            if col in data.columns:
                data[col] = pd.to_numeric(data[col], errors='coerce')

        data = data.dropna(subset=ohlc_cols)

        if data.empty:
            raise ValueError(f"No valid plot data for {self.symbol} after cleaning.")
            
        return data

    def plot_data(self, data):
        """Cleans data and then plots it."""
        self.loading_label.setVisible(False)
        
        try:
            clean_data = self._clean_data_for_plotting(data)
            self.canvas.fig.clear()

            ax1 = self.canvas.fig.add_axes([0.1, 0.3, 0.8, 0.6])
            ax2 = self.canvas.fig.add_axes([0.1, 0.1, 0.8, 0.2], sharex=ax1)

            mc = mpf.make_marketcolors(
                up='g', down='r', inherit=True
            )
            s = mpf.make_mpf_style(
                base_mpf_style='nightclouds',
                marketcolors=mc,
                facecolor='#2b2b2b',
                gridcolor='#555',
                rc={'text.color': 'white', 'axes.labelcolor': 'white'}
            )
            
            # --- THIS IS THE FIX ---
            # 1. Decide date format based on the period label
            if 'Day' in self.current_period_label:
                # For 1D or 5D, show Hour:Minute
                date_format = '%H:%M' 
            else:
                # For 1M or 1Y, show Month-Day
                date_format = '%b %d' 
            # --- END OF FIX ---

            mpf.plot(
                clean_data,
                type='candle',
                style=s,
                ax=ax1,
                volume=ax2,
                datetime_format=date_format, # <-- PASS THE FORMAT HERE
                warn_too_much_data=10000
            )
            
            ax1.set_title(f"{self.symbol} - {self.current_period_label}", color='white')
            
            ax1.set_ylabel('Price (INR)', color='white')
            ax2.set_ylabel('Volume', color='white')
            ax1.tick_params(axis='x', colors='white')
            ax1.tick_params(axis='y', colors='white')
            ax2.tick_params(axis='x', colors='white')
            ax2.tick_params(axis='y', colors='white')
            
            self.canvas.draw()
        
        except Exception as e:
            print(f"Error during plotting: {e}")
            self.show_error_message(f"Error plotting data: {e}")

    def show_error_message(self, message):
        """Displays an error message on the chart canvas."""
        try:
            self.loading_label.setVisible(False)
            self.canvas.fig.clear()
            ax = self.canvas.fig.add_subplot(111)
            ax.set_facecolor('#2b2b2b')
            for spine in ax.spines.values():
                spine.set_visible(False)
            ax.text(0.5, 0.5, message, 
                  ha='center', va='center', color='red', fontsize=16, wrap=True)
            ax.set_xticks([])
            ax.set_yticks([])
            self.canvas.draw()
        except Exception as e:
            print(f"Error in show_error_message: {e}")