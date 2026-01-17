#!/usr/bin/env python3
"""
Constants for Invoice Processor
Centralized location for all magic values and constants.
"""

# Parsing sentinel values
PARSING_FAILED = "PARSING FAILED"

# Default scan interval (in seconds)
DEFAULT_SCAN_INTERVAL = 300  # 5 minutes

# GUI settings
DEFAULT_WINDOW_WIDTH = 1200
DEFAULT_WINDOW_HEIGHT = 600
DEFAULT_WINDOW_GEOMETRY = f"{DEFAULT_WINDOW_WIDTH}x{DEFAULT_WINDOW_HEIGHT}"

# File paths (relative to script directory)
DEFAULT_PENDING_DIR = "invoices/pending"
DEFAULT_PROCESSED_DIR = "invoices/processed"

# Threading delays
THREAD_UPDATE_DELAY_MS = 50  # Delay for updating GUI from threads (milliseconds)

# Column indices for checkboxes (after Banking column added)
TRANSFER_TYPE_COLUMN = '#7'
PAYMENT_SET_COLUMN = '#8'

# Currencies
CURRENCY_EUR = "EUR"
CURRENCY_USD = "USD"
CURRENCY_GBP = "GBP"

# Currency symbols
SYMBOL_EUR = "€"
SYMBOL_USD = "$"
SYMBOL_GBP = "£"

# Logging settings
DEFAULT_LOG_LEVEL = "INFO"
DEFAULT_LOG_FILE = "invoice_processor.log"
DEFAULT_LOG_TO_CONSOLE = True
