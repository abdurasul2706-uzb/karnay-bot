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

# 1. SERVER (Bot o'chmasligi uchun)
app = Flask('')
@app.route('/')
def home(): return "Karnay.uzb Bot Ishlamoqda!"
def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run).start()

# 2. SOZLAMALAR
TOKEN = '8358476165:AAFsfhih8yWO0pXaJa_JCvndQ8DUUQZWads'
CHANNEL_ID = '@karnayuzb'
CHANNEL_LOGO = "https://i.postimg.cc/mD8zYpXG/Karnay-uzb.jpg" 

bot = telebot.TeleBot(TOKEN)
translator = Translator()

# XOTIRA (Faylga yozish - Takrorlanmaslik kafolati)
DB_FILE = "sent_links_log.txt"
if not os.path.exists(DB_FILE):
    with open(DB_FILE, "w") as f: pass

def is_published(link):
    try:
        with open(DB_FILE, "r") as f:
            return link in f.read()
    except: return False

def save_news(link):
    try:
        with open(DB_FILE, "a") as f:
            f.write(link + "\n")
    except: pass

# 3. MANBALAR (Siz so'ragan barcha 20+ manba, chalkashtirilgan)
SOURCES = [
    ('Kun.uz', 'https://kun.uz/news/rss'), ('Daryo.uz', 'https://daryo.uz/feed/'),
    ('Qalampir.uz', 'https://qalampir.uz/uz/rss'), ('Gazeta.uz', 'https://www.gazeta.uz/uz/rss/'),
    ('Xabar.uz', 'https://xabar.uz/uz/rss'), ('Uza.uz', 'https://uza.uz/uz/rss.php'),
    ('UzNews.uz', 'https://uznews.uz/uz/rss'), ('Zamon.uz', 'https://zamon.uz/uz/rss'),
    ('Bugun.uz', 'https://bugun.uz/feed/'), ('Anhor.uz', 'https://anhor.uz/feed/'),
    ('TASS News', 'https://tass.com/rss/v2.xml'),
    ('Reuters', 'https://www.reutersagency.com/feed/?best-topics=world-news&post_type=best'),
    ('BBC Uzbek', 'https://www.bbc.com/uzbek/index.xml'),
    ('The New York Times', 'https://rss.nytimes.com/services/xml/rss/nyt/World.xml'),
    ('Associated Press', 'https://newsatme.com/go/ap/world'),
    ('Al Jazeera', 'https://www.aljazeera.com/xml/rss/all.xml'),
    ('The Washington Post', 'https://feeds.washingtonpost.com/rss/world'),
    ('Deutsche Welle', 'https://rss.dw.com/xml/rss-en-all'),
    ('TechCrunch', 'https://techcrunch.com/feed/'),
    ('Championat Asia', 'https://championat.asia/uz/news/rss')
]

# 4. RADIKAL TOZALASH (Endi "Введите почту" ham o'chadi)
def professional_clean(text, name):
    if not text: return None
    
    # TASS matn boshini tozalash (MOSKVA, Sana va h.k.)
    if "TASS" in name:
        text = re.sub(r'^[A-Z\s,]+.*?(\d{1,2}|TASS)\s*.*?/', '', text, flags=re.IGNORECASE)
        text = text.replace("MOSKVA", "").replace("TASS", "").replace("(TASS)", "").strip()

    # STOP-SO'ZLAR (Bular qatnashgan qatorlar butunlay o'chiriladi)
    stop_words = [
        'введите', 'почту', 'номер телефона', 'вышлем код', 'пароль', 'регистрация',
        'cookies', 'rozilik', 'lotinchada', 'na russkom', 'подтверждения', 'установить новый',
        'facebook', 'instagram', 'obuna bo‘ling', 'reklama', 'tahririyat', '©'
    ]
    
    lines = text.split('\n')
    cleaned_lines = []
    for line in lines:
        line = line.strip()
        # Agar qatorda stop-so'z bo'lsa yoki qator juda qisqa bo'lsa - o'chiramiz
        if any(stop in line.lower() for stop in stop_words): continue
        if len(line) < 60: continue 
        cleaned_lines.append(line)
    
    final = " ".join(cleaned_lines)
    return final[:950] if len(final) > 100 else None

def get_content(url, name):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(res.content, 'html.parser')
        
        # TASS bo'lsa o'z logotipingiz, bo'lmasa saytdan rasm
        img_url = CHANNEL_LOGO if "TASS" in name else (soup.find("meta", property="og:image")['content'] if soup.find("meta", property="og:image") else None)

        for tag in soup(['script', 'style', 'nav', 'header', 'footer', 'aside', 'form']): tag.decompose()
        paras = soup.find_all('p')
        text = professional_clean("\n".join([p.get_text() for p in paras]), name)
        
        return img_url, text
    except: return None, None

# 5. ASOSIY ISHCHI
def start_bot():
    while True:
        random.shuffle(SOURCES)
        for name, url in SOURCES:
            try:
                feed = feedparser.parse(url)
                # Faqat eng yangi 2 ta xabarni tekshirish (Eski xabarlar chiqmasligi uchun)
                for entry in feed.entries[:2]:
                    if is_published(entry.link): continue
                    
                    img_url, text = get_content(entry.link, name)
                    if not text: continue
                    
                    title = entry.title
                    # Tarjima (Rus/Ingliz bo'lsa)
                    if any(x in url.lower() for x in ['tass', 'reuters', 'nytimes', 'ap', 'aljazeera', 'washingtonpost', 'dw', 'techcrunch']):
                        try:
                            title = translator.translate(title, dest='uz').text
                            text = translator.translate(text, dest='uz').text
                        except: pass

                    # TASS sarlavhasini tozalash
                    if "TASS" in name: title = title.replace("TASS:", "").strip()

                    # FORMATLASH (Faqat KARNAY.UZB brendi bilan)
                    caption = f"📢 **KARNAY.UZB**\n\n**{title}**\n\n{text}...\n\n✅ @karnayuzb — Dunyo sizning qo'lingizda!"
                    
                    try:
                        if img_url: bot.send_photo(CHANNEL_ID, img_url, caption=caption, parse_mode='Markdown')
                        else: bot.send_message(CHANNEL_ID, caption, parse_mode='Markdown')
                        
                        save_news(entry.link)
                        time.sleep(30)
                    except: continue
            except: continue
        time.sleep(240) # Har 4 daqiqada yangi aylanish

if __name__ == "__main__":
    keep_alive()
    start_bot()
