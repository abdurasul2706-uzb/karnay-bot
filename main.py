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

# 1. SERVER
app = Flask('')
@app.route('/')
def home(): return "Karnay.uzb Global Network Active"
def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run).start()

# 2. BOT SOZLAMALARI
TOKEN = '8358476165:AAFsfhih8yWO0pXaJa_JCvndQ8DUUQZWads'
CHANNEL_ID = '@karnayuzb'
CHANNEL_LOGO = "https://i.postimg.cc/mD8zYpXG/Karnay-uzb.jpg" 

bot = telebot.TeleBot(TOKEN)
translator = Translator()

# XOTIRA TIZIMI
DB_FILE = "global_news_db.txt"
if not os.path.exists(DB_FILE):
    with open(DB_FILE, "w") as f: pass

def is_duplicate(link):
    try:
        with open(DB_FILE, "r") as f:
            return link in f.read()
    except: return False

def log_link(link):
    try:
        with open(DB_FILE, "a") as f:
            f.write(link + "\n")
    except: pass

# 3. GLOBAL MANBALAR RO'YXATI (Yangi qo'shilganlar bilan)
SOURCES = [
    # --- O'ZBEKISTON ---
    ('Kun.uz', 'https://kun.uz/news/rss'), ('Daryo.uz', 'https://daryo.uz/feed/'),
    ('Qalampir.uz', 'https://qalampir.uz/uz/rss'), ('Gazeta.uz', 'https://www.gazeta.uz/uz/rss/'),
    ('Uza.uz', 'https://uza.uz/uz/rss.php'), ('Terabayt.uz', 'https://www.terabayt.uz/feed'),
    
    # --- AQSH (USA - TOP 5) ---
    ('CNN World', 'http://rss.cnn.com/rss/edition_world.rss'),
    ('The New York Times', 'https://rss.nytimes.com/services/xml/rss/nyt/World.xml'),
    ('The Washington Post', 'https://feeds.washingtonpost.com/rss/world'),
    ('ABC News', 'https://abcnews.go.com/abcnews/internationalheadlines'),
    ('USA Today', 'https://www.usatoday.com/rss/world/'),

    # --- YEVROPA (EUROPE - TOP 5) ---
    ('BBC News', 'http://feeds.bbci.co.uk/news/world/rss.xml'),
    ('The Guardian', 'https://www.theguardian.com/world/rss'),
    ('Euronews', 'https://www.euronews.com/rss?level=vertical&name=news'),
    ('Deutsche Welle', 'https://rss.dw.com/xml/rss-en-all'),
    ('Le Monde', 'https://www.lemonde.fr/en/world/rss_full.xml'),

    # --- OSIYO (ASIA - TOP 5) ---
    ('Al Jazeera', 'https://www.aljazeera.com/xml/rss/all.xml'),
    ('Nikkei Asia', 'https://asia.nikkei.com/rss/feed/nar'),
    ('South China Morning Post', 'https://www.scmp.com/rss/91/feed.xml'),
    ('CNA Asia', 'https://www.channelnewsasia.com/rssfeeds/8395981'),
    ('The Japan Times', 'https://www.japantimes.co.jp/feed/'),

    # --- ROSSIYA (RUSSIA - TOP 3) ---
    ('TASS News', 'https://tass.com/rss/v2.xml'),
    ('RIA Novosti', 'https://ria.ru/export/rss2/world/index.xml'),
    ('Kommersant', 'https://www.kommersant.ru/RSS/news.xml'),

    # --- SIYOSAT (POLITICS - TOP 3) ---
    ('Politico', 'https://www.politico.com/rss/politicopicks.xml'),
    ('Foreign Affairs', 'https://www.foreignaffairs.com/rss.xml'),
    ('The Economist', 'https://www.economist.com/international/rss.xml')
]

# 4. RADIKAL TOZALASH
def ultimate_clean(text, name):
    if not text: return None
    if "TASS" in name or "RIA" in name:
        text = re.sub(r'^[A-Z\s,]+.*?(\d{1,2}|TASS|RIA)\s*.*?/', '', text, flags=re.IGNORECASE)

    trash_patterns = [
        r"Если вы нашли ошибку.*", r"Ctrl\+Enter.*", r"Выделите фрагмент.*",
        r"Подпишитесь на наш.*", r"Barcha huquqlar himoyalangan.*",
        r"Copyright.*", r"All rights reserved.*"
    ]
    for pattern in trash_patterns:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE | re.DOTALL)

    stop_list = ['vvevya', 'kod podtverjdeniya', 'vvedite', 'parol', 'cookies', 'lotinchada', 'na russkom']
    lines = text.split('\n')
    cleaned_lines = [l.strip() for l in lines if len(l.strip()) > 50 and not any(s in l.lower() for s in stop_list)]
    
    final_text = " ".join(cleaned_lines).strip()
    return final_text[:950] if len(final_text) > 100 else None

# 5. MAJBURIY TARJIMA
def smart_translate(text):
    try:
        detected = translator.detect(text).lang
        if detected != 'uz':
            return translator.translate(text, dest='uz').text
        return text
    except: return text

def get_content(url, name):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers, timeout=20)
        soup = BeautifulSoup(res.content, 'html.parser')
        
        if "TASS" in name or "RIA" in name:
            img_url = CHANNEL_LOGO
        else:
            img = soup.find("meta", property="og:image")
            img_url = img['content'] if img else None

        for tag in soup(['script', 'style', 'nav', 'header', 'footer', 'aside', 'form', 'button']): tag.decompose()
        paras = soup.find_all('p')
        raw_text = "\n".join([p.get_text() for p in paras])
        
        cleaned = ultimate_clean(raw_text, name)
        return img_url, cleaned
    except: return None, None

# 6. ASOSIY ISHCHI
def start_processing():
    while True:
        random.shuffle(SOURCES) # Hammasini chalkashtirish
        for name, url in SOURCES:
            try:
                feed = feedparser.parse(url)
                for entry in feed.entries[:1]: # Eng yangi 1 tasini tekshirish
                    if is_duplicate(entry.link): continue
                    
                    img_url, text = get_content(entry.link, name)
                    if not text: continue
                    
                    title_uz = smart_translate(entry.title)
                    text_uz = smart_translate(text)

                    if "TASS" in name or "RIA" in name: 
                        title_uz = title_uz.replace("TASS:", "").replace("RIA:", "").strip()

                    caption = f"📢 **KARNAY.UZB**\n\n**{title_uz}**\n\n{text_uz}...\n\n✅ @karnayuzb — Dunyo sizning qo'lingizda!"
                    
                    try:
                        if img_url:
                            bot.send_photo(CHANNEL_ID, img_url, caption=caption, parse_mode='Markdown')
                        else:
                            bot.send_message(CHANNEL_ID, caption, parse_mode='Markdown')
                        
                        log_link(entry.link)
                        time.sleep(45) # Navbat bilan tashlash
                    except: continue
            except: continue
        time.sleep(180) # 3 daqiqa kutish

if __name__ == "__main__":
    keep_alive()
    start_processing()
