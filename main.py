import os
from threading import Thread
from flask import Flask
import telebot

# Render ko active rakhne ke liye Flask app
app = Flask('')

@app.route('/')
def home():
    return "⛩️ Mitsuha Bot is Live!"

# Tumhara Telegram Bot Code (Preserved Token)
TOKEN = '8717295226:AAFAAyfKGvGjqEJQVnpko7g-C3AbQv95Yy8'
bot = telebot.TeleBot(TOKEN)

# Texts for Commands
RULES_TEXT = """
˚₊‧꒰ა ⛩️ 🎀 𝖪𝖺𝗐𝖺𝗂𝗂 𝖢𝗅𝗎𝖻 𝖱𝗎𝗅𝖾𝗌 🌸 ໒꒱ ‧₊˚

1. Everyone ke saath respectful aur friendly raho! 💕
2. Chat me spamming, link sharing, ya toxicity strictly banned hai. 🚫
3. Keep the vibe cute, aesthetic, aur active! 🍥🧸
"""

NOTICES_TEXT = """
📢 *𝖪𝖺𝗐𝖺𝗂𝗂 𝖢𝗅𝗎𝖻  𝖭𝗈𝗍𝗂𝖼𝖾𝗌* 🌸

Abhi tak koi naya notice nahi hai! Stay tuned for exciting updates! ✨
"""

@bot.message_handler(commands=['start'])
def send_welcome(message):
    welcome_text = (
        "🍥 *Konichiwa! Main hoon Mitsuha.* ⛩️\n\n"
        "Main *Kawaii Club* ki official manager desk hoon. "
        "Club ke updates aur rules dekhne ke liye niche diye gaye commands use karein! 🎀✨\n\n"
        "📜 /rules - Group ke rules dekhne ke liye\n"
        "📢 /notices - Important notices dekhne ke liye"
    )
    bot.reply_to(message, welcome_text, parse_mode='Markdown')

@bot.message_handler(commands=['rules'])
def send_rules(message):
    bot.reply_to(message, RULES_TEXT, parse_mode='Markdown')

@bot.message_handler(commands=['notices'])
def send_notices(message):
    bot.reply_to(message, NOTICES_TEXT, parse_mode='Markdown')

# Gunicorn ke liye Background Thread me Bot ko Start Karna
def start_bot():
    print("⛩️ Mitsuha Bot polling started...")
    bot.infinity_polling()

bot_thread = Thread(target=start_bot)
bot_thread.daemon = True
bot_thread.start()
