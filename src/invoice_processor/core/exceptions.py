#!/usr/bin/env python3
"""
Custom Exception Classes
Defines specific exceptions for the invoice processor application.
"""


class InvoiceProcessorError(Exception):
    """Base exception for all invoice processor errors"""
    pass


class PDFParsingError(InvoiceProcessorError):
    """Raised when PDF parsing fails"""
    pass


class PDFCorruptedError(PDFParsingError):
    """Raised when PDF file is corrupted or invalid"""
    pass


class FileOperationError(InvoiceProcessorError):
    """Raised when file operations fail (move, copy, etc.)"""
    pass


class ValidationError(InvoiceProcessorError):
    """Raised when input validation fails"""
    pass


class PathTraversalError(ValidationError):
    """Raised when path traversal attack is detected"""
    pass


class ConfigurationError(InvoiceProcessorError):
    """Raised when configuration is invalid or missing"""
    pass
