"""
logcore: Standardized JSON logging library

Provides structured JSON logging with validation for consistent log format
across deployed applications.
"""

from logcore.logger import JSONFormatter, get_logger

__all__ = ['JSONFormatter', 'get_logger']
__version__ = '1.0.0'
