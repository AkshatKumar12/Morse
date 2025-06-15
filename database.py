# database.py
import sqlite3
import os
import time # <--- ADDED THIS IMPORT

DB_NAME = 'messenger.db'

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Create contacts table if it doesn't exist
    # A 'contact' here represents another user in your system
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS contacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL
        );
    """)

    # Create messages table if it doesn't exist
    # 'chat_partner_id' links to the 'contacts' table
    # 'sender_username' and 'receiver_username' are useful for display and clarity
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_partner_username TEXT NOT NULL, -- The username of the person you are chatting with
            sender_username TEXT NOT NULL,       -- Your username or partner's username
            receiver_username TEXT NOT NULL,     -- Your username or partner's username
            message_content TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            is_sent_by_me INTEGER NOT NULL       -- 1 if sent by this client, 0 if received
        );
    """)

    conn.commit()
    conn.close()

def add_contact(username):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO contacts (username) VALUES (?)", (username,))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        # Username already exists
        return False
    finally:
        conn.close()

def get_contacts():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT username FROM contacts ORDER BY username")
    contacts = [row[0] for row in cursor.fetchall()]
    conn.close()
    return contacts

def save_message(chat_partner_username, sender_username, receiver_username, message_content, is_sent_by_me):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
        INSERT INTO messages (chat_partner_username, sender_username, receiver_username, message_content, timestamp, is_sent_by_me)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (chat_partner_username, sender_username, receiver_username, message_content, timestamp, 1 if is_sent_by_me else 0))
    conn.commit()
    conn.close()

def get_messages(chat_partner_username):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT sender_username, message_content, timestamp, is_sent_by_me
        FROM messages
        WHERE chat_partner_username = ?
        ORDER BY timestamp
    """, (chat_partner_username,))
    messages = []
    for row in cursor.fetchall():
        messages.append({
            "sender": row[0],
            "content": row[1],
            "timestamp": row[2],
            "is_sent_by_me": bool(row[3])
        })
    conn.close()
    return messages

if __name__ == '__main__':
    # Simple test for database
    if os.path.exists(DB_NAME):
        os.remove(DB_NAME)
        print("Removed existing database for fresh start.")
    init_db()
    print("Database initialized.")

    add_contact("Alice")
    add_contact("Bob")
    add_contact("Alice") # Should return False, already exists
    print(f"Contacts: {get_contacts()}")

    save_message("Alice", "Me", "Alice", "Hello Alice!", True)
    save_message("Alice", "Alice", "Me", "Hi there!", False)
    save_message("Bob", "Me", "Bob", "Hey Bob, how are you?", True)

    print("\nMessages with Alice:")
    for msg in get_messages("Alice"):
        print(msg)

    print("\nMessages with Bob:")
    for msg in get_messages("Bob"):
        print(msg)