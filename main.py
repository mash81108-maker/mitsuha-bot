import os
import sqlite3
import random
import threading
import time
from datetime import datetime, timedelta, date
from flask import Flask
import telebot

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
FACTIONS = [
    "🎀 Dreamy Dolls",
    "👑 Pretty Princesses",
    "🌸 Blossom Babes",
    "💜 Lavender Ladies",
    "💅 Slay Sisters",
    "🦋 Velvet Vixens",
    "🌹 Rosy Roses"
]

VALID_BADGES = [
    "🌸 Newbie Babe",
    "✨ Shining Star",
    "🌟 Star Queen",
    "🔥 Streak Lady",
    "⚡ Unstoppable Princess",
    "💖 Faction Angel",
    "✨ EMPRESS"
]

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
                exp INTEGER DEFAULT 0,
                level INTEGER DEFAULT 1,
                warns INTEGER DEFAULT 0,
                faction TEXT DEFAULT 'Unassigned',
                msg_count INTEGER DEFAULT 0,
                streak INTEGER DEFAULT 1,
                last_active_date TEXT,
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
def get_or_create_user(user_id, chat_id, username):
    now_dt = datetime.utcnow()
    now_str = now_dt.isoformat()
    today_str = str(date.today())

    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        row = cur.fetchone()
        
        if not row:
            assigned_faction = random.choice(FACTIONS)
            cur.execute("""
                INSERT INTO users (user_id, chat_id, username, last_active, last_active_date, faction, msg_count, streak)
                VALUES (?, ?, ?, ?, ?, ?, 1, 1)
            """, (user_id, chat_id, username or "User", now_str, today_str, assigned_faction))
            conn.commit()
            
            # Grant Newbie Badge Automatically
            cur.execute("INSERT OR IGNORE INTO badges (user_id, badge_name) VALUES (?, ?)", (user_id, "🌸 Newbie Babe"))
            conn.commit()
            
            cur.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            row = cur.fetchone()
        else:
            # Streak calculation
            last_date_str = row["last_active_date"]
            current_streak = row["streak"]
            if last_date_str:
                last_date = datetime.strptime(last_date_str, "%Y-%m-%d").date()
                delta = (date.today() - last_date).days
                if delta == 1:
                    current_streak += 1
                elif delta > 1:
                    current_streak = 1
            
            cur.execute("""
                UPDATE users 
                SET last_active = ?, last_active_date = ?, username = ?, msg_count = msg_count + 1, streak = ? 
                WHERE user_id = ?
            """, (now_str, today_str, username or "User", current_streak, user_id))
            conn.commit()

        return dict(row)

def check_auto_badges(user_id):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT msg_count, exp, streak FROM users WHERE user_id = ?", (user_id,))
        user = cur.fetchone()
        if not user:
            return

        msg_count = user["msg_count"]
        exp = user["exp"]
        streak = user["streak"]

        badge_rules = [
            ("🌸 Newbie Babe", True),
            ("✨ Shining Star", msg_count >= 100),
            ("🌟 Star Queen", msg_count >= 1000),
            ("🔥 Streak Lady", streak >= 7),
            ("⚡ Unstoppable Princess", streak >= 30),
            ("💖 Faction Angel", exp >= 1000),
            ("✨ EMPRESS", exp >= 10000)
        ]

        for badge_name, condition in badge_rules:
            if condition:
                cur.execute("INSERT OR IGNORE INTO badges (user_id, badge_name) VALUES (?, ?)", (user_id, badge_name))
        conn.commit()

def get_user_badges(user_id):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT badge_name FROM badges WHERE user_id = ?", (user_id,))
        rows = cur.fetchall()
        return [row["badge_name"] for row in rows]

def add_exp(user_id, exp_amount):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT exp FROM users WHERE user_id = ?", (user_id,))
        row = cur.fetchone()
        if row:
            new_exp = row["exp"] + exp_amount
            new_level = 1 + (new_exp // 100)
            cur.execute("UPDATE users SET exp = ?, level = ? WHERE user_id = ?", (new_exp, new_level, user_id))
            conn.commit()

# ---------------------------------------------------------
# BACKGROUND DAEMONS (Auto-Kick)
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

# ---------------------------------------------------------
# COMMANDS & HANDLERS
# ---------------------------------------------------------
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    welcome_text = (
        "<b>System Online</b>\n\n"
        "<b>User Commands:</b>\n"
        "/profile - View rank, EXP, streak, faction & badges\n\n"
        "<b>Admin Commands:</b>\n"
        "/warn | /mute | /kick | /ban | /unban | /pin\n"
        "/addbadge [Badge Name] - Manually give an official badge\n"
        "/backup - DM full SQLite database backup"
    )
    bot.reply_to(message, welcome_text)

@bot.message_handler(commands=['profile'])
def show_profile(message):
    user_id = message.from_user.id
    user_data = get_or_create_user(user_id, message.chat.id, message.from_user.username)
    check_auto_badges(user_id)
    user_badges = get_user_badges(user_id)
    
    badges_display = "\n".join(f"• {b}" for b in user_badges) if user_badges else "None"

    profile_msg = (
        f"<b>User Profile:</b> @{user_data['username']}\n"
        f"<b>Faction:</b> {user_data['faction']}\n"
        f"<b>Level:</b> {user_data['level']} (EXP: {user_data['exp']})\n"
        f"<b>Streak:</b> {user_data['streak']} Days 🔥\n"
        f"<b>Messages:</b> {user_data['msg_count']}\n\n"
        f"<b>Badges:</b>\n{badges_display}\n\n"
        f"<b>Warnings:</b> {user_data['warns']}/3"
    )
    bot.reply_to(message, profile_msg)

@bot.message_handler(commands=['addbadge'])
def add_badge(message):
    if bot.get_chat_member(message.chat.id, message.from_user.id).status not in ['administrator', 'creator']:
        return
    if not message.reply_to_message:
        bot.reply_to(message, "Reply to a user's message to grant a badge.")
        return

    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        valid_list = "\n".join(f"• <code>{b}</code>" for b in VALID_BADGES)
        bot.reply_to(message, f"Provide a valid badge name!\n\n<b>Allowed Badges:</b>\n{valid_list}")
        return

    badge_name = args[1].strip()
    if badge_name not in VALID_BADGES:
        bot.reply_to(message, "⚠️ Invalid badge name! Select only from official system badges.")
        return

    target_id = message.reply_to_message.from_user.id
    target_user = message.reply_to_message.from_user.username or "User"

    get_or_create_user(target_id, message.chat.id, target_user)

    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("INSERT OR IGNORE INTO badges (user_id, badge_name) VALUES (?, ?)", (target_id, badge_name))
        conn.commit()

    bot.reply_to(message, f"Badge <b>{badge_name}</b> successfully awarded to @{target_user}!")

@bot.message_handler(commands=['warn'])
def warn_user(message):
    if bot.get_chat_member(message.chat.id, message.from_user.id).status not in ['administrator', 'creator']:
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
        bot.reply_to(message, "Backup sent to Admin DM.")
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
        check_auto_badges(message.from_user.id)

# ---------------------------------------------------------
# MAIN EXECUTION
# ---------------------------------------------------------
if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    threading.Thread(target=inactivity_daemon, daemon=True).start()
    bot.infinity_polling(skip_pending=True)
