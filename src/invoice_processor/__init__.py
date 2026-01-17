#!/usr/bin/env python3
"""
Invoice Processor - PDF Invoice Parser with GUI
Extracts structured data from PDF invoices using multiple parsing strategies.
"""

__version__ = "2.0.0"
__author__ = "Invoice Processor Team"

from .core.config import get_config, Config
from .core.constants import PARSING_FAILED
from .core.exceptions import (
    InvoiceProcessorError,
    PDFParsingError,
    PDFCorruptedError,
    FileOperationError,
    ValidationError,
    PathTraversalError,
    ConfigurationError
)
from .parsers.pdf_parser import parse_invoice

__all__ = [
    'get_config',
    'Config',
    'PARSING_FAILED',
    'InvoiceProcessorError',
    'PDFParsingError',
    'PDFCorruptedError',
    'FileOperationError',
    'ValidationError',
    'PathTraversalError',
    'ConfigurationError',
    'parse_invoice',
]
