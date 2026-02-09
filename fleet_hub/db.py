"""
Database connection management for Fleet Hub
"""
import os
import psycopg2
from psycopg2.extras import RealDictCursor


def get_db_connection():
    """
    Create a PostgreSQL database connection

    Reads connection string from OBSERV_DB_URL environment variable.
    Returns connection with RealDictCursor for dict-like row access.
    """
    db_url = os.getenv('OBSERV_DB_URL')

    if not db_url:
        raise ValueError(
            "OBSERV_DB_URL environment variable not set. "
            "Please set it to your PostgreSQL connection string."
        )

    conn = psycopg2.connect(db_url, cursor_factory=RealDictCursor)
    return conn
