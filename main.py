import os
import time
import sqlite3
import random
from datetime import datetime, timedelta
from threading import Thread
from flask import Flask
import telebot

# --- 🌸 FRAMEWORK INITIALIZATION ---
app = Flask('')

@app.route('/')
def home():
    return "⛩️ Mitsuha Bot is Live & Wrapped in Pastel Magic!"

# 🔒 Token Configuration (Render Environment Variable)
TOKEN = os.environ.get('BOT_TOKEN')
bot = telebot.TeleBot(TOKEN)

# Fixed Admin aur Group IDs
YOUR_USER_ID = 8787638791
GROUP_CHAT_ID = -1003983125875

DB_FILE = "mitsuha_bot.db"

# --- 📁 DATABASE HELPER FUNCTIONS (THREAD-SAFE) ---
def get_db_connection():
    """Opens a thread-safe connection to the SQLite database."""
    conn = sqlite3.connect(DB_FILE, timeout=15)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes the database schema with WAL mode enabled for safe concurrent writes."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL;")
    
    # Users Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        first_name TEXT,
        hearts INTEGER DEFAULT 0,
        msg_count INTEGER DEFAULT 0,
        daily_streak INTEGER DEFAULT 0,
        last_daily TEXT,
        join_date TEXT,
        last_msg_time REAL DEFAULT 0
    )
    """)
    
    # Besties Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS besties (
        user_one INTEGER,
        user_two INTEGER,
        status TEXT,
        timestamp REAL,
        PRIMARY KEY (user_one, user_two)
    )
    """)
    
    # Achievements Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS achievements (
        user_id INTEGER,
        achievement_id TEXT,
        unlocked_at TEXT,
        PRIMARY KEY (user_id, achievement_id)
    )
    """)
    
    # Message Log Table for Advanced Group Analytics
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS message_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        timestamp TEXT
    )
    """)
    
    conn.commit()
    conn.close()

# Initialize database structures immediately
init_db()


# --- 🎀 UTILITY HELPERS & LEVEL CONFIGURATION ---
LEVELS = [
    (10000, "Angel Queen 👼✨"),
    (7500, "Heart Stealer 💖"),
    (5500, "Cutie Princess 👑"),
    (4000, "Vibe Matcher 🎵"),
    (2800, "Group Bestie 🎀"),
    (1800, "Sweetie Pie 🍰"),
    (1000, "Chat Buddy 🧸"),
    (500, "Little Star ✨"),
    (200, "Soft Bubble 🫧"),
    (0, "Fresh Face 🌸")
]

def get_level_info(hearts):
    """Calculates user level, title, and remaining hearts needed for the next tier."""
    total_levels = len(LEVELS)
    for index, (threshold, title) in enumerate(LEVELS):
        if hearts >= threshold:
            current_level = total_levels - index
            if index == 0:
                return current_level, title, 0  # Max Level reached
            next_threshold = LEVELS[index - 1][0]
            hearts_needed = next_threshold - hearts
            return current_level, title, hearts_needed
    return 1, "Fresh Face 🌸", 200

def escape_html(text):
    """Safeguards text inputs against Telegram HTML parsing crashes."""
    if not text:
        return "Kawaii Member"
    return text.replace('<', '&lt;').replace('>', '&gt;')

def resolve_username_from_cache(username_str):
    """Resolves a typed username to a Telegram user_id using the internal database cache."""
    clean_username = username_str.replace("@", "").strip()
    conn = get_db_connection()
    row = conn.execute("SELECT user_id FROM users WHERE LOWER(username) = LOWER(?)", (clean_username,)).fetchone()
    conn.close()
    return row["user_id"] if row else None


# --- 🗓️ 2026 FESTIVAL & SEASONAL EVENTS ENGINE ---
EVENTS_CONFIG = {
    "New Year": {"start_msg": "01-01", "end_msg": "01-02", "badge": "🥂✨", "bonus": 5, "text": "Happy New Year, cuties! Let's fill this year with sweet memories!"},
    "Valentine's Day": {"start_msg": "02-14", "end_msg": "02-15", "badge": "💝🌸", "bonus": 10, "text": "Happy Valentine's Day! Spread love, kindness, and pastel sparkles today!"},
    "Holi": {"start_msg": "2026-03-03", "end_msg": "2026-03-04", "badge": "🎨🌈", "bonus": 5, "text": "Bura na mano Holi hai! Wishing you a vibrant, colorful, and sweet day!"},
    "Eid al-Fitr": {"start_msg": "2026-03-20", "end_msg": "2026-03-21", "badge": "🌙⭐", "bonus": 5, "text": "Eid Mubarak to all my beautiful girls! Stay blessed and happy!"},
    "Raksha Bandhan": {"start_msg": "2026-08-28", "end_msg": "2026-08-29", "badge": "🧿🎀", "bonus": 5, "text": "Happy Raksha Bandhan! Celebrating the sweet bond of protection and care!"},
    "Halloween": {"start_msg": "10-31", "end_msg": "11-01", "badge": "🎃🍬", "bonus": 5, "text": "Spooky but sweet! Happy Halloween, my adorable little witches!"},
    "Diwali": {"start_msg": "2026-11-08", "end_msg": "2026-11-09", "badge": "🪔✨", "bonus": 10, "text": "Happy Diwali, beauties! May your lives shine brighter than the prettiest diyas!"},
    "Christmas": {"start_msg": "12-25", "end_msg": "12-26", "badge": "🎄🎁", "bonus": 10, "text": "Merry Christmas, sweet angels! May Santa bring you infinite joy!"}
}

def get_active_event():
    """Evaluates current calendar date against tracking windows to return active events."""
    now = datetime.now()
    current_date_str = now.strftime("%Y-%m-%d")
    current_md_str = now.strftime("%m-%d")
    
    for event_name, info in EVENTS_CONFIG.items():
        if "-" in info["start_msg"] and len(info["start_msg"]) > 5:
            # Match strict calendar dates for floating holidays
            if info["start_msg"] <= current_date_str <= info["end_msg"]:
                return event_name, info
        else:
            # Match month-day blocks for structural fixed events
            if info["start_msg"] <= current_md_str <= info["end_msg"]:
                return event_name, info
    return None, None


# --- 🏆 SYSTEM ACHIEVEMENT TRACKER ---
ACHIEVEMENTS_BOOK = {
    "first_msg": {"badge": "🌱", "title": "First Step", "desc": "Sent your very first message in Kawaii Club!"},
    "msg_100": {"badge": "💬", "title": "Chatty Angel", "desc": "Reached a milestone of 100 messages!"},
    "hearts_1000": {"badge": "❤️", "title": "Heart Collector", "desc": "Accumulated 1,000 Hearts!"},
    "streak_7": {"badge": "🔥", "title": "Unstoppable", "desc": "Maintained a 7-day daily checking streak!"},
    "top_1": {"badge": "👑", "title": "Club Queen", "desc": "Ranked #1 on the active sweethearts list!"},
    "event_winner": {"badge": "🎀", "title": "Festival Star", "desc": "Participated or won an active group seasonal event!"}
}

def grant_achievement(user_id, achievement_id, message):
    """Validates and persists unlocked achievements, triggering an aesthetic confirmation."""
    conn = get_db_connection()
    exists = conn.execute("SELECT 1 FROM achievements WHERE user_id = ? AND achievement_id = ?", (user_id, achievement_id)).fetchone()
    
    if not exists:
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        conn.execute("INSERT INTO achievements (user_id, achievement_id, unlocked_at) VALUES (?, ?, ?)", (user_id, achievement_id, now_str))
        conn.commit()
        conn.close()
        
        ach = ACHIEVEMENTS_BOOK[achievement_id]
        clean_name = escape_html(message.from_user.first_name)
        announcement = (
            f"✨ <b>𝖪𝖺𝗐𝖺𝗂𝗂 𝖠𝖼𝗁𝗂𝖾𝗏𝖾𝗆𝖾𝗇𝗍 𝖴𝗇𝗅𝗈𝖼𝗄𝖾𝖽!</b> 🎀\n\n"
            f"🌸 🔔 <b>{clean_name}</b> has unlocked a new milestone:\n"
            f"{ach['badge']} <b>{ach['title']}</b> — <i>{ach['desc']}</i>\n\n"
            f"Keep shining and spreading cozy vibes! 💕"
        )
        bot.reply_to(message, announcement, parse_mode='HTML')
    else:
        conn.close()


# --- 🚀 CORE BACKGROUND TRACKER & HOOKS ---
@bot.message_handler(func=lambda message: message.chat.type in ['group', 'supergroup'], content_types=['text', 'photo', 'sticker', 'animation', 'video', 'document'])
def track_group_activities(message):
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name
    now_time = time.time()
    now_date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    conn = get_db_connection()
    user_row = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
    
    # Base configuration values
    event_name, event_info = get_active_event()
    base_earn = 10
    bonus_applied = 0
    
    if event_info:
        bonus_applied += event_info["bonus"]
    
    total_earned = base_earn + bonus_applied
    
    if not user_row:
        conn.execute("""
            INSERT INTO users (user_id, username, first_name, hearts, msg_count, join_date, last_msg_time) 
            VALUES (?, ?, ?, ?, 1, ?, ?)
        """, (user_id, username, first_name, total_earned, now_date_str, now_time))
        current_msg_count = 1
        current_hearts = total_earned
        last_peer_time = 0
    else:
        current_msg_count = user_row["msg_count"] + 1
        current_hearts = user_row["hearts"] + total_earned
        last_peer_time = user_row["last_msg_time"]
        
        conn.execute("""
            UPDATE users 
            SET username = ?, first_name = ?, hearts = ?, msg_count = ?, last_msg_time = ? 
            WHERE user_id = ?
        """, (username, first_name, current_hearts, current_msg_count, now_time, user_id))
    
    # Log transactional messages to analytical history
    conn.execute("INSERT INTO message_log (user_id, timestamp) VALUES (?, ?)", (user_id, now_date_str))
    
    # Evaluate conversational bestie bonus
    bestie_row = conn.execute("""
        SELECT * FROM besties 
        WHERE (user_one = ? OR user_two = ?) AND status = 'accepted'
    """, (user_id, user_id)).fetchone()
    
    bestie_bonus_triggered = False
    if bestie_row:
        partner_id = bestie_row["user_two"] if bestie_row["user_one"] == user_id else bestie_row["user_one"]
        partner_row = conn.execute("SELECT last_msg_time FROM users WHERE user_id = ?", (partner_id,)).fetchone()
        
        if partner_row and partner_row["last_msg_time"] > 0:
            # Add +5 hearts if conversational response occurs within a 5-minute window
            if abs(now_time - partner_row["last_msg_time"]) <= 300:
                bestie_bonus_triggered = True
                conn.execute("UPDATE users SET hearts = hearts + 5 WHERE user_id = ?", (user_id,))
                current_hearts += 5
                
    conn.commit()
    conn.close()
    
    # Handle contextual conditional achievements safely
    if current_msg_count == 1:
        grant_achievement(user_id, "first_msg", message)
    if current_msg_count == 100:
        grant_achievement(user_id, "msg_100", message)
    if current_hearts >= 1000:
        grant_achievement(user_id, "hearts_1000", message)
    if event_info and bonus_applied > 0 and current_msg_count % 30 == 0:
        grant_achievement(user_id, "event_winner", message)


# --- 📑 LEGACY CORE BOT COMMANDS ---
RULES_TEXT = """
˚₊‧꒰ა ⛩️ 🎀 𝖪𝖺𝗐𝖺𝗂𝗂 𝖢/-𝗎𝖻 𝖱𝗎𝗅𝖾𝗌 🌸 ໒꒱ ‧₊˚

1. Everyone ke saath respectful aur friendly raho! 💕
2. Chat me spamming, link sharing, ya toxicity strictly banned hai. 🚫
3. Keep the vibe cute, aesthetic, aur active! 🍥🧸
"""

GROUPS_TEXT = """
🔗 <b>𝖪𝖺𝗐𝖺𝗂𝗂 𝖢/🇺𝖻 More Groups</b> 🌸

Humare baaki groups aur community ko join karne ke liye neeche diye gaye link par click karein:

🤝 <b>Team Tamashi:</b> https://t.me/team_tamashi
"""

@bot.message_handler(commands=['start'])
def send_welcome(message):
    welcome_text = (
        "🍥 <b>Konichiwa! Main hoon Mitsuha.</b> ⛩️\n\n"
        "Main <b>Kawaii Club</b> ki official manager desk hoon. "
        "Club ke updates aur rules dekhne ke liye niche diye gaye commands use karein! 🎀✨\n\n"
        "📜 /rules - Group ke rules dekhne ke liye\n"
        "🔗 /groups - Humare baaki groups ke links dekhne ke liye\n"
        "💖 /hearts - Apne profile and hearts points check karne ke liye\n"
        "🏆 /sweethearts - Top active members dekhne ke liye"
    )
    bot.reply_to(message, welcome_text, parse_mode='HTML')

@bot.message_handler(commands=['rules'])
def send_rules(message):
    bot.reply_to(message, RULES_TEXT, parse_mode='HTML')

@bot.message_handler(commands=['groups'])
def send_groups(message):
    bot.reply_to(message, GROUPS_TEXT, parse_mode='HTML')

@bot.message_handler(commands=['hearts'])
def show_hearts(message):
    user_id = message.from_user.id
    name = escape_html(message.from_user.first_name)
    
    conn = get_db_connection()
    row = conn.execute("SELECT hearts FROM users WHERE user_id = ?", (user_id,)).fetchone()
    conn.close()
    
    if row:
        pts = row["hearts"]
        _, title, needed = get_level_info(pts)
        next_str = f" Next level ke liye <b>{needed} Hearts</b> aur chahiye! ✨" if needed > 0 else " Aap max level par ho! 👑"
        bot.reply_to(message, f"🌸 <b>{name}</b>, aapke paas kul <b>{pts} Hearts 💖</b> hain!\n📝 Title: <b>{title}</b>\n{next_str}", parse_mode='HTML')
    else:
        bot.reply_to(message, f"🌸 <b>{name}</b>, abhi aapke paas 0 Hearts hain. Chatting shuru karo aur dil jeeto! 💕", parse_mode='HTML')


# --- 👑 SYSTEM SPAM-PROOF LEADERBOARD COMMAND ---
@bot.message_handler(commands=['sweethearts'])
def show_sweethearts_leaderboard(message):
    conn = get_db_connection()
    rows = conn.execute("SELECT user_id, first_name, hearts FROM users ORDER BY hearts DESC LIMIT 10").fetchall()
    
    if not rows:
        bot.reply_to(message, "🏆 Abhi leaderboard khali hai! Group me chatting shuru karo. ✨")
        conn.close()
        return
    
    lb_text = "🏆 <b>𝖪𝖺𝗐𝖺𝗂𝗂 𝖢/🇺𝖻 Most Loved Members</b> 🌸\n\n"
    medals = ["🥇", "🥈", "🥉", "✨", "✨", "✨", "✨", "✨", "✨", "✨"]
    
    for index, row in enumerate(rows):
        clean_name = escape_html(row["first_name"])
        lb_text += f"{medals[index]} <b>{clean_name}</b> — {row['hearts']} 💖\n"
        
        # Grant top spot achievement dynamic link
        if index == 0:
            grant_achievement(row["user_id"], "top_1", message)
            
    conn.close()
    bot.reply_to(message, lb_text, parse_mode='HTML')


# --- 👥 INTERACTIVE SOCIAL & BESTIE MATRIX ---
@bot.message_handler(commands=['bestie'])
def process_bestie_command(message):
    args = message.text.split()
    if len(args) < 2:
        bot.reply_to(message, "🧁 <b>Usage:</b> /bestie @username\nApni kisi pyaari saheli ko invite bhejo! ✨", parse_mode='HTML')
        return
    
    sender_id = message.from_user.id
    sender_name = escape_html(message.from_user.first_name)
    target_username = args[1]
    
    target_id = resolve_username_from_cache(target_username)
    if not target_id:
        bot.reply_to(message, "❌ Mujhe wo member database me nahi mili. Unhein bolo group me ek baar text karein! 💕")
        return
    
    if sender_id == target_id:
        bot.reply_to(message, "🙈 Aap khud ko hi apni bestie nahi bana sakti, cutie!")
        return
    
    conn = get_db_connection()
    
    # Check conflicting relational mappings
    already_bonded = conn.execute("""
        SELECT * FROM besties 
        WHERE ((user_one = ? AND user_two = ?) OR (user_one = ? AND user_two = ?)) AND status = 'accepted'
    """, (sender_id, target_id, target_id, sender_id)).fetchone()
    
    if already_bonded:
        # Calculate matching deterministic platonic bonding score
        low = min(sender_id, target_id)
        high = max(sender_id, target_id)
        calc_pct = ((low * 7 + high * 13) % 41) + 60 # Deterministic scale between 60% and 100%
        
        bot.reply_to(message, f"🎀 Aap dono toh pehle se hi official besties ho! \n💖 Aapka friendship bond <b>{calc_pct}%</b> strong aur cute hai! ✨", parse_mode='HTML')
        conn.close()
        return
        
    pending_invite = conn.execute("""
        SELECT * FROM besties WHERE user_one = ? AND user_two = ? AND status = 'pending'
    """, (target_id, sender_id)).fetchone()
    
    if pending_invite:
        conn.execute("UPDATE besties SET status = 'accepted', timestamp = ? WHERE user_one = ? AND user_two = ?", (time.time(), target_id, sender_id))
        conn.commit()
        conn.close()
        bot.reply_to(message, f"🎉 Yayy! <b>{sender_name}</b> ne invitation accept kar liya! Ab aap dono official besties ho! 🫂💕", parse_mode='HTML')
    else:
        # Establish structural placeholder relational bond row
        conn.execute("INSERT OR REPLACE INTO besties (user_one, user_two, status, timestamp) VALUES (?, ?, 'pending', ?)", (sender_id, target_id, time.time()))
        conn.commit()
        conn.close()
        bot.reply_to(message, f"🌸 🔔 <b>{target_username}</b>, aapko {sender_name} ne apni bestie banane ke liye invite kiya hai! Connect karne ke liye respond karein: `/bestie @{escape_html(message.from_user.username)}`", parse_mode='HTML')


# --- 💳 ECONOMY & DAILY ENGAGEMENT CORE ---
@bot.message_handler(commands=['daily'])
def claim_daily_allowance(message):
    user_id = message.from_user.id
    name = escape_html(message.from_user.first_name)
    today_str = datetime.now().strftime("%Y-%m-%d")
    yesterday_str = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    
    conn = get_db_connection()
    row = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
    
    if not row:
        # Safe structural fallback insertion
        now_date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn.execute("INSERT INTO users (user_id, first_name, hearts, msg_count, daily_streak, last_daily, join_date) VALUES (?, ?, 50, 0, 1, ?, ?)", (user_id, name, today_str, now_date_str))
        conn.commit()
        conn.close()
        bot.reply_to(message, f"🎁 <b>Daily Bonus Claimed!</b>\n🌸 Welcome {name}! Aapko mile hain <b>50 Hearts 💖</b>! (Streak: 1 Day)", parse_mode='HTML')
        return
        
    if row["last_daily"] == today_str:
        bot.reply_to(message, f"🎀 🌟 <b>{name}</b>, aapne aaj ka gift pehle hi claim kar liya hai. Kal dobara aana, cutie! 🥰", parse_mode='HTML')
        conn.close()
        return
        
    # Check continuity of daily logins
    new_streak = row["daily_streak"] + 1 if row["last_daily"] == yesterday_str else 1
    reward = 50 + (new_streak * 5)
    if reward > 150: 
        reward = 150 # Upper operational bound ceiling for rewards
        
    conn.execute("UPDATE users SET hearts = hearts + ?, daily_streak = ?, last_daily = ? WHERE user_id = ?", (reward, new_streak, today_str, user_id))
    conn.commit()
    conn.close()
    
    bot.reply_to(message, f"🎁 <b>Daily Sweetness Unlocked!</b>\n💖 Aapko mile hain <b>{reward} Hearts</b>!\n🔥 Daily Streak: <b>{new_streak} Days</b>. Keep it up! ✨", parse_mode='HTML')
    
    if new_streak >= 7:
        grant_achievement(user_id, "streak_7", message)

@bot.message_handler(commands=['gift'])
def gift_hearts_allowance(message):
    args = message.text.split()
    if len(args) < 3:
        bot.reply_to(message, "🧁 <b>Usage:</b> /gift @username &lt;amount&gt;", parse_mode='HTML')
        return
        
    sender_id = message.from_user.id
    target_username = args[1]
    
    try:
        amount = int(args[2])
    except ValueError:
        bot.reply_to(message, "❌ Amount ek valid number hona chahiye, cutie!")
        return
        
    if amount <= 0:
        bot.reply_to(message, "❌ Pyaari behen, 0 ya negative hearts gift nahi kar sakti! 😉")
        return
        
    target_id = resolve_username_from_cache(target_username)
    if not target_id:
        bot.reply_to(message, "❌ Wo member database me nahi mili. Unhein bolo group me ek baar text karein!")
        return
        
    if sender_id == target_id:
        bot.reply_to(message, "🙈 Khud ko gift dekar kya milega, saheli?")
        return
        
    conn = get_db_connection()
    sender_row = conn.execute("SELECT hearts FROM users WHERE user_id = ?", (sender_id,)).fetchone()
    
    if not sender_row or sender_row["hearts"] < amount:
        bot.reply_to(message, "❌ Aapke paas itne Hearts nahi hain gift karne ke liye! 😢")
        conn.close()
        return
        
    conn.execute("UPDATE users SET hearts = hearts - ? WHERE user_id = ?", (amount, sender_id))
    conn.execute("UPDATE users SET hearts = hearts + ? WHERE user_id = ?", (amount, target_id))
    conn.commit()
    conn.close()
    
    bot.reply_to(message, f"🎉 💝 <b>Generous Angel Alert!</b>\n\n<b>{escape_html(message.from_user.first_name)}</b> ne <b>{target_username}</b> ko <b>{amount} Hearts 💖</b> gift kiye hain! Kitni pyaari dosti hai! ✨", parse_mode='HTML')

@bot.message_handler(commands=['rank'])
def show_user_rank(message):
    user_id = message.from_user.id
    name = escape_html(message.from_user.first_name)
    
    conn = get_db_connection()
    leaderboard = conn.execute("SELECT user_id, hearts FROM users ORDER BY hearts DESC").fetchall()
    
    rank = 0
    user_hearts_val = 0
    for idx, row in enumerate(leaderboard):
        if row["user_id"] == user_id:
            rank = idx + 1
            user_hearts_val = row["hearts"]
            break
            
    conn.close()
    
    if rank == 0:
        bot.reply_to(message, "🌸 Aap abhi database me listed nahi ho, thoda chat karo, cutie!")
        return
        
    _, title, needed = get_level_info(user_hearts_val)
    next_status_str = f"Next tier ke liye <b>{needed} hearts</b> baki hain!" if needed > 0 else "Aap rank heights ke peak par ho! 👑"
    
    bot.reply_to(message, f"👑 <b>𝖪𝖺𝗐𝖺𝗂𝗂 𝖢/🇺𝖻 Standing Card</b> 🌸\n\n🎯 Rank: <b>#{rank}</b> in the Club\n✨ Current Status: <b>{title}</b>\n💖 Score: <b>{user_hearts_val} Total Hearts</b>\n📈 {next_status_str}", parse_mode='HTML')


# --- 🎀 ADVANCED COMPREHENSIVE PROFILE SYSTEM ---
@bot.message_handler(commands=['profile'])
def display_user_profile(message):
    user_id = message.from_user.id
    name = escape_html(message.from_user.first_name)
    
    conn = get_db_connection()
    user_row = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
    
    if not user_row:
        bot.reply_to(message, "🌸 Mujhe aapki data profile nahi mili. Thoda chat karke history banaiye!")
        conn.close()
        return
        
    # Discover operational system rank
    leaderboard = conn.execute("SELECT user_id FROM users ORDER BY hearts DESC").fetchall()
    rank = next((idx + 1 for idx, r in enumerate(leaderboard) if r["user_id"] == user_id), "N/A")
    
    # Extract structural bestie data relationships
    bestie_row = conn.execute("""
        SELECT * FROM besties 
        WHERE ((user_one = ? OR user_two = ?)) AND status = 'accepted'
    """, (user_id, user_id)).fetchone()
    
    bestie_display = "None yet 🥺"
    if bestie_row:
        partner_id = bestie_row["user_two"] if bestie_row["user_one"] == user_id else bestie_row["user_one"]
        partner_row = conn.execute("SELECT first_name FROM users WHERE user_id = ?", (partner_id,)).fetchone()
        if partner_row:
            bestie_display = f"💝 {escape_html(partner_row['first_name'])}"
            
    # Compile unlocked badges strings
    ach_rows = conn.execute("SELECT achievement_id FROM achievements WHERE user_id = ?", (user_id,)).fetchall()
    unlocked_badges = [ACHIEVEMENTS_BOOK[r["achievement_id"]]["badge"] for r in ach_rows if r["achievement_id"] in ACHIEVEMENTS_BOOK]
    badges_display = " ".join(unlocked_badges) if unlocked_badges else "No badges yet 🌱"
    
    conn.close()
    
    hearts_val = user_row["hearts"]
    lvl, title, _ = get_level_info(hearts_val)
    
    profile_card = (
        f"˚₊‧꒰ა ⛩️ 🎀 <b>𝖪𝖺𝗐𝖺𝗂𝗂 𝖢/🇺𝖻 𝖯𝗋𝗈𝖿𝗂𝗅𝖾</b> 🌸 ໒꒱ ‧₊˚\n\n"
        f"🙋‍♀️ Name: <b>{name}</b>\n"
        f"💖 Hearts: <b>{hearts_val}</b>\n"
        f"📈 Level: <b>{lvl}</b>\n"
        f"💮 Title: <b>{title}</b>\n"
        f"🏆 Rank: <b>#{rank}</b>\n"
        f"🫂 Bestie: <b>{bestie_display}</b>\n"
        f"📊 Messages: <b>{user_row['msg_count']}</b>\n"
        f"🔥 Streak: <b>{user_row['daily_streak']} Days</b>\n"
        f"📅 Joined At: <code>{user_row['join_date'][:10]}</code>\n"
        f"🎖️ Badges: {badges_display}\n\n"
        f"<i>🌸 Stay sweet, stay cute! 🌸</i>"
    )
    bot.reply_to(message, profile_card, parse_mode='HTML')


# --- 📜 MILESTONE ACHIEVEMENTS ARCHIVE ---
@bot.message_handler(commands=['achievements'])
def display_achievements_catalog(message):
    user_id = message.from_user.id
    conn = get_db_connection()
    unlocked = [r["achievement_id"] for r in conn.execute("SELECT achievement_id FROM achievements WHERE user_id = ?", (user_id,)).fetchall()]
    conn.close()
    
    catalog_text = "✨ <b>𝖪𝖺𝗐𝖺𝗂𝗂 𝖢𝗅𝗎𝖻 𝖠𝖼𝗂𝖾𝗏𝖾𝗆𝖾𝗇𝗍𝗌 𝖡𝗈𝗈𝗄</b> 🎀\n\n"
    
    for ach_id, data in ACHIEVEMENTS_BOOK.items():
        status_check = "✅ Unlocked" if ach_id in unlocked else "🔒 Locked"
        catalog_text += f"{data['badge']} <b>{data['title']}</b> ({status_check})\n<i>ℹ️ {data['desc']}</i>\n\n"
        
    bot.reply_to(message, catalog_text, parse_mode='HTML')


# --- 📊 ANALYTICAL GROUP STATS ENGINE ---
@bot.message_handler(commands=['groupstats'])
def show_group_metrics(message):
    now = datetime.now()
    today_date_str = now.strftime("%Y-%m-%d")
    weekly_date_str = (now - timedelta(days=7)).strftime("%Y-%m-%d")
    
    conn = get_db_connection()
    
    total_members = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    total_hearts = conn.execute("SELECT SUM(hearts) FROM users").fetchone()[0] or 0
    total_messages = conn.execute("SELECT SUM(msg_count) FROM users").fetchone()[0] or 0
    
    # Calculate conditional time metrics safely
    today_msgs = conn.execute("SELECT COUNT(*) FROM message_log WHERE timestamp LIKE ?", (f"{today_date_str}%",)).fetchone()[0]
    weekly_msgs = conn.execute("SELECT COUNT(*) FROM message_log WHERE timestamp >= ?", (weekly_date_str,)).fetchone()[0]
    
    # Active operational threshold counts
    active_members = conn.execute("SELECT COUNT(DISTINCT user_id) FROM message_log WHERE timestamp >= ?", (weekly_date_str,)).fetchone()[0]
    
    top_row = conn.execute("SELECT first_name, hearts FROM users ORDER BY hearts DESC LIMIT 1").fetchone()
    top_member_str = f"{escape_html(top_row['first_name'])} ({top_row['hearts']} 💖)" if top_row else "None"
    
    besties_count = conn.execute("SELECT COUNT(*) FROM besties WHERE status = 'accepted'").fetchone()[0]
    total_achs = conn.execute("SELECT COUNT(*) FROM achievements").fetchone()[0]
    
    conn.close()
    
    stats_msg = (
        f"📊 <b>𝖪𝖺𝗐𝖺𝗂𝗂 𝖢/🇺𝖻 Group Analytics</b> 🌸\n\n"
        f"🎀 Total Members Tracked: <b>{total_members}</b>\n"
        f"⚡ Active Members (This Week): <b>{active_members}</b>\n"
        f"💬 Total Messages Sent: <b>{total_messages}</b>\n"
        f"💖 Total Hearts Circulating: <b>{total_hearts} 💖</b>\n\n"
        f"📅 Today's Messages: <b>{today_msgs}</b>\n"
        f"📈 Weekly Traffic: <b>{weekly_msgs}</b>\n\n"
        f"👑 Top Sweetheart: <b>{top_member_str}</b>\n"
        f"🫂 Bestie Connections established: <b>{besties_count} pairs</b>\n"
        f"🎖️ Achievements Unlocked: <b>{total_achs} milestones</b>"
    )
    bot.reply_to(message, stats_msg, parse_mode='HTML')


# --- 🧸 COZY FUN AESTHETIC COMMANDS ---
@bot.message_handler(commands=['hug'])
def fun_hug_handler(message):
    clean_sender = escape_html(message.from_user.first_name)
    if message.reply_to_message:
        clean_receiver = escape_html(message.reply_to_message.from_user.first_name)
        bot.reply_to(message, f"🌸 <b>{clean_sender}</b> ne <b>{clean_receiver}</b> ko ek ekdum warm, cozy aur soft jhappi di! 🫂💕✨", parse_mode='HTML')
    else:
        bot.reply_to(message, f"🎀 <b>{clean_sender}</b> ne group ke saari pyaari saheliyon ko ek buraa sa hug diya! 🫂 unconditional love! 🌸", parse_mode='HTML')

@bot.message_handler(commands=['pat'])
def fun_pat_handler(message):
    clean_sender = escape_html(message.from_user.first_name)
    if message.reply_to_message:
        clean_receiver = escape_html(message.reply_to_message.from_user.first_name)
        bot.reply_to(message, f"🧸 <b>{clean_sender}</b> gently pats <b>{clean_receiver}</b>'s head! Sab thik ho jayega, cutie! ✨🌸", parse_mode='HTML')
    else:
        bot.reply_to(message, "👋 Headpat lene ke liye kisi ke cute message par reply karo, sweetie!")

@bot.message_handler(commands=['cookie'])
def fun_cookie_handler(message):
    clean_sender = escape_html(message.from_user.first_name)
    if message.reply_to_message:
        clean_receiver = escape_html(message.reply_to_message.from_user.first_name)
        bot.reply_to(message, f"🍪 💖 <b>{clean_sender}</b> baked a fresh chocolate chip cookie for <b>{clean_receiver}</b>! Sweet treat for a sweet soul! 🍥", parse_mode='HTML')
    else:
        bot.reply_to(message, f"🍪 Freshly baked cookies are out! Here is a cute virtual cookie for you, <b>{clean_sender}</b>! 🍰", parse_mode='HTML')

@bot.message_handler(commands=['flowers'])
def fun_flowers_handler(message):
    clean_sender = escape_html(message.from_user.first_name)
    if message.reply_to_message:
        clean_receiver = escape_html(message.reply_to_message.from_user.first_name)
        bot.reply_to(message, f"💐 🌸 <b>{clean_sender}</b> sends a gorgeous bouquet of pastel roses and lilies to <b>{clean_receiver}</b>! You make life beautiful! ✨", parse_mode='HTML')
    else:
        bot.reply_to(message, f"🌷 Here is a fresh pink tulip loop for you, <b>{clean_sender}</b>! Stay beautiful! 🌺", parse_mode='HTML')

@bot.message_handler(commands=['poke'])
def fun_poke_handler(message):
    clean_sender = escape_html(message.from_user.first_name)
    if message.reply_to_message:
        clean_receiver = escape_html(message.reply_to_message.from_user.first_name)
        bot.reply_to(message, f"👉 🤭 <b>{clean_sender}</b> pokes <b>{clean_receiver}</b>! Hehehe, daily check-in attention obtained! 🍥", parse_mode='HTML')
    else:
        bot.reply_to(message, "👉 Poke karne ke liye kisi ke message par reply karo, badmaash! 😉")

@bot.message_handler(commands=['coinflip'])
def fun_coinflip_handler(message):
    outcome = random.choice(["Heads 🪙 (Cute side!)", "Tails 🪙 (Sweet side!)"])
    bot.reply_to(message, f"✨ Mitsuha flips a shiny pink coin for you...\n🎯 Result: <b>{outcome}</b>", parse_mode='HTML')

@bot.message_handler(commands=['dice'])
def fun_dice_handler(message):
    num = random.randint(1, 6)
    dice_emojis = ["🎲 1️⃣", "🎲 2️⃣", "🎲 3️⃣", "🎲 4️⃣", "🎲 5️⃣", "🎲 6️⃣"]
    bot.reply_to(message, f"🎲 Mitsuha rolls the aesthetic dice...\n🎀 Outcome: <b>{dice_emojis[num-1]}</b>", parse_mode='HTML')

@bot.message_handler(commands=['8ball'])
def fun_eightball_handler(message):
    responses = [
        "Yes, absolutely, cutie! 🌸",
        "It is certain! ✨",
        "Most definitely! 💖",
        "Hmm, ask me again later while chatting! 🍥",
        "My pink crystal ball is hazy right now... 🔮",
        "No way, sweetie! 🥺",
        "Don't count on it, sorry! 💔",
        "Outlook says sweet surprises are ahead! ⭐"
    ]
    ans = random.choice(responses)
    bot.reply_to(message, f"🔮 <b>𝖪𝖺𝗐𝖺𝗂𝗂 𝖬𝗒𝗌𝗍𝗂𝖼 𝟪-𝖡𝖺𝗅𝗅</b>\n\n💬 Reply: <b>{ans}</b>", parse_mode='HTML')


# --- 🚀 RECONCILED ADMIN RE-FORWARDING SYSTEM ---
@bot.message_handler(func=lambda message: message.chat.type == 'private', content_types=['text', 'photo', 'sticker', 'animation', 'video', 'document'])
def forward_dm_to_group(message):
    if message.from_user.id == YOUR_USER_ID:
        try:
            bot.copy_message(chat_id=GROUP_CHAT_ID, from_chat_id=message.chat.id, message_id=message.message_id)
            bot.reply_to(message, "✅ Group me post kar diya hai, boss!")
        except Exception as e:
            bot.reply_to(message, f"❌ Error aaya bhai: {e}\nCheck karo bot group me Admin hai ya nahi.")
    else:
        bot.reply_to(message, "❌ Aap is bot ke admin nahi ho.")


# --- 🌐 WORKER LOGIC POLLING & APPLICATION LAUNCH ---
def start_bot_polling():
    bot.infinity_polling()

bot_thread = Thread(target=start_bot_polling)
bot_thread.daemon = True
bot_thread.start()

# Flask deployment hooks initialization on port 10000
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
