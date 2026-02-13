import telebot
import feedparser
import time
import requests
import re
import random
import sqlite3
import os
from bs4 import BeautifulSoup
from googletrans import Translator
from flask import Flask
from threading import Thread
from datetime import datetime
import pytz

# 1. SERVER
app = Flask('')
@app.route('/')
def home(): return "Bot is running..."
def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run).start()

# 2. SOZLAMALAR
TOKEN = '8358476165:AAFsfhih8yWO0pXaJa_JCvndQ8DUUQZWads'
CHANNEL_ID = '@karnayuzb'
CHANNEL_LOGO = "https://i.postimg.cc/mD8zYpXG/Karnay-uzb.jpg"
bot = telebot.TeleBot(TOKEN)
translator = Translator()
uzb_tz = pytz.timezone('Asia/Tashkent')

# 3. BAZA (SQLite)
def init_db():
    conn = sqlite3.connect('karnay.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS news (link TEXT PRIMARY KEY)''')
    conn.commit()
    conn.close()

def is_duplicate(link):
    conn = sqlite3.connect('karnay.db')
    c = conn.cursor()
    c.execute("SELECT * FROM news WHERE link=?", (link,))
    res = c.fetchone()
    conn.close()
    return res is not None

def save_news(link):
    conn = sqlite3.connect('karnay.db')
    c = conn.cursor()
    try:
        c.execute("INSERT INTO news VALUES (?)", (link,))
        conn.commit()
    except: pass
    conn.close()

# 4. MANBALAR (Qisqartirilgan va sinalgan ro'yxat, keyin ko'paytirish mumkin)
SOURCES = [
    ('Kun.uz', 'https://kun.uz/news/rss'),
    ('Daryo.uz', 'https://daryo.uz/feed/'),
    ('Qalampir.uz', 'https://qalampir.uz/uz/rss'),
    ('BBC Uzbek', 'https://www.bbc.com/uzbek/index.xml'),
    ('TASS', 'https://tass.com/rss/v2.xml'),
    ('Reuters', 'https://www.reutersagency.com/feed/?best-topics=world-news&post_type=best'),
    ('Championat Asia', 'https://championat.asia/uz/news/rss'),
    ('Terabayt.uz', 'https://www.terabayt.uz/feed')
]

# 5. TOZALASH VA TARJIMA
def clean_text(text):
    if not text: return None
    trash = [r"Если вы нашли ошибку.*", r"Ctrl\+Enter.*", r"cookies.*", r"Lotincha", r"Na russkom"]
    for p in trash: text = re.sub(p, "", text, flags=re.IGNORECASE | re.DOTALL)
    lines = [l.strip() for l in text.split('\n') if len(l.strip()) > 50]
    return " ".join(lines).strip()[:900]

def translate_to_uz(text):
    try:
        if not text: return ""
        # googletrans ba'zan bloklanadi, shuning uchun try-except ichida
        res = translator.translate(text, dest='uz')
        return res.text
    except Exception as e:
        print(f"Tarjima xatosi: {e}")
        return text # Xato bo'lsa aslini qaytaradi

def get_content(url):
    try:
        r = requests.get(url, timeout=15)
        soup = BeautifulSoup(r.content, 'html.parser')
        img = soup.find("meta", property="og:image")
        img_url = img['content'] if img else CHANNEL_LOGO
        paras = soup.find_all('p')
        text = clean_text("\n".join([p.get_text() for p in paras]))
        return img_url, text
    except: return CHANNEL_LOGO, None

# 6. ASOSIY SIKL
def start_bot():
    init_db()
    print("Bot ishga tushdi...")
    while True:
        random.shuffle(SOURCES)
        for name, url in SOURCES:
            try:
                print(f"Tekshirilmoqda: {name}")
                feed = feedparser.parse(url)
                for entry in feed.entries[:3]:
                    if is_duplicate(entry.link): continue
                    
                    img, text = get_content(entry.link)
                    if not text: continue
                    
                    title = translate_to_uz(entry.title)
                    desc = translate_to_uz(text)
                    
                    caption = f"📢 **KARNAY.UZB**\n\n**{title}**\n\n{desc}...\n\n✅ @karnayuzb"
                    
                    bot.send_photo(CHANNEL_ID, img, caption=caption, parse_mode='Markdown')
                    save_news(entry.link)
                    print(f"✅ Post yuborildi: {name}")
                    time.sleep(60) # Har bir post orasida 1 daqiqa
            except Exception as e:
                print(f"Xato yuz berdi ({name}): {e}")
                continue
        time.sleep(300) # Har bir aylanishdan keyin 5 daqiqa dam oladi

if __name__ == "__main__":
    keep_alive()
    start_bot()
