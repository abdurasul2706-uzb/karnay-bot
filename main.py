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
def home(): return "Karnay.uzb Multi-Source System Active"
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

# 3. KENGAYTIRILGAN MANBALAR RO'YXATI
SOURCES = [
    # --- O'ZBEKISTON ---
    ('Kun.uz', 'https://kun.uz/news/rss'), ('Daryo.uz', 'https://daryo.uz/feed/'),
    ('Qalampir.uz', 'https://qalampir.uz/uz/rss'), ('Gazeta.uz', 'https://www.gazeta.uz/uz/rss/'),
    ('Uza.uz', 'https://uza.uz/uz/rss.php'), ('UzNews.uz', 'https://uznews.uz/uz/rss'),

    # --- SPORT (Yangi + Ommabop 5 ta) ---
    ('ESPN FC', 'https://www.espn.com/espn/rss/soccer/news'),
    ('Sky Sports', 'https://www.skysports.com/rss/12040'),
    ('Eurosport', 'https://www.eurosport.com/rss.xml'),
    ('Marca', 'https://e00-marca.uecdn.es/rss/en/index.xml'),
    ('Championat Asia', 'https://championat.asia/uz/news/rss'),

    # --- SAN'AT VA MADANIYAT (Yangi + Ommabop 5 ta) ---
    ('ArtNews', 'https://www.artnews.com/feed/'),
    ('The Art Newspaper', 'https://www.theartnewspaper.com/rss'),
    ('Culture.ru', 'https://www.culture.ru/rss'),
    ('Rolling Stone', 'https://www.rollingstone.com/feed/'),
    ('Afisha.uz', 'https://www.afisha.uz/uz/rss/'),

    # --- TEXNIKA VA TEXNOLOGIYA (Yangi + Ommabop 5 ta) ---
    ('The Verge', 'https://www.theverge.com/rss/index.xml'),
    ('Wired', 'https://www.wired.com/feed/rss'),
    ('CNET', 'https://www.cnet.com/rss/news/'),
    ('Gizmodo', 'https://gizmodo.com/rss'),
    ('Terabayt.uz', 'https://www.terabayt.uz/feed'),

    # --- DUNYO VA SIYOSAT (Avvalgilar) ---
    ('CNN World', 'http://rss.cnn.com/rss/edition_world.rss'),
    ('BBC News', 'http://feeds.bbci.co.uk/news/world/rss.xml'),
    ('The New York Times', 'https://rss.nytimes.com/services/xml/rss/nyt/World.xml'),
    ('Al Jazeera', 'https://www.aljazeera.com/xml/rss/all.xml'),
    ('TASS News', 'https://tass.com/rss/v2.xml'),
    ('Reuters', 'https://www.reutersagency.com/feed/?best-topics=world-news&post_type=best'),
    ('Deutsche Welle', 'https://rss.dw.com/xml/rss-en-all'),
    ('Politico', 'https://www.politico.com/rss/politicopicks.xml')
]

# 4. RADIKAL TOZALASH
def ultimate_clean(text, name):
    if not text: return None
    if any(x in name.upper() for x in ["TASS", "RIA", "RIA NOVOSTI"]):
        text = re.sub(r'^[A-Z\s,]+.*?(\d{1,2}|TASS|RIA)\s*.*?/', '', text, flags=re.IGNORECASE)

    trash_patterns = [
        r"Если вы нашли ошибку.*", r"Ctrl\+Enter.*", r"Выделите фрагмент.*",
        r"Подпишитесь на наш.*", r"Barcha huquqlar himoyalangan.*",
        r"Copyright.*", r"All rights reserved.*", r"Мнение редакции может не совпадать.*"
    ]
    for pattern in trash_patterns:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE | re.DOTALL)

    stop_list = ['vvevya', 'kod podtverjdeniya', 'vvedite', 'parol', 'cookies', 'lotinchada', 'na russkom']
    lines = text.split('\n')
    cleaned_lines = [l.strip() for l in lines if len(l.strip()) > 55 and not any(s in l.lower() for s in stop_list)]
    
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
        
        # TASS uchun logo, boshqalar uchun og:image
        if "TASS" in name.upper():
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
        random.shuffle(SOURCES) # Hammasini chalkashtirib tashlash
        for name, url in SOURCES:
            try:
                feed = feedparser.parse(url)
                for entry in feed.entries[:1]:
                    if is_duplicate(entry.link): continue
                    
                    img_url, text = get_content(entry.link, name)
                    if not text: continue
                    
                    title_uz = smart_translate(entry.title)
                    text_uz = smart_translate(text)

                    # TASS brendini tozalash
                    if "TASS" in name.upper(): 
                        title_uz = title_uz.replace("TASS:", "").strip()

                    caption = f"📢 **KARNAY.UZB**\n\n**{title_uz}**\n\n{text_uz}...\n\n✅ @karnayuzb — Dunyo sizning qo'lingizda!"
                    
                    try:
                        if img_url:
                            bot.send_photo(CHANNEL_ID, img_url, caption=caption, parse_mode='Markdown')
                        else:
                            bot.send_message(CHANNEL_ID, caption, parse_mode='Markdown')
                        
                        log_link(entry.link)
                        time.sleep(45) 
                    except: continue
            except: continue
        time.sleep(200)

if __name__ == "__main__":
    keep_alive()
    start_processing()
