
import sqlite3
import hashlib
import secrets

DB_NAME = "uniconnect.db"


# ---------------- DATABASE CONNECTION ----------------

def connect_db():
    return sqlite3.connect(DB_NAME, timeout=10)


# ---------------- DATABASE INITIALISATION ----------------

def init_db():
    conn = connect_db()
    cursor = conn.cursor()

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
        cursor.execute("""
            INSERT INTO users
            (username, password_hash, salt, name)
            VALUES (?, ?, ?, ?)
        """, (username, password_hash, salt, name))

        conn.commit()
        return True

    except sqlite3.IntegrityError:
        return False

    finally:
        conn.close()


# ---------------- USER LOGIN ----------------

def login_user(username, password):
    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("""
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

# Get all student usernames
def get_all_users():
    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("SELECT username FROM users")
    users = [row[0] for row in cursor.fetchall()]

    conn.close()
    return users


# Get one student's profile
def get_profile(username):
    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT username, name, programme, study_year, bio, skills
        FROM users
        WHERE username = ?
    """, (username,))

    profile = cursor.fetchone()
    conn.close()

    return profile


# Get all student profiles in one database query
def get_all_profiles():
    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT username, name, programme, study_year, bio, skills
        FROM users
    """)

    profiles = cursor.fetchall()
    conn.close()

    return profiles


# Update student profile
def update_profile(username, name, programme, study_year, bio, skills):
    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("""
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

# Send a connection request
def send_request(sender, receiver):

    if sender == receiver:
        return False

    conn = connect_db()
    cursor = conn.cursor()

    # Check whether both users exist
    cursor.execute("""
        SELECT COUNT(*)
        FROM users
        WHERE username IN (?, ?)
    """, (sender, receiver))

    if cursor.fetchone()[0] != 2:
        conn.close()
        return False

    user1, user2 = sorted([sender, receiver])

    # Check whether they are already connected
    cursor.execute("""
        SELECT *
        FROM connections
        WHERE user1 = ? AND user2 = ?
    """, (user1, user2))

    if cursor.fetchone():
        conn.close()
        return False

    # Check for an existing pending request in either direction
    cursor.execute("""
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

    # Create the new request
    cursor.execute("""
        INSERT INTO requests (sender, receiver)
        VALUES (?, ?)
    """, (sender, receiver))

    conn.commit()
    conn.close()

    return True


# Get incoming requests
def get_incoming_requests(username):
    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, sender
        FROM requests
        WHERE receiver = ? AND status = 'pending'
    """, (username,))

    requests = cursor.fetchall()
    conn.close()

    return requests


# Get outgoing requests
def get_outgoing_requests(username):
    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, receiver
        FROM requests
        WHERE sender = ? AND status = 'pending'
    """, (username,))

    requests = cursor.fetchall()
    conn.close()

    return requests


# Accept a connection request
def accept_request(request_id):
    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("""
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

    cursor.execute("""
        INSERT OR IGNORE INTO connections (user1, user2)
        VALUES (?, ?)
    """, (user1, user2))

    cursor.execute("""
        UPDATE requests
        SET status = 'accepted'
        WHERE id = ?
    """, (request_id,))

    conn.commit()
    conn.close()

    return True


# Reject a connection request
def reject_request(request_id):
    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE requests
        SET status = 'rejected'
        WHERE id = ? AND status = 'pending'
    """, (request_id,))

    conn.commit()
    conn.close()


# Cancel an outgoing connection request
def cancel_request(sender, receiver):
    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("""
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


# Remove an existing connection
def remove_connection(user1, user2):
    first, second = sorted([user1, user2])

    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM connections
        WHERE user1 = ? AND user2 = ?
    """, (first, second))

    conn.commit()
    conn.close()


# Get all accepted connections
def get_all_connections():
    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT user1, user2
        FROM connections
    """)

    connections = cursor.fetchall()
    conn.close()

    return connections


# ---------------- POSTS ----------------

# Create a post
def create_post(username, content):
    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO posts (username, content)
        VALUES (?, ?)
    """, (username, content))

    conn.commit()
    conn.close()


# Get all posts, newest first
def get_all_posts():
    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, username, content, created_at
        FROM posts
        ORDER BY created_at DESC
    """)

    posts = cursor.fetchall()
    conn.close()

    return posts


# Delete your own post
def delete_post(post_id, username):
    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM posts
        WHERE id = ? AND username = ?
    """, (post_id, username))

    conn.commit()
    conn.close()


