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
def home(): return "Karnay.uzb Professional System"
def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run).start()

# 2. BOT SOZLAMALARI
TOKEN = '8358476165:AAFsfhih8yWO0pXaJa_JCvndQ8DUUQZWads'
CHANNEL_ID = '@karnayuzb'
CHANNEL_LOGO = "https://i.postimg.cc/mD8zYpXG/Karnay-uzb.jpg" 

bot = telebot.TeleBot(TOKEN)
translator = Translator()

# XOTIRA TIZIMI (Faylga asoslangan)
DB_FILE = "published_news.txt"
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

# 3. KENGAYTIRILGAN MANBALAR (Sport, San'at, Texnika qo'shildi)
SOURCES = [
    # Sport & Madaniyat
    ('Championat Asia', 'https://championat.asia/uz/news/rss'),
    ('Tribuna.uz', 'https://kun.uz/news/category/sport/rss'),
    ('Afisha.uz', 'https://www.afisha.uz/uz/rss/'),
    ('ArtNews', 'https://www.artnews.com/feed/'),
    # Texnologiya
    ('Terabayt.uz', 'https://www.terabayt.uz/feed'),
    ('TechCrunch', 'https://techcrunch.com/feed/'),
    ('The Verge', 'https://www.theverge.com/rss/index.xml'),
    # Siyosat & Jamiyat (UZ)
    ('Kun.uz', 'https://kun.uz/news/rss'),
    ('Daryo.uz', 'https://daryo.uz/feed/'),
    ('Qalampir.uz', 'https://qalampir.uz/uz/rss'),
    ('Gazeta.uz', 'https://www.gazeta.uz/uz/rss/'),
    ('Uza.uz', 'https://uza.uz/uz/rss.php'),
    ('UzNews.uz', 'https://uznews.uz/uz/rss'),
    # Jahon
    ('TASS News', 'https://tass.com/rss/v2.xml'),
    ('Reuters', 'https://www.reutersagency.com/feed/?best-topics=world-news&post_type=best'),
    ('BBC Uzbek', 'https://www.bbc.com/uzbek/index.xml'),
    ('Al Jazeera', 'https://www.aljazeera.com/xml/rss/all.xml')
]

# 4. RADIKAL TOZALASH (Ctrl+Enter va boshqa chiqindilarni yo'qotish)
def ultimate_clean(text, name):
    if not text: return None
    
    # 1. TASS boshidagi MOSKVA/Sana larni o'chirish
    if "TASS" in name:
        text = re.sub(r'^[A-Z\s,]+.*?(\d{1,2}|TASS)\s*.*?/', '', text, flags=re.IGNORECASE)

    # 2. Matn ohiridagi barcha "axlat" gaplar (Ctrl+Enter, email, etc.)
    trash_patterns = [
        r"Если вы нашли ошибку.*", r"Ctrl\+Enter.*", r"Выделите фрагмент.*",
        r"Подпишитесь на наш.*", r"Barcha huquqlar himoyalangan.*",
        r"Мнение редакции может не совпадать.*", r"Mualliflik huquqi.*"
    ]
    for pattern in trash_patterns:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE | re.DOTALL)

    # 3. Stop-so'zlar orqali qatorlarni filtrlash
    stop_list = ['vvevya', 'kod podtverjdeniya', 'vvedite', 'parol', 'cookies', 'lotinchada', 'na russkom']
    lines = text.split('\n')
    cleaned_lines = []
    for line in lines:
        line = line.strip()
        if len(line) < 45: continue 
        if any(stop in line.lower() for stop in stop_list): continue
        cleaned_lines.append(line)
    
    final_text = " ".join(cleaned_lines).strip()
    return final_text[:950] if len(final_text) > 100 else None

# 5. MATNNI TUSHUNISH VA TARJIMA QILISH
def smart_translate(text):
    """Matn ruscha yoki inglizcha bo'lsa, o'zbekchaga o'giradi"""
    try:
        # Kirish matni tilini aniqlash va majburiy o'zbekchaga o'girish
        # Agar matnda o'zbekcha bo'lmagan belgilar ko'p bo'lsa tarjima qiladi
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
        
        # Rasm
        img_url = CHANNEL_LOGO if "TASS" in name else (soup.find("meta", property="og:image")['content'] if soup.find("meta", property="og:image") else None)

        for tag in soup(['script', 'style', 'nav', 'header', 'footer', 'aside', 'form', 'button']): tag.decompose()
        paras = soup.find_all('p')
        raw_text = "\n".join([p.get_text() for p in paras])
        
        cleaned = ultimate_clean(raw_text, name)
        return img_url, cleaned
    except: return None, None

# 6. ASOSIY ISLOXOT
def start_processing():
    while True:
        random.shuffle(SOURCES) # Manbalarni har aylanishda chalkashtirish
        for name, url in SOURCES:
            try:
                feed = feedparser.parse(url)
                # Faqat oxirgi 1 ta yangilikni olish (Xotira to'lmasligi va qaytarmasligi uchun)
                for entry in feed.entries[:1]:
                    if is_duplicate(entry.link): continue
                    
                    img_url, text = get_content(entry.link, name)
                    if not text: continue
                    
                    # MAJBURIY TARJIMA (Sarlavha va Matn uchun)
                    title_uz = smart_translate(entry.title)
                    text_uz = smart_translate(text)

                    # TASS sarlavhasini brendsiz qilish
                    if "TASS" in name: title_uz = title_uz.replace("TASS:", "").strip()

                    caption = f"📢 **KARNAY.UZB**\n\n**{title_uz}**\n\n{text_uz}...\n\n✅ @karnayuzb — Dunyo sizning qo'lingizda!"
                    
                    try:
                        if img_url:
                            bot.send_photo(CHANNEL_ID, img_url, caption=caption, parse_mode='Markdown')
                        else:
                            bot.send_message(CHANNEL_ID, caption, parse_mode='Markdown')
                        
                        log_link(entry.link)
                        time.sleep(40) # Spamsiz, navbat bilan
                    except: continue
            except: continue
        time.sleep(300)

if __name__ == "__main__":
    keep_alive()
    start_processing()
