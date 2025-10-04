# prospect_tool.py
import sqlite3
from datetime import datetime

DB_PATH = "sales_ai.db"

def get_connection():
    """Get a fresh database connection."""
    conn = sqlite3.connect(DB_PATH)
    return conn

# Initialize table
def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS prospect_data (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        email TEXT UNIQUE,
        company TEXT,
        details TEXT,
        created_at TEXT
    )
    """)
    conn.commit()
    conn.close()

def add_prospect(name: str, email: str, company: str, details: str = "") -> str:
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO prospect_data (name, email, company, details, created_at) VALUES (?, ?, ?, ?, ?)",
            (name, email, company, details, datetime.now().isoformat())
        )
        conn.commit()
        conn.close()
        return f"✅ Prospect {name} added successfully."
    except sqlite3.IntegrityError:
        return f"❌ Prospect with email {email} already exists."
    except Exception as e:
        return f"❌ Error adding prospect: {str(e)}"

def update_prospect(email: str, name: str = None, company: str = None, details: str = None) -> str:
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        update_fields = []
        values = []
        
        if name:
            update_fields.append("name = ?")
            values.append(name)
        if company:
            update_fields.append("company = ?")
            values.append(company)
        if details:
            update_fields.append("details = ?")
            values.append(details)
        
        if not update_fields:
            return "❌ No fields to update."
        
        values.append(email)
        cursor.execute(f"UPDATE prospect_data SET {', '.join(update_fields)} WHERE email = ?", values)
        
        if cursor.rowcount == 0:
            conn.close()
            return "❌ Prospect not found."
        
        conn.commit()
        conn.close()
        return f"✅ Prospect {email} updated successfully."
        
    except Exception as e:
        return f"❌ Error updating prospect: {str(e)}"

def get_prospect(email: str) -> str:
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name, email, company, details FROM prospect_data WHERE email=?", (email,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return f"Name: {row[0]}, Email: {row[1]}, Company: {row[2]}, Details: {row[3]}"
        return "❌ Prospect not found."
    except Exception as e:
        return f"❌ Error getting prospect: {str(e)}"

def list_all_prospects() -> str:
    """Get all prospects from the database."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name, email, company, details FROM prospect_data ORDER BY name")
        rows = cursor.fetchall()
        conn.close()
        
        if not rows:
            return "📭 No prospects found in database."
        
        result = f"📋 **ALL PROSPECTS ({len(rows)} total):**\n\n"
        for row in rows:
            result += f"• {row[0]} ({row[2]}) - {row[1]}\n"
            if row[3]:  # If details exist
                result += f"  Notes: {row[3]}\n"
            result += "\n"
        
        return result
        
    except Exception as e:
        return f"❌ Error listing prospects: {str(e)}"


# Initialize on import
init_db()