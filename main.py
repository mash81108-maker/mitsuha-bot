import os
import sqlite3
import random
import threading
import time
from datetime import datetime, timedelta
from flask import Flask
import telebot
from telebot import types

# ---------------------------------------------------------
# CONFIGURATION & INITIALIZATION
# ---------------------------------------------------------
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
DB_FILE = "bot_data.db"

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is running online 24/7!"

def run_flask():
    port = int(os.getenv("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

# ---------------------------------------------------------
# DATABASE ENGINE (SQLite + WAL Mode)
# ---------------------------------------------------------
def get_db():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                chat_id INTEGER,
                username TEXT,
                hearts INTEGER DEFAULT 0,
                exp INTEGER DEFAULT 0,
                level INTEGER DEFAULT 1,
                warns INTEGER DEFAULT 0,
                faction TEXT DEFAULT 'Unassigned',
                duo_partner INTEGER DEFAULT NULL,
                last_active TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS badges (
                user_id INTEGER,
                badge_name TEXT,
                PRIMARY KEY (user_id, badge_name)
            )
        """)
        conn.commit()

init_db()

# ---------------------------------------------------------
# HELPER FUNCTIONS & PROGRESSION LOGIC
# ---------------------------------------------------------
FACTIONS = ["Solaris", "Lunaris", "Aether"]

def get_or_create_user(user_id, chat_id, username):
    now = datetime.utcnow().isoformat()
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        row = cur.fetchone()
        if not row:
            assigned_faction = random.choice(FACTIONS)
            cur.execute("""
                INSERT INTO users (user_id, chat_id, username, last_active, faction)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, chat_id, username, now, assigned_faction))
            conn.commit()
            cur.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            row = cur.fetchone()
        else:
            cur.execute("UPDATE users SET last_active = ?, username = ? WHERE user_id = ?", (now, username, user_id))
            conn.commit()
        return dict(row)

def add_exp(user_id, exp_amount):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT exp, level FROM users WHERE user_id = ?", (user_id,))
        row = cur.fetchone()
        if row:
            new_exp = row["exp"] + exp_amount
            new_level = 1 + (new_exp // 100)
            cur.execute("UPDATE users SET exp = ?, level = ? WHERE user_id = ?", (new_exp, new_level, user_id))
            conn.commit()

# ---------------------------------------------------------
# BACKGROUND DAEMONS (Auto-Kick & Polls)
# ---------------------------------------------------------
def inactivity_daemon():
    while True:
        try:
            cutoff = (datetime.utcnow() - timedelta(days=7)).isoformat()
            with get_db() as conn:
                cur = conn.cursor()
                cur.execute("SELECT user_id, chat_id FROM users WHERE last_active < ?", (cutoff,))
                inactive_users = cur.fetchall()
                for user in inactive_users:
                    try:
                        bot.ban_chat_member(user["chat_id"], user["user_id"])
                        bot.unban_chat_member(user["chat_id"], user["user_id"])
                    except Exception:
                        pass
        except Exception as e:
            print(f"Inactivity Error: {e}")
        time.sleep(86400)

def daily_poll_daemon():
    polls = [
        ("Daily Check-in: How is your activity today?", ["High", "Medium", "Low"]),
        ("Which faction is dominant today?", ["Solaris", "Lunaris", "Aether"])
    ]
    while True:
        time.sleep(43200)
        # Add automated group poll dispatch logic here as needed

# ---------------------------------------------------------
# MODERATION & USER COMMANDS
# ---------------------------------------------------------
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    welcome_text = (
        "<b>System Online</b>\n\n"
        "<b>User Commands:</b>\n"
        "/profile - View rank, hearts, EXP & faction\n"
        "/heart - Give a heart to a user (reply to message)\n\n"
        "<b>Admin Commands:</b>\n"
        "/warn | /mute | /kick | /ban | /unban | /pin\n"
        "/backup - DM full SQLite database backup"
    )
    bot.reply_to(message, welcome_text)

@bot.message_handler(commands=['profile'])
def show_profile(message):
    user_id = message.from_user.id
    user_data = get_or_create_user(user_id, message.chat.id, message.from_user.username)
    profile_msg = (
        f"<b>User Profile:</b> @{user_data['username']}\n"
        f"<b>Level:</b> {user_data['level']} (EXP: {user_data['exp']})\n"
        f"<b>Hearts:</b> {user_data['hearts']} ❤️\n"
        f"<b>Faction:</b> {user_data['faction']}\n"
        f"<b>Warnings:</b> {user_data['warns']}/3"
    )
    bot.reply_to(message, profile_msg)

@bot.message_handler(commands=['warn'])
def warn_user(message):
    if not bot.get_chat_member(message.chat.id, message.from_user.id).status in ['administrator', 'creator']:
        return
    if not message.reply_to_message:
        bot.reply_to(message, "Reply to a user's message to warn them.")
        return

    target_id = message.reply_to_message.from_user.id
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("UPDATE users SET warns = warns + 1 WHERE user_id = ?", (target_id,))
        conn.commit()
        cur.execute("SELECT warns FROM users WHERE user_id = ?", (target_id,))
        warns = cur.fetchone()["warns"]

    if warns >= 3:
        bot.ban_chat_member(message.chat.id, target_id)
        bot.reply_to(message, f"User reached {warns} warnings and was banned.")
    else:
        bot.reply_to(message, f"User warned ({warns}/3).")

@bot.message_handler(commands=['backup'])
def backup_db(message):
    if message.from_user.id != ADMIN_ID:
        return
    try:
        with open(DB_FILE, 'rb') as doc:
            bot.send_document(message.from_user.id, doc, caption="Database Backup")
        bot.reply_to(message, "Backup dispatched to Admin DM.")
    except Exception as e:
        bot.reply_to(message, f"Backup failed: {e}")

# ---------------------------------------------------------
# GENERAL MESSAGE TRACKER
# ---------------------------------------------------------
@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    if message.chat.type in ['group', 'supergroup']:
        get_or_create_user(message.from_user.id, message.chat.id, message.from_user.username)
        add_exp(message.from_user.id, random.randint(5, 15))

# ---------------------------------------------------------
# MAIN EXECUTION
# ---------------------------------------------------------
if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    threading.Thread(target=inactivity_daemon, daemon=True).start()
    threading.Thread(target=daily_poll_daemon, daemon=True).start()
    bot.infinity_polling(skip_pending=True)
