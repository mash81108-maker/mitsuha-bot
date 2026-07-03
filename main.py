import os
from threading import Thread
from flask import Flask
import telebot

# Render ko active rakhne ke liye dummy server
app = Flask('')

@app.route('/')
def home():
    return "⛩️ Mitsuha Bot is Live!"

def run():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()

# Tumhara Telegram Bot Code (Token ke saath)
TOKEN = '8717295226:AAFAAyfKGvGjqEJQVnpko7g-C3AbQv95Yy8'
bot = telebot.TeleBot(TOKEN)

RULES_TEXT = """
˚₊‧꒰ა ⛩️ 🎀 𝖪𝖺𝗐𝖺𝗂𝗂 𝖢𝗅𝗎𝖻 𝖱𝗎𝗅𝖾𝗌 🌸 ໒꒱ ‧₊˚

1. Everyone ke saath respectful aur friendly raho! 💕
2. Chat me spamming, link sharing, ya toxicity strictly banned hai. 🚫
3. Keep the vibe cute, aesthetic, aur active! 🍥🧸
"""

@bot.message_handler(commands=['start'])
def send_welcome(message):
    welcome_text = "🍥 *Konichiwa! Main hoon Mitsuha.* ⛩️\n\nMain *Kawaii Club* ki official manager desk hoon. Club ke updates aur rules dekhne ke liye niche diye gaye commands use karein! 🎀✨"
    bot.reply_to(message, welcome_text, parse_mode='Markdown')

@bot.message_handler(commands=['rules'])
def send_rules(message):
    bot.reply_to(message, RULES_TEXT, parse_mode='Markdown')

if __name__ == "__main__":
    keep_alive()
    print("⛩️ Mitsuha Bot cloud par ready hai...")
    bot.infinity_polling()
  
