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

# 1. SERVER SOZLAMASI (Render o'chib qolmasligi uchun)
app = Flask('')
@app.route('/')
def home(): return "Karnay.uzb Professional Media Hub is Running 🚀"
def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run).start()

# 2. BOT VA TRANSLATOR SOZLAMALARI
TOKEN = '8358476165:AAFsfhih8yWO0pXaJa_JCvndQ8DUUQZWads'
CHANNEL_ID = '@karnayuzb'
CHANNEL_LOGO = "https://i.postimg.cc/mD8zYpXG/Karnay-uzb.jpg"
bot = telebot.TeleBot(TOKEN)
translator = Translator()
uzb_tz = pytz.timezone('Asia/Tashkent')

# 3. MA'LUMOTLAR BAZASI (SQLite)
def init_db():
    conn = sqlite3.connect('karnay_ultimate.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS news (link TEXT PRIMARY KEY)''')
    conn.commit()
    conn.close()

def is_duplicate(link):
    conn = sqlite3.connect('karnay_ultimate.db')
    c = conn.cursor()
    c.execute("SELECT * FROM news WHERE link=?", (link,))
    res = c.fetchone()
    conn.close()
    return res is not None

def save_news(link):
    conn = sqlite3.connect('karnay_ultimate.db')
    c = conn.cursor()
    try:
        c.execute("INSERT INTO news VALUES (?)", (link,))
        conn.commit()
    except: pass
    conn.close()

# 4. VAQT FILTRI (Faqat oxirgi 24 soat ichidagi xabarlar)
def is_recent(entry):
    try:
        published_parsed = entry.get('published_parsed') or entry.get('updated_parsed')
        if not published_parsed: return True
        dt = datetime.fromtimestamp(time.mktime(published_parsed), pytz.utc)
        now = datetime.now(pytz.utc)
        return (now - dt).total_seconds() < 86400
    except: return True

# 5. MATNNI PROFESSIONAL TOZALASH (Trash cleaner)
def ultimate_clean(text):
    if not text: return ""
    # Sayt texnik yozuvlari va reklamalarni o'chirish
    trash_list = [
        r"Введите почту или номер телефона.*", r"вышлем код подтверждения.*",
        r"установить новый пароль.*", r"Если вы нашли ошибку.*", r"Ctrl\+Enter.*", 
        r"cookies.*", r"Lotincha", r"Na russkom", r"Biz sayt.*", r"©.*",
        r"Ro'yxatdan o'tish.*", r"Tahririyat fikri.*", r"Barcha huquqlar.*"
    ]
    for pattern in trash_list:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE | re.DOTALL)
    
    # Paragraflarni yig'ish (faqat mazmunlilari)
    paragraphs = [p.strip() for p in text.split('\n') if len(p.strip()) > 75]
    
    # Eng yaxshi 4-6 ta paragrafni birlashtirish
    return "\n\n".join(paragraphs[:6])

def smart_translate(text):
    if not text: return ""
    try:
        # Tarjima tizimi barqarorligi uchun 2 marta urinish
        for _ in range(2):
            try:
                res = translator.translate(text, dest='uz')
                return res.text
            except: time.sleep(1)
        return text
    except: return text

def get_content_data(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        r = requests.get(url, headers=headers, timeout=20)
        soup = BeautifulSoup(r.content, 'html.parser')
        
        # Rasm topish
        img_tag = soup.find("meta", property="og:image")
        img_url = img_tag['content'] if img_tag else CHANNEL_LOGO
        
        # Keraksiz teglarni o'chirish
        for tag in soup(['script', 'style', 'nav', 'header', 'footer', 'form', 'aside']): tag.decompose()
        
        # Matnni yig'ish
        paras = soup.find_all('p')
        raw_text = "\n".join([p.get_text() for p in paras])
        
        return img_url, ultimate_clean(raw_text)
    except: return CHANNEL_LOGO, ""

# 6. TABRIKLAR
def send_greetings():
    now = datetime.now(uzb_tz).strftime("%H:%M")
    if now == "06:00":
        bot.send_message(CHANNEL_ID, "☀️ **Xayrli tong, aziz Karnay.uzb obunachilari!**\n\nBugungi kuningiz yangiliklarga va muvaffaqiyatlarga boy bo'lsin! 🚀", parse_mode='Markdown')
        time.sleep(65)
    elif now == "23:59":
        bot.send_message(CHANNEL_ID, "🌙 **Xayrli tun!**\n\nBugun biz bilan bo'lganingiz uchun rahmat. Ertagacha uchrashguncha! ✨", parse_mode='Markdown')
        time.sleep(65)

# 7. ASOSIY LOGIKA (Xatolardan xulosa qilingan variant)
def start_processing():
    init_db()
    # 48 ta manba (qisqartirilgan, lekin ishonchli ro'yxat)
    SOURCES = [
        ('Kun.uz', 'https://kun.uz/news/rss'), ('Daryo.uz', 'https://daryo.uz/feed/'),
        ('Qalampir.uz', 'https://qalampir.uz/uz/rss'), ('Gazeta.uz', 'https://www.gazeta.uz/uz/rss/'),
        ('Uza.uz', 'https://uza.uz/uz/rss.php'), ('CNN', 'http://rss.cnn.com/rss/edition_world.rss'),
        ('BBC World', 'http://feeds.bbci.co.uk/news/world/rss.xml'), ('TASS', 'https://tass.com/rss/v2.xml'),
        ('Reuters', 'https://www.reutersagency.com/feed/?best-topics=world-news&post_type=best'),
        ('Championat Asia', 'https://championat.asia/uz/news/rss'), ('The Verge', 'https://www.theverge.com/rss/index.xml')
    ]

    while True:
        random.shuffle(SOURCES)
        for name, url in SOURCES:
            send_greetings()
            try:
                feed = feedparser.parse(url)
                for entry in feed.entries[:5]:
                    if is_duplicate(entry.link) or not is_recent(entry):
                        continue
                    
                    img, text = get_content_data(entry.link)
                    if not text or len(text) < 150: continue
                    
                    title = smart_translate(entry.title)
                    body = smart_translate(text)
                    
                    # Sarlavhadan brendlarni o'chirish
                    title = re.sub(r'^(TASS|RIA|KUN\.UZ|DARYO):', '', title, flags=re.IGNORECASE).strip()

                    # Post formati
                    caption = f"📢 **KARNAY.UZB**\n\n⚡️ **{title.upper()}**\n\n{body}\n\n🔗 **Manba:** Karnay.uzb\n✅ @karnayuzb — Dunyo sizning qo'lingizda!"

                    # GAPNI OXIRIDA CHIROYLI KESISH (Tugal matn effekti)
                    if len(caption) > 1024:
                        short_body = body[:780]
                        last_dot = short_body.rfind('.')
                        final_body = body[:last_dot + 1] if last_dot != -1 else body[:750]
                        caption = f"📢 **KARNAY.UZB**\n\n⚡️ **{title.upper()}**\n\n{final_body}\n\n🔗 **Manba:** Karnay.uzb\n✅ @karnayuzb"

                    try:
                        bot.send_photo(CHANNEL_ID, img, caption=caption, parse_mode='Markdown')
                        save_news(entry.link)
                        print(f"✅ Post yuborildi: {name}")
                        time.sleep(60) 
                    except Exception as e:
                        print(f"⚠️ Rasmda xato, logotip bilan yuboriladi: {e}")
                        bot.send_photo(CHANNEL_ID, CHANNEL_LOGO, caption=caption, parse_mode='Markdown')
                        save_news(entry.link)
                        time.sleep(60)
            except: continue
        time.sleep(300)

if __name__ == "__main__":
    keep_alive()
    start_processing()
