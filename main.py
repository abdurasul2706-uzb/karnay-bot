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
def home(): return "Karnay.uzb Professional Bot"
def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run).start()

# 2. SOZLAMALAR
TOKEN = '8358476165:AAFsfhih8yWO0pXaJa_JCvndQ8DUUQZWads'
CHANNEL_ID = '@karnayuzb'
# O'zingizning logotipingiz (TASS uchun majburiy rasm)
CHANNEL_LOGO = "https://i.postimg.cc/mD8zYpXG/Karnay-uzb.jpg" 

bot = telebot.TeleBot(TOKEN)
translator = Translator()

# XOTIRA - Faylga yozish (Takrorlanmaslik uchun)
DB_FILE = "news_db.txt"
if not os.path.exists(DB_FILE):
    with open(DB_FILE, "w") as f: pass

def is_published(link):
    with open(DB_FILE, "r") as f:
        return link in f.read()

def save_news(link):
    with open(DB_FILE, "a") as f:
        f.write(link + "\n")

# 3. MANBALAR (Yana O'zbekiston manbalari kuchaytirildi)
SOURCES = [
    ('Kun.uz', 'https://kun.uz/news/rss'),
    ('Daryo.uz', 'https://daryo.uz/feed/'),
    ('Qalampir.uz', 'https://qalampir.uz/uz/rss'),
    ('Gazeta.uz', 'https://www.gazeta.uz/uz/rss/'),
    ('Xabar.uz', 'https://xabar.uz/uz/rss'),
    ('Uza.uz', 'https://uza.uz/uz/rss.php'),
    ('UzNews.uz', 'https://uznews.uz/uz/rss'),
    ('Zamon.uz', 'https://zamon.uz/uz/rss'),
    ('TASS News', 'https://tass.com/rss/v2.xml'), # TASS faqat jahon xabarlari uchun
    ('Reuters', 'https://www.reutersagency.com/feed/?best-topics=world-news&post_type=best'),
    ('BBC Uzbek', 'https://www.bbc.com/uzbek/index.xml')
]

# 4. TASS VA BOSHQA MATNLARNI TOZALASH (RADIKAL USUL)
def extreme_clean(text, name):
    if not text: return None
    
    # 1. TASS xususiy tozalash
    if "TASS" in name:
        # MOSKVA, sana va /TASS/ formatlarini butunlay o'chirish (RegEx)
        text = re.sub(r'^[A-Z\s]+,.*?\d{1,2}.*?/TASS/\.', '', text, flags=re.IGNORECASE)
        text = re.sub(r'^[A-Z\s]+,.*?\d{1,2}\s[a-z]+\.', '', text, flags=re.IGNORECASE)
        # Qolgan "MOSKVA", "TASS" so'zlarini butunlay o'chirish
        text = text.replace("MOSKVA", "").replace("TASS", "").replace("/ /", "").strip()

    # 2. Umumiy keraksiz so'zlar
    blacklist = ['cookies', 'rozilik', 'yaxshilash', 'lotinchada', 'na russkom', '©', 'tahririyat']
    lines = text.split('\n')
    cleaned_lines = []
    for line in lines:
        line = line.strip()
        if len(line) < 65: continue
        if any(bad in line.lower() for bad in blacklist): continue
        cleaned_lines.append(line)
    
    final = " ".join(cleaned_lines)
    return final[:950] if len(final) > 150 else None

def get_content(url, name):
    try:
        # TASS uchun har doim o'z logotipingizni ishlatamiz (shartingiz bo'yicha)
        if "TASS" in name:
            img_url = CHANNEL_LOGO
        else:
            # Boshqa saytlardan rasmni "og:image" orqali olish
            res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
            soup = BeautifulSoup(res.content, 'html.parser')
            img_tag = soup.find("meta", property="og:image")
            img_url = img_tag['content'] if img_tag else None

        # Matn olish
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
        soup = BeautifulSoup(res.content, 'html.parser')
        for s in soup(['script', 'style', 'nav', 'header', 'footer']): s.decompose()
        paras = soup.find_all('p')
        text = extreme_clean("\n".join([p.get_text() for p in paras]), name)
        
        return img_url, text
    except: return None, None

# 5. ASOSIY ISH
def start_worker():
    while True:
        random.shuffle(SOURCES)
        for name, url in SOURCES:
            try:
                feed = feedparser.parse(url)
                # Faqat eng yangi 2 ta yangilikni tekshiramiz (Eski xabarlar chiqib ketmasligi uchun)
                for entry in feed.entries[:2]:
                    if is_published(entry.link): continue
                    
                    # TASS uchun o'tgan yilgi xabarlarni sana bo'yicha cheklash
                    if "TASS" in name:
                        # Agar xabar sanasi hozirgi kundan juda uzoq bo'lsa - tashlamaymiz
                        published_date = getattr(entry, 'published_parsed', None)
                        if published_date:
                            if datetime.now().year > published_date.tm_year: continue

                    img_url, text = get_content(entry.link, name)
                    if not text: continue
                    
                    title = entry.title
                    # Tarjima (Rus/Ingliz)
                    if any(x in url.lower() for x in ['tass', 'reuters', 'bbc']):
                        try:
                            title = translator.translate(title, dest='uz').text
                            text = translator.translate(text, dest='uz').text
                        except: pass

                    # TASS sarlavhasini tozalash
                    if "TASS" in name:
                        title = title.replace("TASS:", "").strip()

                    caption = f"📢 **KARNAY.UZB**\n\n**{title}**\n\n{text}...\n\n✅ @karnayuzb — Dunyo sizning qo'lingizda!"
                    
                    try:
                        # Rasm bo'lsa rasm bilan, bo'lmasa matnning o'zi
                        if img_url:
                            bot.send_photo(CHANNEL_ID, img_url, caption=caption, parse_mode='Markdown')
                        else:
                            bot.send_message(CHANNEL_ID, caption, parse_mode='Markdown')
                        
                        save_news(entry.link)
                        time.sleep(35)
                    except: continue
            except: continue
        time.sleep(300)

if __name__ == "__main__":
    keep_alive()
    start_worker()
