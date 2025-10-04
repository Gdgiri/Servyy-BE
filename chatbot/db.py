import sqlite3
from datetime import datetime
import json

conn = sqlite3.connect("chat_memory.db", check_same_thread=False)
cursor = conn.cursor()

# Create table: store one row per turn (human + ai)
cursor.execute("""
CREATE TABLE IF NOT EXISTS conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    messages TEXT NOT NULL,  -- JSON: {"user": "...", "ai": "..."}
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
)
""")
conn.commit()


def save_turn(user_id: str, user_message: str, ai_message: str):
    """Save a turn in a single row for the user, appending to existing conversation."""
    # Load existing conversation for this user
    cursor.execute("SELECT messages FROM conversations WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()

    if row:
        # Existing conversation: parse and append new turn
        conversation = json.loads(row[0])
    else:
        # New conversation
        conversation = []

    # Append current turn
    conversation.append({"user": user_message, "ai": ai_message})

    # Convert to JSON string
    messages_json = json.dumps(conversation, ensure_ascii=False)

    if row:
        # Update existing row
        cursor.execute(
            "UPDATE conversations SET messages = ?, timestamp = CURRENT_TIMESTAMP WHERE user_id = ?",
            (messages_json, user_id)
        )
    else:
        # Insert new row
        cursor.execute(
            "INSERT INTO conversations (user_id, messages) VALUES (?, ?)",
            (user_id, messages_json)
        )

    conn.commit()



def load_history(user_id: str, limit: int = 10):
    """Load the last N turns for a user from a single-row conversation."""
    cursor.execute("SELECT messages FROM conversations WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    if row:
        conversation = json.loads(row[0])
        # Keep only the last N turns
        return conversation[-limit:]
    return []


