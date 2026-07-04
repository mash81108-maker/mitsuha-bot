import os
from threading import Thread
from flask import Flask
import telebot

# Render active rakhne ke liye Flask
app = Flask('')

@app.route('/')
def home():
    return "⛩️ Mitsuha Bot is Live!"

# 🔒 Token ab Safe hai (Render Environment Variable se aayega)
TOKEN = os.environ.get('BOT_TOKEN')
bot = telebot.TeleBot(TOKEN)

# Fixed Admin aur Group IDs
YOUR_USER_ID = 8787638791
GROUP_CHAT_ID = -1003983125875

# Bot ki memory mein Hearts save karne ke liye dictionary
user_hearts = {}

# Texts for Commands (HTML Formatting)
RULES_TEXT = """
˚₊‧꒰ა ⛩️ 🎀 𝖪𝖺𝗐𝖺𝗂𝗂 𝖢/-𝗎𝖻 𝖱𝗎└𝖾𝗌 🌸 ໒꒱ ‧₊˚

1. Everyone ke saath respectful aur friendly raho! 💕
2. Chat me spamming, link sharing, ya toxicity strictly banned hai. 🚫
3. Keep the vibe cute, aesthetic, aur active! 🍥🧸
"""

GROUPS_TEXT = """
🔗 <b>𝖪𝖺𝗐𝖺𝗂𝗂 𝖢/𝗎𝖻 More Groups</b> 🌸

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
        "💖 /hearts - Apne Hearts points check karne ke liye\n"
        "🏆 /leaderboard - Top active members dekhne ke liye"
    )
    bot.reply_to(message, welcome_text, parse_mode='HTML')

@bot.message_handler(commands=['rules'])
def send_rules(message):
    bot.reply_to(message, RULES_TEXT, parse_mode='HTML')

@bot.message_handler(commands=['groups'])
def send_groups(message):
    bot.reply_to(message, GROUPS_TEXT, parse_mode='HTML')

# --- 🎯 HEARTS COMMANDS (User points check kar sakte hain) ---
@bot.message_handler(commands=['hearts'])
def show_hearts(message):
    user_id = message.from_user.id
    name = message.from_user.first_name
    
    if user_id in user_hearts:
        current_pts = user_hearts[user_id]["hearts"]
        bot.reply_to(message, f"🌸 <b>{name}</b>, aapke paas kul <b>{current_pts} Hearts 💖</b> hain! Ekdum pyaare member! ✨", parse_mode='HTML')
    else:
        bot.reply_to(message, f"🌸 <b>{name}</b>, abhi aapke paas 0 Hearts hain. Chatting shuru karo aur dil jeeto! 💕", parse_mode='HTML')

@bot.message_handler(commands=['leaderboard'])
def show_leaderboard(message):
    if not user_hearts:
        bot.reply_to(message, "🏆 Abhi leaderboard khali hai! Group me chatting shuru karo. ✨")
        return
    
    # Highest Hearts ke hisab se top 5 logo ko sort karna
    sorted_users = sorted(user_hearts.items(), key=lambda item: item[1]["hearts"], reverse=True)[:5]
    
    lb_text = "🏆 <b>𝖪𝖺𝗐𝖺𝗂𝗂 𝖢/𝗎𝖻 Most Loved Members</b> 🌸\n\n"
    medals = ["🥇", "🥈", "🥉", "✨", "✨"]
    
    for index, (uid, info) in enumerate(sorted_users):
        clean_name = info["name"].replace('<', '&lt;').replace('>', '&gt;')
        lb_text += f"{medals[index]} <b>{clean_name}</b> — {info['hearts']} 💖\n"
        
    bot.reply_to(message, lb_text, parse_mode='HTML')

# --- 🚀 SILENT HEARTS TRACKER & GROUP HANDLER ---
@bot.message_handler(func=lambda message: message.chat.type in ['group', 'supergroup'], content_types=['text', 'photo', 'sticker', 'animation', 'video', 'document'])
def handle_group_messages(message):
    user_id = message.from_user.id
    name = message.from_user.first_name or "Kawaii Member"
    
    # Background me chupchaap Hearts badhao
    if user_id not in user_hearts:
        user_hearts[user_id] = {"name": name, "hearts": 0}
    
    user_hearts[user_id]["hearts"] += 10  # Har message par +10 Hearts 💖
    user_hearts[user_id]["name"] = name

# --- 🚀 MAIN MAGIC: DM TO GROUP FORWARDER ---
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

# Background thread me chalane ke liye
def start_bot():
    bot.infinity_polling()

bot_thread = Thread(target=start_bot)
bot_thread.daemon = True
bot_thread.start()

# Flask Web Server ko start karne ke liye
app.run(host='0.0.0.0', port=10000)
