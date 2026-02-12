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

# 1. SERVER SOZLAMALARI
app = Flask('')
@app.route('/')
def home(): return "Karnay.uzb Bot Ishlamoqda!"
def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run).start()

# 2. BOT SOZLAMALARI
TOKEN = '8358476165:AAFsfhih8yWO0pXaJa_JCvndQ8DUUQZWads'
CHANNEL_ID = '@karnayuzb'
# O'z kanalingiz logotipi URL manzili (TASS uchun)
CHANNEL_LOGO = "https://i.postimg.cc/mD8zYpXG/Karnay-uzb.jpg" 

bot = telebot.TeleBot(TOKEN)
translator = Translator()

# XOTIRA TIZIMI (Takrorlanmaslik kafolati)
SENT_NEWS_FILE = "sent_links.txt"
if not os.path.exists(SENT_NEWS_FILE):
    with open(SENT_NEWS_FILE, "w") as f: pass

def is_already_sent(link):
    with open(SENT_NEWS_FILE, "r") as f:
        return link in f.read()

def mark_as_sent(link):
    with open(SENT_NEWS_FILE, "a") as f:
        f.write(link + "\n")

# 3. MANBALAR (O'zbekiston manbalari ko'paytirildi va hammasi aralashtirildi)
SOURCES = [
    ('Kun.uz', 'https://kun.uz/news/rss'),
    ('Daryo.uz', 'https://daryo.uz/feed/'),
    ('Qalampir.uz', 'https://qalampir.uz/uz/rss'),
    ('Gazeta.uz', 'https://www.gazeta.uz/uz/rss/'),
    ('Xabar.uz', 'https://xabar.uz/uz/rss'),
    ('Uza.uz', 'https://uza.uz/uz/rss.php'),
    ('Zamon.uz', 'https://zamon.uz/uz/rss'),
    ('Bugun.uz', 'https://bugun.uz/feed/'),
    ('Anhor.uz', 'https://anhor.uz/feed/'),
    ('UzNews.uz', 'https://uznews.uz/uz/rss'),
    ('TASS News', 'https://tass.com/rss/v2.xml'),
    ('Reuters', 'https://www.reutersagency.com/feed/?best-topics=world-news&post_type=best'),
    ('BBC Uzbek', 'https://www.bbc.com/uzbek/index.xml'),
    ('The New York Times', 'https://rss.nytimes.com/services/xml/rss/nyt/World.xml'),
    ('Associated Press', 'https://newsatme.com/go/ap/world'),
    ('Al Jazeera', 'https://www.aljazeera.com/xml/rss/all.xml'),
    ('Deutsche Welle', 'https://rss.dw.com/xml/rss-en-all'),
    ('Championat Asia', 'https://championat.asia/uz/news/rss')
]
random.shuffle(SOURCES) # Manbalarni har doim chalkashtirib tashlash

# 4. TOZALASH VA FILTRLASH (TASS va boshqalar uchun)
def professional_clean(text, source_name):
    if not text: return None
    
    # TASS xabarlaridagi texnik qismlarni o'chirish
    if "TASS" in source_name or "TASS" in text:
        text = re.sub(r'^[A-Z\s]+,\s\d+\s[A-Za-z]+\.\s/TASS/\.', '', text)
        text = re.sub(r'\(TASS\)', '', text)
        text = text.replace('MOSKVA', '').replace('TASS', '')

    blacklist = ['cookies', 'yaxshilash', 'rozilik', 'lotinchada', 'na russkom', '©', 'facebook', 'instagram']
    lines = [line.strip() for line in text.split('\n') if len(line.strip()) > 60]
    cleaned = " ".join([l for l in lines if not any(bad in l.lower() for bad in blacklist)])
    
    return cleaned.strip()[:900] if len(cleaned) > 150 else None

def get_content(url, source_name):
    try:
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
        soup = BeautifulSoup(res.content, 'html.parser')
        
        # Rasm tanlash (TASS bo'lsa o'z logotipingiz, bo'lmasa saytdan)
        if "TASS" in source_name:
            img_url = CHANNEL_LOGO
        else:
            img = soup.find("meta", property="og:image")
            img_url = img['content'] if img else None
            
        for tag in soup(['script', 'style', 'nav', 'header', 'footer']): tag.decompose()
        paras = soup.find_all('p')
        text = professional_clean("\n".join([p.get_text() for p in paras]), source_name)
        
        return img_url, text
    except: return None, None

# 5. ASOSIY ISHCHI FUNKSIYA
def run_bot():
    while True:
        random.shuffle(SOURCES) # Har siklda manbalarni yana bir bor aralashtirish
        for name, url in SOURCES:
            try:
                feed = feedparser.parse(url)
                for entry in feed.entries[:2]:
                    if is_already_sent(entry.link): continue
                    
                    img_url, text = get_content(entry.link, name)
                    if not text: continue
                    
                    title = entry.title
                    # Chet el manbalarini tarjima qilish
                    if any(x in url.lower() for x in ['reuters', 'tass', 'nytimes', 'ap', 'aljazeera', 'dw']):
                        try:
                            title = translator.translate(title, dest='uz').text
                            text = translator.translate(text, dest='uz').text
                        except: pass

                    # TASS sarlavhasini tozalash
                    if "TASS" in name:
                        title = title.replace('TASS:', '').strip()

                    # FORMATLASH (Siz so'ragan: Karnay.uzb brendi bilan)
                    caption = f"📢 **KARNAY.UZB**\n\n"
                    caption += f"**{title}**\n\n"
                    caption += f"{text}...\n\n"
                    caption += f"✅ @karnayuzb — Dunyo sizning qo'lingizda!\n"
                    caption += f"#Karnay #Yangiliklar #O'zbekiston"

                    try:
                        if img_url:
                            bot.send_photo(CHANNEL_ID, img_url, caption=caption, parse_mode='Markdown')
                        else:
                            bot.send_message(CHANNEL_ID, caption, parse_mode='Markdown')
                        
                        mark_as_sent(entry.link)
                        time.sleep(30) # Spamsiz yuborish
                    except Exception as e:
                        if "caption is too long" in str(e):
                            # Agar matn juda uzun bo'lib ketsa, qisqartirib qayta urinish
                            bot.send_message(CHANNEL_ID, caption[:1024], parse_mode='Markdown')
                            mark_as_sent(entry.link)
                        continue
            except: continue
        time.sleep(300) # 5 daqiqa dam olib keyin yangi aylanish

if __name__ == "__main__":
    keep_alive()
    run_bot()
