import os
from threading import Thread
from flask import Flask
import telebot

# Render active rakhne ke liye Flask
app = Flask('')

@app.route('/')
def home():
    return "⛩️ Mitsuha Bot is Live!"

# Tumhara Token aur IDs fixed
TOKEN = '8717295226:AAFAAyfKGvGjqEJQVnpko7g-C3AbQv95Yy8'
bot = telebot.TeleBot(TOKEN)

# Fixed Admin aur Group IDs
YOUR_USER_ID = 8787638791
GROUP_CHAT_ID = -1003983125875

# Texts for Commands (HTML Formatting)
RULES_TEXT = """
˚₊‧꒰ა ⛩️ 🎀 𝖪𝖺𝗐𝖺𝗂𝗂 𝖢𝗅𝗎𝖻 𝖱𝗎𝗅𝖾𝗌 🌸 ໒꒱ ‧₊˚

1. Everyone ke saath respectful aur friendly raho! 💕
2. Chat me spamming, link sharing, ya toxicity strictly banned hai. 🚫
3. Keep the vibe cute, aesthetic, aur active! 🍥🧸
"""

NOTICES_TEXT = """
📢 <b>𝖪𝖺𝗐𝖺𝗂𝗂 𝖢𝗅𝗎𝖻  𝖭𝗈𝗍𝗂𝖼𝖾𝗌</b> 🌸

Abhi tak koi naya notice nahi hai! Stay tuned for exciting updates! ✨
"""

GROUPS_TEXT = """
🔗 <b>𝖪𝖺𝗐𝖺𝗂𝗂 𝖢𝗅𝗎𝖻 More Groups</b> 🌸

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
        "📢 /notices - Important notices dekhne ke liye\n"
        "🔗 /groups - Humare baaki groups ke links dekhne ke liye"
    )
    bot.reply_to(message, welcome_text, parse_mode='HTML')

@bot.message_handler(commands=['rules'])
def send_rules(message):
    bot.reply_to(message, RULES_TEXT, parse_mode='HTML')

@bot.message_handler(commands=['notices'])
def send_notices(message):
    bot.reply_to(message, NOTICES_TEXT, parse_mode='HTML')

@bot.message_handler(commands=['groups'])
def send_groups(message):
    bot.reply_to(message, GROUPS_TEXT, parse_mode='HTML')

# --- 🚀 MAIN MAGIC: DM TO GROUP FORWARDER ---
@bot.message_handler(func=lambda message: message.chat.type == 'private')
def forward_dm_to_group(message):
    # Sirf TUMHARI baat sunega
    if message.from_user.id == YOUR_USER_ID:
        try:
            # Jo bhi tum bhejoge (Text, Photo, Sticker), wo group me copy ho jayega bina forward tag ke
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

# Flask Web Server ko start karne ke liye (UptimeRobot ke liye zaroori line)
app.run(host='0.0.0.0', port=10000)
