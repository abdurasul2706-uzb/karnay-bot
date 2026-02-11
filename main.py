import telebot
import feedparser
import time
import requests
import re
import random
import os
from bs4 import BeautifulSoup
from googletrans import Translator
from flask import Flask
from threading import Thread
from datetime import datetime
import pytz

# 1. SERVER (Render uchun)
app = Flask('')
@app.route('/')
def home(): return "Bot uyg'oq!"
def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run).start()

# 2. BOT SOZLAMALARI
TOKEN = '8358476165:AAFsfhih8yWO0pXaJa_JCvndQ8DUUQZWads'
CHANNEL_ID = '@karnayuzb'
bot = telebot.TeleBot(TOKEN)
translator = Translator()

# XOTIRA FAYLI (Qayta-qayta tashlamasligi uchun)
DB_FILE = "sent_news.txt"
if not os.path.exists(DB_FILE):
    with open(DB_FILE, "w") as f: f.write("")

def is_sent(link):
    with open(DB_FILE, "r") as f:
        return link in f.read()

def save_sent(link):
    with open(DB_FILE, "a") as f:
        f.write(link + "\n")

# 3. MANBALAR (Hammasi bir joyda, aniq ishlashi uchun)
SOURCES = [
    ('Kun.uz', 'https://kun.uz/news/rss'),
    ('Daryo.uz', 'https://daryo.uz/feed/'),
    ('Qalampir.uz', 'https://qalampir.uz/uz/rss'),
    ('Gazeta.uz', 'https://www.gazeta.uz/uz/rss/'),
    ('Xabar.uz', 'https://xabar.uz/uz/rss'),
    ('BBC Uzbek', 'https://www.bbc.com/uzbek/index.xml'),
    ('Reuters', 'https://www.reutersagency.com/feed/?best-topics=world-news&post_type=best'),
    ('The New York Times', 'https://rss.nytimes.com/services/xml/rss/nyt/World.xml'),
    ('Associated Press', 'https://newsatme.com/go/ap/world'),
    ('Al Jazeera', 'https://www.aljazeera.com/xml/rss/all.xml'),
    ('The Washington Post', 'https://feeds.washingtonpost.com/rss/world'),
    ('Deutsche Welle', 'https://rss.dw.com/xml/rss-en-all'),
    ('Championat Asia', 'https://championat.asia/uz/news/rss'),
    ('Tribuna.uz', 'https://kun.uz/news/category/sport/rss'),
    ('TASS News', 'https://tass.com/rss/v2.xml')
]

# 4. RADIKAL TOZALASH
def clean_text(text):
    if not text: return ""
    blacklist = ['cookies', 'rozilik', 'lotinchada', 'na russkom', '©', 'tahririyat', 'muallif', 'reklama', 'facebook', 'instagram', 'telegram']
    lines = [line.strip() for line in text.split('\n') if len(line.strip()) > 50]
    cleaned = " ".join([l for l in lines if not any(bad in l.lower() for bad in blacklist)])
    return cleaned[:900]

def get_full_article(url):
    try:
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
        soup = BeautifulSoup(res.content, 'html.parser')
        img = soup.find("meta", property="og:image")
        img_url = img['content'] if img else None
        
        # Matnni qidirish
        for tag in soup(['script', 'style', 'nav', 'header', 'footer']): tag.decompose()
        paras = soup.find_all('p')
        text = clean_text("\n".join([p.get_text() for p in paras]))
        return img_url, text
    except: return None, ""

# 5. SALOMLASHISH
def check_greetings():
    tz = pytz.timezone('Asia/Tashkent')
    now = datetime.now(tz)
    hm = now.strftime("%H:%M")
    if hm == "06:00":
        bot.send_message(CHANNEL_ID, f"☀️ **Xayrli tong!**\n\nBugun: {now.strftime('%d-%m-%Y')}\nKuningiz barokatli o'tsin! 😊", parse_mode='Markdown')
        time.sleep(65)
    elif hm == "23:59":
        bot.send_message(CHANNEL_ID, "🌙 **Xayrli tun.**\nYaxshi dam oling! ✨", parse_mode='Markdown')
        time.sleep(65)

# 6. ASOSIY ISHCHI
def start_bot():
    while True:
        random.shuffle(SOURCES)
        for name, url in SOURCES:
            check_greetings()
            try:
                print(f"Skaner: {name}")
                feed = feedparser.parse(url)
                for entry in feed.entries[:2]:
                    if is_sent(entry.link): continue
                    
                    img_url, text = get_full_article(entry.link)
                    title = entry.title
                    
                    # AQLLI TARJIMA (Faqat ingliz tilidagi bo'lsa)
                    if any(word in url for word in ['reuters', 'nytimes', 'ap', 'aljazeera', 'washingtonpost', 'dw', 'tass']):
                        try:
                            title = translator.translate(title, dest='uz').text
                            if text: text = translator.translate(text, dest='uz').text
                        except: pass

                    if not text: text = "Yangilik matni topilmadi."

                    caption = f"📢 **{name.upper()}**\n\n**{title}**\n\n{text}...\n\n✅ @karnayuzb — Eng so'nggi xabarlar"
                    
                    try:
                        if img_url: bot.send_photo(CHANNEL_ID, img_url, caption=caption, parse_mode='Markdown')
                        else: bot.send_message(CHANNEL_ID, caption, parse_mode='Markdown')
                        
                        save_sent(entry.link)
                        time.sleep(20)
                    except: continue
            except: continue
        time.sleep(120)

if __name__ == "__main__":
    keep_alive()
    start_bot()
