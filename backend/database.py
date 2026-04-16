import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'simchaleads.db')


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_db()
    cursor = conn.cursor()

    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS engagements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chatan_first TEXT NOT NULL,
            chatan_last TEXT,
            kallah_first TEXT NOT NULL,
            kallah_last TEXT,
            source_url TEXT,
            source_caption TEXT,
            post_date TEXT,
            scraped_at TEXT NOT NULL DEFAULT (datetime('now')),
            matched INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS contacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            phone TEXT,
            email TEXT,
            address TEXT,
            city TEXT,
            community TEXT,
            source TEXT DEFAULT 'smartlist',
            imported_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS matches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            engagement_id INTEGER NOT NULL,
            contact_id INTEGER NOT NULL,
            match_type TEXT NOT NULL,  -- 'chatan', 'kallah', 'chatan_family', 'kallah_family'
            confidence REAL NOT NULL DEFAULT 1.0,
            matched_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (engagement_id) REFERENCES engagements(id),
            FOREIGN KEY (contact_id) REFERENCES contacts(id),
            UNIQUE(engagement_id, contact_id)
        );

        CREATE TABLE IF NOT EXISTS drafts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            engagement_id INTEGER NOT NULL,
            match_id INTEGER,
            recipient_name TEXT NOT NULL,
            recipient_phone TEXT,
            recipient_email TEXT,
            channel TEXT NOT NULL DEFAULT 'sms',  -- 'sms', 'whatsapp', 'email'
            subject TEXT,
            message TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'draft',  -- 'draft', 'approved', 'sent', 'failed'
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            sent_at TEXT,
            FOREIGN KEY (engagement_id) REFERENCES engagements(id),
            FOREIGN KEY (match_id) REFERENCES matches(id)
        );

        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );

        -- Indexes for fast lookups
        CREATE INDEX IF NOT EXISTS idx_contacts_name ON contacts(last_name, first_name);
        CREATE INDEX IF NOT EXISTS idx_engagements_names ON engagements(chatan_last, kallah_last);
        CREATE INDEX IF NOT EXISTS idx_drafts_status ON drafts(status);
    """)

    # Insert default settings
    defaults = {
        'business_name': 'CodePros',
        'discount_percent': '5',
        'instagram_account': 'simchaspot',
        'message_template_sms': 'Mazel Tov {recipient_name} on the engagement of {chatan} & {kallah}! 🎉\n\nFrom all of us at {business_name}, we wish you a beautiful journey ahead.\n\nAs a special mazel tov gift, we\'d like to offer you {discount}% off our services.\n\nReach out anytime to learn more!\n- {business_name}',
        'message_template_whatsapp': 'Mazel Tov {recipient_name} on the engagement of {chatan} & {kallah}! 🎉\n\nFrom all of us at {business_name}, we wish you a beautiful journey ahead.\n\nAs a special mazel tov gift, we\'d like to offer you {discount}% off our services.\n\nReach out anytime to learn more!\n- {business_name}',
        'message_template_email': 'Dear {recipient_name},\n\nMazel Tov on the engagement of {chatan} & {kallah}! 🎉\n\nFrom all of us at {business_name}, we wish you a beautiful journey ahead.\n\nAs a special mazel tov gift, we\'d like to offer you {discount}% off our services.\n\nWe\'d love to help make this simcha even more special. Feel free to reach out anytime to learn more about what we offer.\n\nWith warm wishes,\n{business_name}',
        'email_subject_template': 'Mazel Tov from {business_name}! 🎉',
    }
    for key, value in defaults.items():
        cursor.execute(
            "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
            (key, value)
        )

    conn.commit()
    conn.close()


if __name__ == '__main__':
    init_db()
    print(f"Database initialized at {DB_PATH}")
