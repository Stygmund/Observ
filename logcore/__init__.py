"""
logcore: Standardized JSON logging library

Provides structured JSON logging with validation for consistent log format
across deployed applications.
"""

from logcore.logger import JSONFormatter, get_logger, setup_logging

__all__ = ['JSONFormatter', 'get_logger', 'setup_logging']
__version__ = '1.0.0'
