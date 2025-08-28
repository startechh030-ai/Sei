from flask import Flask, request, jsonify
import sqlite3
from datetime import datetime

app = Flask(__name__)
DB_FILE = "db.sqlite"

# ---------- DATABASE SETUP ----------
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    # Users table
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        balance REAL DEFAULT 0
    )''')
    # Deposits table
    c.execute('''CREATE TABLE IF NOT EXISTS deposits (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        amount REAL,
        date TEXT
    )''')
    # Withdrawals table
    c.execute('''CREATE TABLE IF NOT EXISTS withdrawals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        amount REAL,
        date TEXT
    )''')
    conn.commit()
    conn.close()

init_db()

def query_db(query, args=(), one=False):
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cur = conn.execute(query, args)
    rv = cur.fetchall()
    conn.commit()
    conn.close()
    return (rv[0] if rv else None) if one else rv

# ---------- ROUTES ----------
@app.route("/register", methods=["POST"])
def register():
    data = request.get_json()
    username = data.get("username")
    if not username:
        return jsonify({"error": "Username required"}), 400
    
    try:
        query_db("INSERT INTO users (username) VALUES (?)", (username,))
        return jsonify({"message": "User registered", "username": username})
    except:
        return jsonify({"error": "User already exists"}), 400

@app.route("/deposit", methods=["POST"])
def deposit():
    data = request.get_json()
    username, amount = data.get("username"), data.get("amount")
    user = query_db("SELECT * FROM users WHERE username=?", (username,), one=True)
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    query_db("UPDATE users SET balance=balance+? WHERE username=?", (amount, username))
    query_db("INSERT INTO deposits (user_id, amount, date) VALUES (?, ?, ?)", 
             (user["id"], amount, datetime.now().isoformat()))
    return jsonify({"message": f"Deposited {amount} to {username}"})

@app.route("/withdraw", methods=["POST"])
def withdraw():
    data = request.get_json()
    username, amount = data.get("username"), data.get("amount")
    user = query_db("SELECT * FROM users WHERE username=?", (username,), one=True)
    if not user:
        return jsonify({"error": "User not found"}), 404
    if user["balance"] < amount:
        return jsonify({"error": "Insufficient balance"}), 400
    
    query_db("UPDATE users SET balance=balance-? WHERE username=?", (amount, username))
    query_db("INSERT INTO withdrawals (user_id, amount, date) VALUES (?, ?, ?)", 
             (user["id"], amount, datetime.now().isoformat()))
    return jsonify({"message": f"Withdrew {amount} from {username}"})

@app.route("/balance/<username>", methods=["GET"])
def balance(username):
    user = query_db("SELECT * FROM users WHERE username=?", (username,), one=True)
    if not user:
        return jsonify({"error": "User not found"}), 404
    return jsonify({"username": username, "balance": user["balance"]})

@app.route("/history/<username>", methods=["GET"])
def history(username):
    user = query_db("SELECT * FROM users WHERE username=?", (username,), one=True)
    if not user:
        return jsonify({"error": "User not found"}), 404
    deposits = query_db("SELECT amount, date FROM deposits WHERE user_id=?", (user["id"],))
    withdrawals = query_db("SELECT amount, date FROM withdrawals WHERE user_id=?", (user["id"],))
    return jsonify({
        "deposits": [dict(d) for d in deposits],
        "withdrawals": [dict(w) for w in withdrawals]
    })

@app.route("/")
def home():
    return jsonify({"message": "VestupDB API is running ✅"})

if __name__ == "__main__":
    app.run(debug=True)