import os
import time
import sqlite3
import logging
from datetime import datetime, timedelta
from threading import Thread
from flask import Flask
import telebot
from telebot import types

# --- 🌸 LOGGING & CONFIGURATION ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
app = Flask('')

@app.route('/')
def home():
    return "⛩️ Mitsuha Bot is live, secured and running perfectly!"

# 🔒 Reads from Render Environment Variables
TOKEN = os.environ.get('BOT_TOKEN', 'YOUR_BOT_TOKEN_HERE')
bot = telebot.TeleBot(TOKEN)

YOUR_USER_ID = int(os.environ.get('ADMIN_ID', 0))             # Auto-filled from Render ADMIN_ID
GROUP_CHAT_ID = int(os.environ.get('GROUP_ID', 0))           # Auto-filled from Render GROUP_ID
DB_FILE = "mitsuha_bot.db"
GROUP_LINK = "https://t.me/KawaiiClubGirls"                  # Verified Group Link 💖

# --- 🛡️ SECURITY WRAPPER (FORCE JOIN ENGINE) ---
def check_membership(func):
    def wrapper(message):
        # Membership check sirf private DM ke liye apply hoga
        if message.chat.type == 'private':
            # Admin/Owner ko humesha full access milega, check karne ki zaroorat nahi
            if message.from_user.id == YOUR_USER_ID:
                return func(message)
            try:
                member = bot.get_chat_member(GROUP_CHAT_ID, message.from_user.id)
                if member.status in ['left', 'kicked']:
                    no_access_msg = (
                        f"❌ <b>Access Denied, Sweetie!</b> 🥺\n\n"
                        f"Is bot ke personal features aur details check karne ke liye "
                        f"aapko pehle hamara main group join karna hoga.\n\n"
                        f"🌸 <b>Join Here:</b> {GROUP_LINK}\n\n"
                        f"Join karne ke baad dobara command type karein! 💕"
                    )
                    bot.reply_to(message, no_access_msg, parse_mode='HTML', disable_web_page_preview=True)
                    return
            except Exception as e:
                logging.error(f"Membership check system error: {e}")
                bot.reply_to(message, "⚠️ System verification temporary unavailable. Please try again later.")
                return
        return func(message)
    return wrapper

# --- 📁 DATABASE ENGINE (THREAD-SAFE WAL MODE) ---
def get_db_connection():
    conn = sqlite3.connect(DB_FILE, timeout=30)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL;")
    
    # Core User Accounts
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
    
    # Achievements Tracking
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS achievements (
        user_id INTEGER,
        achievement_id TEXT,
        unlocked_at TEXT,
        PRIMARY KEY (user_id, achievement_id)
    )
    """)
    
    # Moderation System Logs
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS warnings (
        user_id INTEGER PRIMARY KEY,
        warn_count INTEGER DEFAULT 0
    )
    """)
    
    # Global Activity Message Analytics Logger
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS message_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        timestamp TEXT
    )
    """)
    
    conn.commit()
    conn.close()

init_db()

# --- 🎀 TITLES, LEVELS & ESCAPE HELPERS ---
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
    total_levels = len(LEVELS)
    for index, (threshold, title) in enumerate(LEVELS):
        if hearts >= threshold:
            current_level = total_levels - index
            if index == 0:
                return current_level, title, 0
            return current_level, title, (LEVELS[index - 1][0] - hearts)
    return 1, "Fresh Face 🌸", 200

def escape_html(text):
    if not text: return "Angel"
    return text.replace('<', '&lt;').replace('>', '&gt;')

# --- 🏆 ACHIEVEMENTS CONFIGURATION & DISPATCHER ---
ACHIEVEMENTS_BOOK = {
    "first_msg": {"badge": "🌱", "title": "First Step", "desc": "Sent your very first message in the group!"},
    "msg_100": {"badge": "💬", "title": "Chatty Angel", "desc": "Reached a milestone of 100 group messages!"},
    "hearts_1000": {"badge": "❤️", "title": "Heart Collector", "desc": "Earned and pooled 1,000 Sweet Hearts!"},
    "streak_7": {"badge": "🔥", "title": "Unstoppable", "desc": "Maintained an active 7-day chat streak!"},
    "top_1": {"badge": "👑", "title": "Club Queen", "desc": "Claimed Rank #1 position on the sweethearts leaderboard!"},
    "event_winner": {"badge": "🎀", "title": "Festival Star", "desc": "Awarded for exceptional community event victory!"}
}

def grant_achievement(user_id, achievement_id, chat_id, explicit_first_name=None):
    conn = get_db_connection()
    exists = conn.execute("SELECT 1 FROM achievements WHERE user_id = ? AND achievement_id = ?", (user_id, achievement_id)).fetchone()
    if not exists:
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        conn.execute("INSERT INTO achievements (user_id, achievement_id, unlocked_at) VALUES (?, ?, ?)", (user_id, achievement_id, now_str))
        conn.commit()
        conn.close()
        
        ach = ACHIEVEMENTS_BOOK[achievement_id]
        display_name = escape_html(explicit_first_name) if explicit_first_name else "Angel"
        
        announcement = (
            f"✨ <b>𝖪𝖺𝗐𝖺𝗂𝗂 𝖠𝖼𝗁𝗂𝖾𝗏𝖾𝗆𝖾่น𝗍 𝖴𝗇𝗅𝗈𝖼𝗄𝖾𝖽!</b> 🎀\n\n"
            f"🌸 🔔 <b>{display_name}</b> has unlocked a special milestone:\n"
            f"{ach['badge']} <b>{ach['title']}</b> — <i>{ach['desc']}</i>\n\n"
            f"Keep spreading cozy vibes! 💕"
        )
        bot.send_message(chat_id, announcement, parse_mode='HTML')
    else:
        conn.close()

# --- 🚀 AUTOMATIC CHAT ROUTINES & TRACKER ---
@bot.message_handler(func=lambda message: message.chat.type in ['group', 'supergroup'], content_types=['text', 'photo', 'sticker', 'animation', 'video', 'document'])
def process_incoming_activities(message):
    user_id = message.from_user.id
    if message.from_user.is_bot: return
    
    username = message.from_user.username
    first_name = message.from_user.first_name
    now_time = time.time()
    today_date_str = datetime.now().strftime("%Y-%m-%d")
    now_timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    conn = get_db_connection()
    user_row = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
    
    current_msg_count = 1
    current_hearts = 10
    current_streak = 1
    last_daily = today_date_str
    
    if not user_row:
        conn.execute("""
            INSERT INTO users (user_id, username, first_name, hearts, msg_count, daily_streak, last_daily, join_date, last_msg_time) 
            VALUES (?, ?, ?, 10, 1, 1, ?, ?, ?)
        """, (user_id, username, first_name, today_date_str, now_timestamp_str, now_time))
    else:
        current_msg_count = user_row["msg_count"] + 1
        current_hearts = user_row["hearts"] + 10
        current_streak = user_row["daily_streak"]
        last_daily = user_row["last_daily"]
        
        if not last_daily:
            current_streak = 1
            last_daily = today_date_str
        else:
            try:
                last_date_obj = datetime.strptime(last_daily, "%Y-%m-%d").date()
                today_obj = datetime.now().date()
                delta_days = (today_obj - last_date_obj).days
                
                if delta_days == 1:
                    current_streak += 1
                    last_daily = today_date_str
                elif delta_days > 1:
                    current_streak = 1
                    last_daily = today_date_str
            except Exception:
                current_streak = 1
                last_daily = today_date_str
                
        conn.execute("""
            UPDATE users SET username = ?, first_name = ?, hearts = ?, msg_count = ?, daily_streak = ?, last_daily = ?, last_msg_time = ? 
            WHERE user_id = ?
        """, (username, first_name, current_hearts, current_msg_count, current_streak, last_daily, now_time, user_id))
        
    conn.execute("INSERT INTO message_log (user_id, timestamp) VALUES (?, ?)", (user_id, now_timestamp_str))
    conn.commit()
    conn.close()
    
    if current_msg_count == 1: grant_achievement(user_id, "first_msg", message.chat.id, first_name)
    if current_msg_count == 100: grant_achievement(user_id, "msg_100", message.chat.id, first_name)
    if current_hearts >= 1000: grant_achievement(user_id, "hearts_1000", message.chat.id, first_name)
    if current_streak >= 7: grant_achievement(user_id, "streak_7", message.chat.id, first_name)

# --- 💖 MEMBER PORTAL COMMANDS (WITH SECURITY) ---
@bot.message_handler(commands=['start'])
@check_membership
def command_start(message):
    welcome = (
        "🍥 <b>Konichiwa! Main hoon Mitsuha.</b> ⛩️\n\n"
        "Main aapke group ki official manager desk hoon. "
        "Yahan aapki tracking, achievements aur activity safe rahegi. 🎀✨\n\n"
        "📖 Sabhi commands check karne ke liye type karein: /help"
    )
    bot.reply_to(message, welcome, parse_mode='HTML')

@bot.message_handler(commands=['rules'])
@check_membership
def command_rules(message):
    rules = f"˚₊‧꒰ა ⛩️ 🎀 <b>𝖪𝖺𝗐𝖺𝗂𝗂 𝖢𝗅𝗎𝖻 𝖱𝗎𝗅𝖾𝗌</b> 🌸 ໒꒱ ‧₊˚\n\n1. Sabhi ke sath respectful aur friendly raho! 💕\n2. Group me unnecessary links, spamming aur fights completely banned hain."
    bot.reply_to(message, rules, parse_mode='HTML')

@bot.message_handler(commands=['groups'])
@check_membership
def command_groups(message):
    network = "🔗 <b>𝖪𝖺𝗐𝖺𝗂𝗂 𝖢𝗅𝗎𝖻 Network Hub</b> 🌸\n\n🤝 <b>Partner Community:</b> @team_tamashi"
    bot.reply_to(message, network, parse_mode='HTML')

@bot.message_handler(commands=['hearts'])
@check_membership
def command_hearts(message):
    user_id = message.from_user.id
    name = escape_html(message.from_user.first_name)
    conn = get_db_connection()
    row = conn.execute("SELECT hearts FROM users WHERE user_id = ?", (user_id,)).fetchone()
    conn.close()
    
    if row:
        pts = row["hearts"]
        _, title, needed = get_level_info(pts)
        next_str = f" Next rank ke liye <b>{needed} Hearts</b> baki hain! ✨" if needed > 0 else " Aap max tier par ho! 👑"
        bot.reply_to(message, f"🌸 <b>{name}</b>: <b>{pts} Hearts 💖</b>\n📝 Custom Title: <b>{title}</b>\n{next_str}", parse_mode='HTML')
    else:
        bot.reply_to(message, f"🌸 <b>{name}</b>, abhi aapke paas 0 Hearts hain. Group me chat shuru karo! 💕", parse_mode='HTML')

@bot.message_handler(commands=['profile'])
@check_membership
def command_profile(message):
    user_id = message.from_user.id
    name = escape_html(message.from_user.first_name)
    conn = get_db_connection()
    user_row = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
    
    if not user_row:
        bot.reply_to(message, "🌸 Aapka profile record abhi system me nahi hai. Pehle group me kuch message bhejein!")
        conn.close()
        return
        
    leaderboard = conn.execute("SELECT user_id FROM users ORDER BY hearts DESC").fetchall()
    rank = next((idx + 1 for idx, r in enumerate(leaderboard) if r["user_id"] == user_id), "N/A")
    
    ach_rows = conn.execute("SELECT achievement_id FROM achievements WHERE user_id = ?", (user_id,)).fetchall()
    unlocked_badges = [ACHIEVEMENTS_BOOK[r["achievement_id"]]["badge"] for r in ach_rows if r["achievement_id"] in ACHIEVEMENTS_BOOK]
    badges_display = " ".join(unlocked_badges) if unlocked_badges else "No badges unlocked yet 🌱"
    conn.close()
    
    _, title, _ = get_level_info(user_row["hearts"])
    
    profile_card = (
        f"˚₊‧꒰ა ⛩️ 🎀 <b>𝖪𝖺𝗐𝖺𝗂𝗂 𝖢𝗅𝗎𝖻 𝖯𝖱𝖮𝖥𝖨𝖫𝖤</b> 🌸 ໒꒱ ‧₊˚\n\n"
        f"🙋‍♀️ Name: <b>{name}</b>\n"
        f"💖 Hearts Multiplier: <b>{user_row['hearts']}</b>\n"
        f"💮 Member Title: <b>{title}</b>\n"
        f"🏆 Global Rank: <b>#{rank}</b>\n"
        f"📊 Text Count: <b>{user_row['msg_count']} msgs</b>\n"
        f"🔥 Active Streak: <b>{user_row['daily_streak']} Days</b>\n"
        f"📅 Date Joined: <code>{user_row['join_date'][:10]}</code>\n"
        f"🎖️ Badges Showcase: {badges_display}"
    )
    bot.reply_to(message, profile_card, parse_mode='HTML')

@bot.message_handler(commands=['rank'])
@check_membership
def command_rank(message):
    user_id = message.from_user.id
    conn = get_db_connection()
    leaderboard = conn.execute("SELECT user_id, hearts FROM users ORDER BY hearts DESC").fetchall()
    rank = next((idx + 1 for idx, r in enumerate(leaderboard) if r["user_id"] == user_id), 0)
    user_data = conn.execute("SELECT hearts FROM users WHERE user_id = ?", (user_id,)).fetchone()
    conn.close()
    
    if rank == 0 or not user_data:
        bot.reply_to(message, "🌸 Rank analyze nahi ho saki. Pehle group me actively chat kijiye!")
        return
        
    _, _, needed = get_level_info(user_data["hearts"])
    needed_str = f"Next tier ke liye <b>{needed} hearts</b> ki zaroorat hai! ✨" if needed > 0 else "Aap peak level titles par ho! 👑"
    bot.reply_to(message, f"🏆 <b>𝖪𝖺𝗐𝖺𝗂𝗂 𝖢𝗅𝗎𝖻 Global Position</b>\n\n🎯 Aapki Rank: <b>#{rank}</b>\n💖 Total Accumulation: <b>{user_data['hearts']} Hearts</b>\n📈 {needed_str}", parse_mode='HTML')

@bot.message_handler(commands=['activity'])
@check_membership
def command_activity(message):
    user_id = message.from_user.id
    conn = get_db_connection()
    row = conn.execute("SELECT msg_count, daily_streak, last_msg_time FROM users WHERE user_id = ?", (user_id,)).fetchone()
    conn.close()
    
    if not row:
        bot.reply_to(message, "🌸 Aapka koi activity metrics record nahi mila.")
        return
        
    last_seen_date = datetime.fromtimestamp(row["last_msg_time"]).strftime("%Y-%m-%d %H:%M") if row["last_msg_time"] > 0 else "Never"
    bot.reply_to(message, f"📊 <b>Personal Activity Tracker:</b>\n\n💬 Total Messages: <b>{row['msg_count']}</b>\n🔥 Daily Activity Streak: <b>{row['daily_streak']} Days</b>\n🕒 Last Seen Active: <code>{last_seen_date}</code>", parse_mode='HTML')

@bot.message_handler(commands=['sweethearts'])
@check_membership
def command_sweethearts(message):
    conn = get_db_connection()
    rows = conn.execute("SELECT user_id, first_name, hearts FROM users ORDER BY hearts DESC LIMIT 10").fetchall()
    if not rows:
        bot.reply_to(message, "🏆 Leaderboard summary records abhi khali hain!")
        conn.close()
        return
    
    lb_text = "🏆 <b>𝖪𝖺𝗐𝖺𝗂𝗂 𝖢𝗅𝗎𝖻 Sweethearts Leaderboard</b> 🌸\n\n"
    medals = ["🥇", "🥈", "🥉", "✨", "✨", "✨", "✨", "✨", "✨", "✨"]
    for index, row in enumerate(rows):
        first_name_clean = escape_html(row['first_name'])
        lb_text += f"{medals[index]} <b>{first_name_clean}</b> — {row['hearts']} 💖\n"
        if index == 0: 
            grant_achievement(row["user_id"], "top_1", message.chat.id, row['first_name'])
    conn.close()
    bot.reply_to(message, lb_text, parse_mode='HTML')

# --- 📊 GROUP STATISTICS ENGINE ---
@bot.message_handler(commands=['groupstats'])
@check_membership
def command_groupstats(message):
    now_date = datetime.now()
    today_stamp = now_date.strftime("%Y-%m-%d")
    weekly_stamp = (now_date - timedelta(days=7)).strftime("%Y-%m-%d")
    
    conn = get_db_connection()
    total_members = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    total_hearts = conn.execute("SELECT SUM(hearts) FROM users").fetchone()[0] or 0
    total_messages = conn.execute("SELECT SUM(msg_count) FROM users").fetchone()[0] or 0
    today_msgs = conn.execute("SELECT COUNT(*) FROM message_log WHERE timestamp LIKE ?", (f"{today_stamp}%",)).fetchone()[0]
    weekly_msgs = conn.execute("SELECT COUNT(*) FROM message_log WHERE timestamp >= ?", (weekly_stamp,)).fetchone()[0]
    active_members_7d = conn.execute("SELECT COUNT(DISTINCT user_id) FROM message_log WHERE timestamp >= ?", (weekly_stamp,)).fetchone()[0]
    total_achievements = conn.execute("SELECT COUNT(*) FROM achievements").fetchone()[0]
    
    top_user = conn.execute("SELECT first_name, hearts FROM users ORDER BY hearts DESC LIMIT 1").fetchone()
    top_member_summary = f"{escape_html(top_user['first_name'])} ({top_user['hearts']} 💖)" if top_user else "None"
    conn.close()
    
    stats_msg = (
        f"📊 <b>𝖪𝖺𝗐𝖺𝗂𝗂 𝖢𝗅𝗎𝖻 Analytics Metrics Card</b> 🌸\n\n"
        f"🎀 Total Profiles Tracked: <b>{total_members}</b>\n"
        f"⚡ Active Members (7 Days): <b>{active_members_7d}</b>\n"
        f"💬 Global Messages Pool: <b>{total_messages} msgs</b>\n"
        f"💖 Cumulative Hearts distributed: <b>{total_hearts} 💖</b>\n"
        f"📅 Today's Live Flow: <b>{today_msgs} messages</b>\n"
        f"📈 7-Day Traffic Velocity: <b>{weekly_msgs} texts</b>\n"
        f"👑 Reigning Top Member: <b>{top_member_summary}</b>\n"
        f"🎖️ Total Milestone Badges Awarded: <b>{total_achievements}</b>"
    )
    bot.reply_to(message, stats_msg, parse_mode='HTML')

# --- 🛡️ EXCLUSIVE MODERATION FRAMEWORK ---
def is_user_admin(chat_id, user_id):
    try:
        if user_id == YOUR_USER_ID: return True
        admins = bot.get_chat_administrators(chat_id)
        return any(admin.user.id == user_id for admin in admins)
    except Exception:
        return False

@bot.message_handler(commands=['warn'])
def command_warn(message):
    if not is_user_admin(message.chat.id, message.from_user.id):
        bot.reply_to(message, "❌ Sirf club admins ye action le sakte hain, sweetie!")
        return
    if not message.reply_to_message:
        bot.reply_to(message, "❌ Please kisi ke rule-breaking message par reply karke /warn use karein.")
        return
        
    target_id = message.reply_to_message.from_user.id
    target_name = escape_html(message.reply_to_message.from_user.first_name)
    
    if is_user_admin(message.chat.id, target_id):
        bot.reply_to(message, "❌ Protected System! Main admins ko warning nahi de sakti.")
        return
        
    conn = get_db_connection()
    row = conn.execute("SELECT warn_count FROM warnings WHERE user_id = ?", (target_id,)).fetchone()
    count = (row["warn_count"] + 1) if row else 1
    conn.execute("INSERT OR REPLACE INTO warnings (user_id, warn_count) VALUES (?, ?)", (target_id, count))
    conn.commit()
    conn.close()
    
    bot.reply_to(message, f"⚠️ <b>{target_name}</b> ko rule breach ke liye warn kiya gaya hai! Current Warnings Status: <b>{count}/3</b>", parse_mode='HTML')
    
    if count >= 3:
        try:
            bot.restrict_chat_member(message.chat.id, target_id, until_date=time.time() + 86400, can_send_messages=False)
            bot.send_message(message.chat.id, f"🔒 <b>{target_name}</b> ne maximum safety warning cross kar di hain. Unhein auto-mute kar diya gaya hai for 24 Hours!")
        except Exception as e:
            bot.send_message(message.chat.id, f"❌ Action failure details: {e}")

@bot.message_handler(commands=['warnings'])
def command_warnings(message):
    target_id = message.reply_to_message.from_user.id if message.reply_to_message else message.from_user.id
    target_name = escape_html(message.reply_to_message.from_user.first_name if message.reply_to_message else message.from_user.first_name)
    
    conn = get_db_connection()
    row = conn.execute("SELECT warn_count FROM warnings WHERE user_id = ?", (target_id,)).fetchone()
    conn.close()
    count = row["warn_count"] if row else 0
    bot.reply_to(message, f"📋 Profile <b>{target_name}</b> ke paas abhi kul <b>{count}/3</b> warnings active hain.", parse_mode='HTML')

@bot.message_handler(commands=['clearwarns'])
def command_clearwarns(message):
    if not is_user_admin(message.chat.id, message.from_user.id): return
    if not message.reply_to_message:
        bot.reply_to(message, "❌ Target member ke message par reply karke warnings reset karein.")
        return
    target_id = message.reply_to_message.from_user.id
    conn = get_db_connection()
    conn.execute("DELETE FROM warnings WHERE user_id = ?", (target_id,))
    conn.commit()
    conn.close()
    bot.reply_to(message, "✅ Saari active warnings clear ho gayi hain. Account record clean ho gaya! 💕")

@bot.message_handler(commands=['mute'])
def command_mute(message):
    if not is_user_admin(message.chat.id, message.from_user.id): return
    if not message.reply_to_message: return
    target_id = message.reply_to_message.from_user.id
    if is_user_admin(message.chat.id, target_id): return
    try:
        bot.restrict_chat_member(message.chat.id, target_id, can_send_messages=False)
        bot.reply_to(message, "🔒 Member ko successfully mute kar diya gaya hai. Shhh! 🤫")
    except Exception as e: bot.reply_to(message, f"❌ Request denied: {e}")

@bot.message_handler(commands=['unmute'])
def command_unmute(message):
    if not is_user_admin(message.chat.id, message.from_user.id): return
    if not message.reply_to_message: return
    target_id = message.reply_to_message.from_user.id
    try:
        bot.restrict_chat_member(message.chat.id, target_id, can_send_messages=True, can_send_media_messages=True, can_send_other_messages=True)
        bot.reply_to(message, "🔓 Text restrictions lifted! Aap ab group me baat kar sakti hain. 💕")
    except Exception as e: bot.reply_to(message, f"❌ Request denied: {e}")

@bot.message_handler(commands=['kick'])
def command_kick(message):
    if not is_user_admin(message.chat.id, message.from_user.id): return
    if not message.reply_to_message: return
    target_id = message.reply_to_message.from_user.id
    if is_user_admin(message.chat.id, target_id): return
    try:
        bot.ban_chat_member(message.chat.id, target_id)
        bot.unban_chat_member(message.chat.id, target_id)
        bot.reply_to(message, "👋 Member ko safety protocol ke tehat group se remove kar diya gaya.")
    except Exception as e: bot.reply_to(message, f"❌ Request denied: {e}")

@bot.message_handler(commands=['ban'])
def command_ban(message):
    if not is_user_admin(message.chat.id, message.from_user.id): return
    if not message.reply_to_message: return
    target_id = message.reply_to_message.from_user.id
    if is_user_admin(message.chat.id, target_id): return
    try:
        bot.ban_chat_member(message.chat.id, target_id)
        bot.reply_to(message, "🚫 User blacklisted. Record permanently banned from access routes.")
    except Exception as e: bot.reply_to(message, f"❌ Request denied: {e}")

@bot.message_handler(commands=['unban'])
def command_unban(message):
    if not is_user_admin(message.chat.id, message.from_user.id): return
    tokens = message.text.split()
    if len(tokens) < 2:
        bot.reply_to(message, "❌ Target numeric Telegram user ID dena zaroori hai. Example: /unban 1234567")
        return
    try:
        bot.unban_chat_member(message.chat.id, int(tokens[1]))
        bot.reply_to(message, "✅ Restrictions removed. User can join back via link! ✨")
    except Exception as e: bot.reply_to(message, f"❌ Request failed: {e}")

# --- 👑 ADMINISTRATIVE EXCLUSIVE (MANUAL GIFT BADGES) ---
@bot.message_handler(commands=['giftbadge'])
def command_giftbadge(message):
    if message.from_user.id != YOUR_USER_ID: return
    if not message.reply_to_message:
        bot.reply_to(message, "❌ Kisi active message par reply karke badge grant karein. Format: /giftbadge event_winner")
        return
    args = message.text.split()
    if len(args) < 2:
        bot.reply_to(message, "❌ Badge ID provide karein. Example: /giftbadge event_winner")
        return
    badge_id = args[1]
    if badge_id not in ACHIEVEMENTS_BOOK:
        bot.reply_to(message, "❌ Di gayi badge ID valid nahi hai catalog me.")
        return
    
    target_id = message.reply_to_message.from_user.id
    target_name = message.reply_to_message.from_user.first_name
    grant_achievement(target_id, badge_id, message.chat.id, target_name)

# --- 👑 CLEAN MANUAL BACKUP ENGINE (NO SPAM) ---
@bot.message_handler(commands=['backup'])
def manual_backup(message):
    if message.from_user.id == YOUR_USER_ID:
        try:
            if os.path.exists(DB_FILE):
                with open(DB_FILE, "rb") as doc:
                    bot.send_document(
                        message.chat.id, 
                        doc, 
                        caption=f"📦 #MITSUHA_BACKUP\n🕒 Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n⚠️ Safe keeping for Render redeploys."
                    )
            else:
                bot.reply_to(message, "❌ Database file abhi tak generate nahi hui hai.")
        except Exception as e:
            bot.reply_to(message, f"❌ Backup failure error: {e}")
    else:
        bot.reply_to(message, "❌ Arey bhai, ye command sirf Master Owner ke liye safe-locked hai!")

# --- ⏳ BACKGROUND AUTOMATED INACTIVITY ENFORCEMENT LOOP ---
def execute_inactivity_scan_cycle():
    while True:
        try:
            time.sleep(86400) # Runs strictly once every 24 hours
            logging.info("Initiating routine scan for tracking user inactivity durations...")
            
            conn = get_db_connection()
            active_profiles = conn.execute("SELECT user_id, username, first_name, last_msg_time FROM users").fetchall()
            now_epoch = time.time()
            
            for profile in active_profiles:
                uid = profile["user_id"]
                first_name_raw = profile["first_name"]
                name_clean = escape_html(first_name_raw)
                username_raw = profile["username"]
                last_active_epoch = profile["last_msg_time"]
                
                if last_active_epoch == 0: continue
                days_elapsed = (now_epoch - last_active_epoch) / 86400
                
                # Admins aur Bots ko skip karna hai safety ke liye
                if is_user_admin(GROUP_CHAT_ID, uid): continue
                
                if username_raw:
                    tag_mention = f"@{username_raw}"
                else:
                    tag_mention = f'<a href="tg://user?id={uid}">{name_clean}</a>'
                
                # Notification triggers based on days
                if 5.0 <= days_elapsed < 6.0:
                    alert = f"🌸 🔔 <b>Reminder:</b> Hey {tag_mention}, hum sab aapko group me bahut miss kar rahe hain! Aakar thodi baatein karo na! 💕"
                    bot.send_message(GROUP_CHAT_ID, alert, parse_mode='HTML')
                    
                elif 6.0 <= days_elapsed < 7.0:
                    alert = f"⚠️ <b>Warning:</b> Beautiful {tag_mention}, aap pichle 6 dinon se inactive ho. Agar kal tak group me text nahi kiya toh aap automatic remove ho jaogi. 🥺"
                    bot.send_message(GROUP_CHAT_ID, alert, parse_mode='HTML')
                    
                elif days_elapsed >= 7.0:
                    try:
                        bot.ban_chat_member(GROUP_CHAT_ID, uid)
                        bot.unban_chat_member(GROUP_CHAT_ID, uid) # Transient ban executes a clean kick
                        expulsion_notice = f"🚪 <b>{name_clean}</b> (ID: <code>{uid}</code>) ko 7 dinon ki continuous inactivity ki wajah se group se remove kar diya gya hai."
                        bot.send_message(GROUP_CHAT_ID, expulsion_notice, parse_mode='HTML')
                    except Exception as ex:
                        logging.error(f"Inactivity kick failed for user {uid}: {ex}")
                        
            conn.close()
        except Exception as loop_error:
            logging.error(f"Error caught inside inactivity routine scheduler: {loop_error}")

inactivity_daemon = Thread(target=execute_inactivity_scan_cycle)
inactivity_daemon.daemon = True
inactivity_daemon.start()

# --- 📖 GROUPED HELP ARCHITECTURE ---
@bot.message_handler(commands=['help'])
@check_membership
def command_help(message):
    help_manifest = (
        "˚₊‧꒰ാ ⛩️ 🎀 <b>𝖬\n𝗂𝗍𝗌𝗎𝗁𝖺 𝖡𝗈𝗍 𝖧𝖾𝗅𝗉 𝖣𝖾𝗌𝗄</b> 🌸 ໒꒱ ‧₊˚\n\n"
        "💖 <b>𝖬𝖤𝖬𝖡𝖤𝖱 𝖢𝖮𝖬𝖬𝖠𝖭𝖣𝖲:</b>\n"
        "• /start - Setup welcome orientation note\n"
        "• /rules - View core group framework rules\n"
        "• /groups - Check connected network links\n"
        "• /hearts - Inspect your tracked scores & titles\n"
        "• /profile - Fetch your full user profile identity card\n"
        "• /rank - Show your global standing tier position\n"
        "• /activity - View private daily activity telemetry logs\n"
        "• /sweethearts - Display Top 10 most active members leaderboard\n\n"
        "📊 <b>𝖲𝖳𝖠𝖳𝖨𝖲𝖳𝖨𝖢𝖲:</b>\n"
        "• /groupstats - Compute group traffic analytics summary\n\n"
        "🛡️ <b>𝖬𝖮𝖣𝖤𝖱𝖠𝖳𝖨𝖮𝖭:</b>\n"
        "• /warn - Strike a warning onto user profile\n"
        "• /warnings - View list of total active warnings\n"
        "• /clearwarns - Wipe account structural warning tallies\n"
        "• /mute | /unmute - Restrict/Restore message abilities\n"
        "• /kick - Perform transient safe user removal\n"
        "• /ban | /unban - Control full entry blacklists\n\n"
        "👑 <b>𝖮𝖶𝖭𝖤𝖱 / 𝖠𝖣𝖬𝖨𝖭:</b>\n"
        "• /backup - Requests database `.db` file manually in chat.\n"
        "• DM Restore - Bot ke personal chat me `mitsuha_bot.db` file send karke database instantly overwrite aur restore kar sakte ho."
    )
    bot.reply_to(message, help_manifest, parse_mode='HTML')

# --- 👑 ADMIN DM RE-ROUTING & PERSISTENT MANUAL RESTORE ENGINE ---
@bot.message_handler(func=lambda message: message.chat.type == 'private', content_types=['text', 'photo', 'sticker', 'animation', 'video', 'document'])
def handle_admin_private_portal(message):
    if message.from_user.id != YOUR_USER_ID:
        # Agar koi outsider DM karta hai (aur wo member hai), tabhi ye access block automatic work karega.
        return

    # Check if Admin sent the Database Document to Restore data
    if message.content_type == 'document':
        if message.document.file_name == DB_FILE:
            try:
                file_info = bot.get_file(message.document.file_id)
                downloaded_file = bot.download_file(file_info.file_path)
                
                with open(DB_FILE, 'wb') as new_db:
                    new_db.write(downloaded_file)
                
                bot.reply_to(message, "✅ <b>Database Overwritten Successfully!</b> Puraana saara metrics telemetry data (Hearts, Streaks, Achievements) successfully restore ho gaya hai! 🔥🌸", parse_mode='HTML')
                logging.info("Database instance manually replaced via Admin workspace upload.")
            except Exception as restoration_failure:
                bot.reply_to(message, f"❌ Restoration error encountered: {restoration_failure}")
        else:
            bot.reply_to(message, f"❌ File ka naam strict <code>{DB_FILE}</code> hona chahiye to pass cloud restore.", parse_mode='HTML')
        return

    # Owner normal message forwarding system to Group
    try:
        bot.copy_message(chat_id=GROUP_CHAT_ID, from_chat_id=message.chat.id, message_id=message.message_id)
        bot.reply_to(message, "✅ Announcement group me copy karke post kar di hai, boss!")
    except Exception as network_error:
        bot.reply_to(message, f"❌ Post forwarding failed: {network_error}")

# --- 🌐 WORKER ROUTINE POLLING LAUNCHERS ---
def execute_bot_polling():
    logging.info("Starting up core asynchronous bot runtime polling thread...")
    bot.infinity_polling()

polling_thread = Thread(target=execute_bot_polling)
polling_thread.daemon = True
polling_thread.start()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
