import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path


@contextmanager
def db_conn(db_file, row_factory=sqlite3.Row):
    """Do all the things that should probably be the defaults.

    Fixes the weird default behavior of transactions, enable reads while
    a transaction is open, improve write performance, enforce foreign keys,
    set dectect_types arg so that columns of type timestamp will be parsed
    into a python datetime and run `pragma optimize` on connection close to
    keep query planner statistics as up to date as possible.

    Args:
        db_file (str, pathlib.Path): The database file.
        row_factory: Default is sqlite3.Row but can be a class_row(<cls>)
    """
    conn = sqlite3.connect(
        db_file,
        isolation_level=None,
        detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES,
    )
    conn.execute("pragma journal_mode=wal;")
    conn.execute("pragma synchronous = normal;")
    conn.execute("pragma temp_store = memory;")
    conn.execute("pragma foreign_keys = on;")
    conn.row_factory = row_factory
    try:
        yield conn
    finally:
        conn.execute("pragma analysis_limit=400;")
        conn.execute("pragma optimize;")
        conn.close()


@contextmanager
def transaction(conn):
    """Context manager for using transactions."""
    # We must issue a "BEGIN" explicitly when running in auto-commit mode.
    conn.execute("BEGIN")
    try:
        # Yield control back to the caller.
        yield
    except:  # noqa: E722
        conn.rollback()  # Roll back all changes if an exception occurs.
        raise
    else:
        conn.commit()


def create_db_if_needed():
    xdg = os.environ.get("XDG_DATA_HOME")
    if not xdg:
        xdg_data_home = Path.home()
    else:
        xdg_data_home = Path(xdg)

    ol_ocr_db = os.environ.get("OL_OCR_DB")
    if not ol_ocr_db:
        db_file = xdg_data_home / "ol_ocr.db"
    else:
        db_file = xdg_data_home / Path(ol_ocr_db)

    if not db_file.exists():
        print("Creating database ...")
        with open('schema.sql') as fp:
            with db_conn(db_file) as conn:
                with transaction(conn):
                    conn.executescript(fp.read())
        print("Database created!")
    return db_file
