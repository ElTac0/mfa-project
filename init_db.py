import sqlite3

# Connect (creates the file if it doesn't exist)
conn = sqlite3.connect("mfa.db")
cur = conn.cursor()

# One table holding users + their temporary OTP state
cur.execute("""
CREATE TABLE IF NOT EXISTS users (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    username        TEXT    UNIQUE NOT NULL,
    password_hash   TEXT    NOT NULL,
    phone           TEXT    NOT NULL,
    otp_code        TEXT,
    otp_expires_at  INTEGER,
    failed_attempts INTEGER NOT NULL DEFAULT 0,
    locked_until    INTEGER
)
""")

conn.commit()
conn.close()
print("Database initialized: mfa.db")