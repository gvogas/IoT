import sqlite3

from config import DB_PATH


def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    # SQLite ignores REFERENCES unless this is on, for every connection
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


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


# Run several writes as one: they are all saved, or none of them are
# work is a function that takes the connection and does the writes
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
