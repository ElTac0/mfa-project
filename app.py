import os
import sqlite3
import bcrypt
import secrets
import time
import smtplib
from email.message import EmailMessage
from flask import Flask, request, jsonify, session
from dotenv import load_dotenv

load_dotenv()

EMAIL_ADDRESS      = os.getenv("EMAIL_ADDRESS")
EMAIL_APP_PASSWORD = os.getenv("EMAIL_APP_PASSWORD")
SMS_GATEWAY        = os.getenv("SMS_GATEWAY")

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY")
DB = "mfa.db"


def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row   
    return conn


def send_sms(phone, message):
    # phone is stored as +1XXXXXXXXXX. strip to the 10 digits
    digits = phone.lstrip("+")
    if digits.startswith("1"):
        digits = digits[1:]
    recipient = f"{digits}{SMS_GATEWAY}"

    msg = EmailMessage()
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = recipient
    msg.set_content(message)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=15) as server:
        server.login(EMAIL_ADDRESS, EMAIL_APP_PASSWORD)
        server.send_message(msg)


@app.route("/register", methods=["POST"])
def register():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")
    phone    = data.get("phone")

    if not username or not password or not phone:
        return jsonify({"error": "username, password, and phone are required"}), 400

    # Hash the password (bcrypt salts automatically)
    password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())

    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO users (username, password_hash, phone) VALUES (?, ?, ?)",
            (username, password_hash.decode("utf-8"), phone)
        )
        conn.commit()
    except sqlite3.IntegrityError:
        return jsonify({"error": "username already exists"}), 409
    finally:
        conn.close()

    return jsonify({"message": f"User '{username}' registered successfully"}), 201


@app.route("/login", methods=["POST"])
def login():

    data = request.get_json()
    username = data.get("username")
    password = data.get("password")
    print(f"[DEBUG] Looking up username: {username}")
    if not username or not password:
        return jsonify({"error": "username and password are required"}), 400

    conn = get_db()
    user = conn.execute(
        "SELECT * FROM users WHERE username = ?", (username,)
    ).fetchone()

    # Unknown user, generic rejection, no lockout tracking
    if user is None:
        conn.close()
        return jsonify({"error": "invalid credentials"}), 401

    now = int(time.time())

    #Lockout check
    if user["locked_until"] is not None and now < user["locked_until"]:
        remaining = user["locked_until"] - now
        conn.close()
        return jsonify({
            "error": f"account locked due to too many failed attempts. try again in {remaining} seconds"
        }), 403

    #Password check
    if not bcrypt.checkpw(password.encode("utf-8"), user["password_hash"].encode("utf-8")):
        # Wrong password, increment failed attempts
        attempts = user["failed_attempts"] + 1

        if attempts >= 5:
            # Lock the account for 15 minutes and reset the counter
            lock_until = now + 300
            conn.execute(
                "UPDATE users SET failed_attempts = 0, locked_until = ? WHERE username = ?",
                (lock_until, username)
            )
            conn.commit()
            conn.close()
            return jsonify({
                "error": "too many failed attempts. account locked for 15 minutes"
            }), 403
        else:
            conn.execute(
                "UPDATE users SET failed_attempts = ? WHERE username = ?",
                (attempts, username)
            )
            conn.commit()
            conn.close()
            return jsonify({
                "error": f"invalid credentials. {5 - attempts} attempts remaining"
            }), 401

    #Password correct, reset lockout state, proceed to OTP 
    otp = str(secrets.randbelow(1000000)).zfill(6)
    expires_at = now + 300

    conn.execute(
        "UPDATE users SET otp_code = ?, otp_expires_at = ?, failed_attempts = 0, locked_until = NULL WHERE username = ?",
        (otp, expires_at, username)
    )
    conn.commit()
    conn.close()

    try:
        send_sms(user["phone"], f"Your verification code is {otp}")
    except Exception as e:
        return jsonify({"error": f"failed to send SMS: {e}"}), 500

    return jsonify({"message": "password verified, OTP sent to your phone"}), 200


@app.route("/verify", methods=["POST"])
def verify():
    data = request.get_json()
    username = data.get("username")
    code     = data.get("code")

    if not username or not code:
        return jsonify({"error": "username and code are required"}), 400

    conn = get_db()
    user = conn.execute(
        "SELECT * FROM users WHERE username = ?", (username,)
    ).fetchone()

    if user is None:
        conn.close()
        return jsonify({"error": "invalid credentials"}), 401

    # No code was ever issued 
    if user["otp_code"] is None:
        conn.close()
        return jsonify({"error": "no active code, please log in first"}), 400

    # Expiry check
    if int(time.time()) > user["otp_expires_at"]:
        conn.close()
        return jsonify({"error": "verification code expired"}), 401

    # Wrong code
    if code != user["otp_code"]:
        conn.close()
        return jsonify({"error": "invalid verification code"}), 401

    # Both factors passed, clear the code so it can't be reused
    conn.execute(
        "UPDATE users SET otp_code = NULL, otp_expires_at = NULL WHERE username = ?",
        (username,)
    )
    conn.commit()
    conn.close()
    session["authenticated"] = True
    session["username"] = username

    return jsonify({"message": "authentication successful, access granted"}), 200

@app.route("/dashboard", methods=["GET"])
def dashboard():
    if not session.get("authenticated"):
        return jsonify({"error": "unauthorized, please complete authentication"}), 401
    return jsonify({"message": f"Welcome, {session['username']}! This is protected content."}), 200

@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"message": "logged out"}), 200

if __name__ == "__main__":
    app.run(debug=True, ssl_context=("certs/server.crt", "certs/server.key"))