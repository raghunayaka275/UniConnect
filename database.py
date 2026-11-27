
import sqlite3
import hashlib
import secrets
import platform
import psycopg
import streamlit as st


# ---------------- DATABASE CONFIGURATION ----------------

# Mac uses SQLite; Streamlit Cloud (Linux) uses PostgreSQL.
USE_POSTGRES = platform.system() == "Linux"

DB_NAME = "uniconnect.db"


def connect_db():
    if USE_POSTGRES:
        database_url = st.secrets["database"]["url"]
        return psycopg.connect(database_url, sslmode="require")

    return sqlite3.connect(DB_NAME, timeout=10)


# ---------------- QUERY EXECUTION ----------------

def execute(cursor, query, params=()):
    if USE_POSTGRES:
        query = query.replace("INSERT OR IGNORE INTO", "INSERT INTO")
        query = query.replace("?", "%s")

        if "INSERT INTO connections" in query:
            query += " ON CONFLICT DO NOTHING"

    cursor.execute(query, params)


# ---------------- DATABASE INITIALISATION ----------------

def init_db():
    conn = connect_db()
    cursor = conn.cursor()

    if USE_POSTGRES:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                password_hash TEXT NOT NULL,
                salt TEXT NOT NULL,
                name TEXT,
                programme TEXT,
                study_year TEXT,
                bio TEXT,
                skills TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS connections (
                user1 TEXT,
                user2 TEXT,
                PRIMARY KEY (user1, user2)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS requests (
                id SERIAL PRIMARY KEY,
                sender TEXT,
                receiver TEXT,
                status TEXT DEFAULT 'pending'
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS posts (
                id SERIAL PRIMARY KEY,
                username TEXT,
                content TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

    else:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                password_hash TEXT NOT NULL,
                salt TEXT NOT NULL,
                name TEXT,
                programme TEXT,
                study_year TEXT,
                bio TEXT,
                skills TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS connections (
                user1 TEXT,
                user2 TEXT,
                PRIMARY KEY (user1, user2)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender TEXT,
                receiver TEXT,
                status TEXT DEFAULT 'pending'
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT,
                content TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

    conn.commit()
    conn.close()


# ---------------- PASSWORD SECURITY ----------------

def hash_password(password, salt):
    return hashlib.pbkdf2_hmac(
        "sha256",
        password.encode(),
        salt.encode(),
        100000
    ).hex()


# ---------------- USER REGISTRATION ----------------

def register_user(username, password, name):
    conn = connect_db()
    cursor = conn.cursor()

    salt = secrets.token_hex(16)
    password_hash = hash_password(password, salt)

    try:
        execute(cursor, """
            INSERT INTO users
            (username, password_hash, salt, name)
            VALUES (?, ?, ?, ?)
        """, (username, password_hash, salt, name))

        conn.commit()
        return True

    except (sqlite3.IntegrityError, psycopg.IntegrityError):
        return False

    finally:
        conn.close()


# ---------------- USER LOGIN ----------------

def login_user(username, password):
    conn = connect_db()
    cursor = conn.cursor()

    execute(cursor, """
        SELECT password_hash, salt
        FROM users
        WHERE username = ?
    """, (username,))

    result = cursor.fetchone()
    conn.close()

    if result is None:
        return False

    stored_hash, salt = result
    entered_hash = hash_password(password, salt)

    return secrets.compare_digest(stored_hash, entered_hash)


# ---------------- USER INFORMATION ----------------

def get_all_users():
    conn = connect_db()
    cursor = conn.cursor()

    execute(cursor, "SELECT username FROM users")
    users = [row[0] for row in cursor.fetchall()]

    conn.close()
    return users


def get_profile(username):
    conn = connect_db()
    cursor = conn.cursor()

    execute(cursor, """
        SELECT username, name, programme, study_year, bio, skills
        FROM users
        WHERE username = ?
    """, (username,))

    profile = cursor.fetchone()
    conn.close()

    return profile


def get_all_profiles():
    conn = connect_db()
    cursor = conn.cursor()

    execute(cursor, """
        SELECT username, name, programme, study_year, bio, skills
        FROM users
    """)

    profiles = cursor.fetchall()
    conn.close()

    return profiles


def update_profile(username, name, programme, study_year, bio, skills):
    conn = connect_db()
    cursor = conn.cursor()

    execute(cursor, """
        UPDATE users
        SET name = ?,
            programme = ?,
            study_year = ?,
            bio = ?,
            skills = ?
        WHERE username = ?
    """, (name, programme, study_year, bio, skills, username))

    conn.commit()
    conn.close()


# ---------------- CONNECTION REQUESTS ----------------

def send_request(sender, receiver):
    if sender == receiver:
        return False

    conn = connect_db()
    cursor = conn.cursor()

    execute(cursor, """
        SELECT COUNT(*)
        FROM users
        WHERE username IN (?, ?)
    """, (sender, receiver))

    if cursor.fetchone()[0] != 2:
        conn.close()
        return False

    user1, user2 = sorted([sender, receiver])

    execute(cursor, """
        SELECT *
        FROM connections
        WHERE user1 = ? AND user2 = ?
    """, (user1, user2))

    if cursor.fetchone():
        conn.close()
        return False

    execute(cursor, """
        SELECT *
        FROM requests
        WHERE status = 'pending'
        AND (
            (sender = ? AND receiver = ?)
            OR
            (sender = ? AND receiver = ?)
        )
    """, (sender, receiver, receiver, sender))

    if cursor.fetchone():
        conn.close()
        return False

    execute(cursor, """
        INSERT INTO requests (sender, receiver)
        VALUES (?, ?)
    """, (sender, receiver))

    conn.commit()
    conn.close()
    return True


def get_incoming_requests(username):
    conn = connect_db()
    cursor = conn.cursor()

    execute(cursor, """
        SELECT id, sender
        FROM requests
        WHERE receiver = ? AND status = 'pending'
    """, (username,))

    requests = cursor.fetchall()
    conn.close()
    return requests


def get_outgoing_requests(username):
    conn = connect_db()
    cursor = conn.cursor()

    execute(cursor, """
        SELECT id, receiver
        FROM requests
        WHERE sender = ? AND status = 'pending'
    """, (username,))

    requests = cursor.fetchall()
    conn.close()
    return requests


def accept_request(request_id):
    conn = connect_db()
    cursor = conn.cursor()

    execute(cursor, """
        SELECT sender, receiver
        FROM requests
        WHERE id = ? AND status = 'pending'
    """, (request_id,))

    request = cursor.fetchone()

    if request is None:
        conn.close()
        return False

    sender, receiver = request
    user1, user2 = sorted([sender, receiver])

    execute(cursor, """
        INSERT OR IGNORE INTO connections (user1, user2)
        VALUES (?, ?)
    """, (user1, user2))

    execute(cursor, """
        UPDATE requests
        SET status = 'accepted'
        WHERE id = ?
    """, (request_id,))

    conn.commit()
    conn.close()
    return True


def reject_request(request_id):
    conn = connect_db()
    cursor = conn.cursor()

    execute(cursor, """
        UPDATE requests
        SET status = 'rejected'
        WHERE id = ? AND status = 'pending'
    """, (request_id,))

    conn.commit()
    conn.close()


def cancel_request(sender, receiver):
    conn = connect_db()
    cursor = conn.cursor()

    execute(cursor, """
        UPDATE requests
        SET status = 'cancelled'
        WHERE sender = ?
        AND receiver = ?
        AND status = 'pending'
    """, (sender, receiver))

    cancelled = cursor.rowcount > 0

    conn.commit()
    conn.close()
    return cancelled


def remove_connection(user1, user2):
    first, second = sorted([user1, user2])

    conn = connect_db()
    cursor = conn.cursor()

    execute(cursor, """
        DELETE FROM connections
        WHERE user1 = ? AND user2 = ?
    """, (first, second))

    conn.commit()
    conn.close()


def get_all_connections():
    conn = connect_db()
    cursor = conn.cursor()

    execute(cursor, """
        SELECT user1, user2
        FROM connections
    """)

    connections = cursor.fetchall()
    conn.close()
    return connections


# ---------------- POSTS ----------------

def create_post(username, content):
    conn = connect_db()
    cursor = conn.cursor()

    execute(cursor, """
        INSERT INTO posts (username, content)
        VALUES (?, ?)
    """, (username, content))

    conn.commit()
    conn.close()


def get_all_posts():
    conn = connect_db()
    cursor = conn.cursor()

    execute(cursor, """
        SELECT id, username, content, created_at
        FROM posts
        ORDER BY created_at DESC
    """)

    posts = cursor.fetchall()
    conn.close()
    return posts


def delete_post(post_id, username):
    conn = connect_db()
    cursor = conn.cursor()

    execute(cursor, """
        DELETE FROM posts
        WHERE id = ? AND username = ?
    """, (post_id, username))

    conn.commit()
    conn.close()
