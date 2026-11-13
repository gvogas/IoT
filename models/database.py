import sqlite3
from datetime import datetime

from config import DB_PATH

# Dates are saved as text in this format, so they sort and compare with < and >
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


# The current time as saved in the database
def now_text():
    return datetime.now().strftime(DATE_FORMAT)


# Open the database with rows as dicts
def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    # SQLite ignores REFERENCES unless this is on, for every connection
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# A money amount as text for the database, or None if it is empty
def money_or_none(amount):
    return None if amount is None else str(amount)


# The ?,?,? for an IN (...) list of these items
def placeholders(items):
    return ",".join("?" * len(items))


# Run a SELECT and give back every row
def query(sql, args=()):
    conn = connect()
    try:
        return conn.execute(sql, args).fetchall()
    finally:
        conn.close()


# Run a SELECT and give back the first row, or None if there is none
def query_one(sql, args=()):
    conn = connect()
    try:
        return conn.execute(sql, args).fetchone()
    finally:
        conn.close()


# Run an INSERT, UPDATE or DELETE, save it, and give back how many rows changed
def execute(sql, args=()):
    conn = connect()
    try:
        cursor = conn.execute(sql, args)
        conn.commit()
        return cursor.rowcount
    finally:
        conn.close()


# Run work(conn) as one: all of its writes are saved, or none
def transaction(work):
    conn = connect()
    try:
        result = work(conn)
        conn.commit()
        return result
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
