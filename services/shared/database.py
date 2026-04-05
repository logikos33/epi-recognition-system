"""
Conexão com banco compartilhada entre API e Worker.
"""
import os
import psycopg2
from contextlib import contextmanager

def get_database_url():
    url = os.environ.get('DATABASE_URL', '')
    # Railway usa postgres:// — psycopg2 precisa postgresql://
    if url.startswith('postgres://'):
        url = url.replace('postgres://', 'postgresql://', 1)
    return url

@contextmanager
def get_db_connection():
    """Context manager: fecha conexão sempre, mesmo com exceção."""
    conn = None
    try:
        conn = psycopg2.connect(get_database_url(), connect_timeout=15)
        yield conn
        conn.commit()
    except Exception:
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()
