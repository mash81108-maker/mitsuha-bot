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

# Members ke Telegram Nicknames auto-save karne ke liye dictionary (Tagall ke liye)
active_members = {}

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

@bot.message_handler(commands=['start'])
def send_welcome(message):
    welcome_text = (
        "🍥 <b>Konichiwa! Main hoon Mitsuha.</b> ⛩️\n\n"
        "Main <b>Kawaii Club</b> ki official manager desk hoon. "
        "Club ke updates aur rules dekhne ke liye niche diye gaye commands use karein! 🎀✨\n\n"
        "📜 /rules - Group ke rules dekhne ke liye\n"
        "📢 /notices - Important notices dekhne ke liye\n"
        "📢 /tagall - Sabhi active members ko tag karne ke liye"
    )
    bot.reply_to(message, welcome_text, parse_mode='HTML')

@bot.message_handler(commands=['rules'])
def send_rules(message):
    bot.reply_to(message, RULES_TEXT, parse_mode='HTML')

@bot.message_handler(commands=['notices'])
def send_notices(message):
    bot.reply_to(message, NOTICES_TEXT, parse_mode='HTML')

# --- AUTOMATIC NICKNAME TAGALL ---
@bot.message_handler(commands=['tagall'])
def tag_all_members(message):
    if message.chat.type == 'private':
        bot.reply_to(message, "❌ Bhai, ye command sirf group me kaam karega!")
        return

    text_parts = message.text.split(' ', 1)
    custom_msg = text_parts[1] if len(text_parts) > 1 else "Sab log online aao! ✨"

    if active_members:
        mentions_list = []
        for user_id, nickname in active_members.items():
            clean_name = nickname.replace('<', '&lt;').replace('>', '&gt;')
            mentions_list.append(f'<a href="tg://user?id={user_id}">{clean_name}</a>')
        
        all_mentions = ", ".join(mentions_list)
        announcement = f"📢 <b>𝖪𝖺𝗐𝖺𝗂𝗂 𝖢𝗅𝗎𝖻 Announcement!</b> 🌸\n\n💬 {custom_msg}\n\n🔔 {all_mentions}"
        bot.send_message(message.chat.id, announcement, parse_mode='HTML')
    else:
        bot.reply_to(message, "❌ Abhi tak kisi ne group me chat nahi ki hai!")

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

# --- AUTO NICKNAME CAPTURER FOR TAGALL ---
@bot.message_handler(func=lambda message: True, content_types=['text', 'photo', 'sticker', 'animation', 'video'])
def capture_active_users(message):
    if message.chat.type in ['group', 'supergroup']:
        user_id = message.from_user.id
        nickname = message.from_user.first_name
        active_members[user_id] = nickname

# Background thread me chalane ke liye
def start_bot():
    bot.infinity_polling()

bot_thread = Thread(target=start_bot)
bot_thread.daemon = True
bot_thread.start()
