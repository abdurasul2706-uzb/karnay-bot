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

# 1. SERVER (Render uchun)
app = Flask('')
@app.route('/')
def home(): return "Karnay.uzb Professional Media System is Live 🚀"
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
    conn = sqlite3.connect('karnay_pro.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS news (link TEXT PRIMARY KEY)''')
    conn.commit()
    conn.close()

def is_duplicate(link):
    conn = sqlite3.connect('karnay_pro.db')
    c = conn.cursor()
    c.execute("SELECT * FROM news WHERE link=?", (link,))
    res = c.fetchone()
    conn.close()
    return res is not None

def save_news(link):
    conn = sqlite3.connect('karnay_pro.db')
    c = conn.cursor()
    try:
        c.execute("INSERT INTO news VALUES (?)", (link,))
        conn.commit()
    except: pass
    conn.close()

# 4. MANBALAR (To'liq ro'yxat)
SOURCES = [
    # O'zbekiston
    ('Kun.uz', 'https://kun.uz/news/rss'), ('Daryo.uz', 'https://daryo.uz/feed/'),
    ('Qalampir.uz', 'https://qalampir.uz/uz/rss'), ('Gazeta.uz', 'https://www.gazeta.uz/uz/rss/'),
    ('Uza.uz', 'https://uza.uz/uz/rss.php'), ('Terabayt.uz', 'https://www.terabayt.uz/feed'),
    # Jahon
    ('CNN', 'http://rss.cnn.com/rss/edition_world.rss'), ('BBC News', 'http://feeds.bbci.co.uk/news/world/rss.xml'),
    ('NY Times', 'https://rss.nytimes.com/services/xml/rss/nyt/World.xml'), ('Al Jazeera', 'https://www.aljazeera.com/xml/rss/all.xml'),
    # Rossiya
    ('TASS', 'https://tass.com/rss/v2.xml'), ('RIA Novosti', 'https://ria.ru/export/rss2/world/index.xml'),
    # Sport & San'at
    ('Sky Sports', 'https://www.skysports.com/rss/12040'), ('ArtNews', 'https://www.artnews.com/feed/'),
    ('Afisha.uz', 'https://www.afisha.uz/uz/rss/'), ('Championat Asia', 'https://championat.asia/uz/news/rss')
]

# 5. MATNNI "TIRILTIRISH" VA TOZALASH (Yangi algoritm)
def professional_clean(text):
    if not text: return None
    
    # 1. Texnik axlatlarni o'chirish (Cookies, Ctrl+Enter, email va h.k)
    trash_patterns = [
        r"Если вы нашли ошибку.*", r"Ctrl\+Enter.*", r"cookies.*", r"Lotincha", 
        r"Na russkom", r"Biz sayt ishlashini.*", r"Ro'yxatdan o'tish", r"Reklama",
        r"Tahririyat fikri.*", r"©.*", r"Copyright.*", r"All rights reserved.*"
    ]
    for pattern in trash_patterns:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE | re.DOTALL)

    # 2. Matnni qismlarga bo'lish va keraksiz qisqa qatorlarni o'chirish
    # Ammo o'ta qisqa qilmaslik uchun limitni 40 belgiga tushiramiz
    paragraphs = [p.strip() for p in text.split('\n') if len(p.strip()) > 40]
    
    # 3. Faqat mazmunli qismini birlashtirish (Dastlabki 4-5 ta mazmunli paragraf)
    full_body = "\n\n".join(paragraphs[:5]) 
    
    return full_body.strip()

def smart_translate(text):
    try:
        if not text: return ""
        # Matn tilini aniqlaymiz, agar o'zbekcha bo'lmasa tarjima qilamiz
        detect = translator.detect(text).lang
        if detect != 'uz':
            # Google Translate ba'zan matnni buzadi, shuning uchun bo'laklab tarjima qilamiz
            translated = translator.translate(text, dest='uz').text
            return translated
        return text
    except: return text

def get_content(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        r = requests.get(url, headers=headers, timeout=20)
        soup = BeautifulSoup(r.content, 'html.parser')
        
        # Rasm topish
        img_tag = soup.find("meta", property="og:image")
        img_url = img_tag['content'] if img_tag else CHANNEL_LOGO
        
        # Matnni yig'ish (faqat <p> teglari ichidagi matnni olamiz - bu saytdagi menyularni chetlab o'tadi)
        paras = soup.find_all('p')
        raw_text = "\n".join([p.get_text() for p in paras])
        
        cleaned = professional_clean(raw_text)
        return img_url, cleaned
    except: return CHANNEL_LOGO, None

# 6. TABRIKLAR TIZIMI
def check_greetings():
    now = datetime.now(uzb_tz).strftime("%H:%M")
    if now == "06:00":
        bot.send_message(CHANNEL_ID, "☀️ **Xayrli tong, aziz Karnay.uzb obunachilari!**\n\nBugungi kuningiz unumli va omadli o'tsin. Yangi marralar sari olg'a! 😊🚀", parse_mode='Markdown')
        time.sleep(61)
    elif now == "23:59":
        bot.send_message(CHANNEL_ID, "🌙 **Tuningiz osuda o'tsin!**\n\nBugungi eng muhim xabarlarni biz bilan kuzatganingiz uchun rahmat. Yaxshi dam oling, ertaga uchrashguncha! ✨", parse_mode='Markdown')
        time.sleep(61)

# 7. ASOSIY SIKL
def start_processing():
    init_db()
    while True:
        random.shuffle(SOURCES)
        for name, url in SOURCES:
            check_greetings()
            try:
                feed = feedparser.parse(url)
                for entry in feed.entries[:3]:
                    if is_duplicate(entry.link): continue
                    
                    img, text = get_content(entry.link)
                    if not text or len(text) < 150: continue # Juda qisqa matnlarni tashlamaydi
                    
                    # Tarjima va Sarlavha
                    title = smart_translate(entry.title)
                    body = smart_translate(text)
                    
                    # Sayt belgilari va brendlarni tozalash
                    title = re.sub(r'^(TASS|RIA|RIA NOVOSTI|KUN\.UZ):', '', title, flags=re.IGNORECASE).strip()

                    # POST FORMATI
                    caption = (
                        f"📢 **KARNAY.UZB**\n\n"
                        f"⚡️ **{title.upper()}**\n\n"
                        f"{body}\n\n"
                        f"🔗 **Manba:** Karnay.uzb\n"
                        f"✅ @karnayuzb — Dunyo sizning qo'lingizda!"
