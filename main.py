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
    try:
        with open(DB_FILE, "r") as f:
            return link in f.read()
    except: return False

def save_sent(link):
    try:
        with open(DB_FILE, "a") as f:
            f.write(link + "\n")
    except: pass

# 3. MANBALAR (Siz so'ragan barcha yo'nalishlar bo'yicha)
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
    ('TASS News', 'https://tass.com/rss/v2.xml'),
    ('TechCrunch', 'https://techcrunch.com/feed/'), # Texnika
    ('ArtNews', 'https://www.artnews.com/feed/') # San'at
]

# 4. TOZALASH VA FILTRLASH
def clean_text(text):
    if not text: return ""
    # "Xunuk" va texnik jumlalar filtri
    blacklist = [
        'cookies', 'rozilik', 'lotinchada', 'na russkom', '©', 'tahririyat', 
        'muallif', 'reklama', 'facebook', 'instagram', 'telegram', 
        'e-pochtangiz', 'ruxsatingiz yo‘q', 'xavfsizlik nuqtai'
    ]
    lines = [line.strip() for line in text.split('\n') if len(line.strip()) > 55]
    cleaned = " ".join([l for l in lines if not any(bad in l.lower() for bad in blacklist)])
    
    # Ortiqcha bo'shliqlarni yo'qotish va bitta yaxlit matn qilish
    cleaned = re.sub(r'\s+', ' ', cleaned)
    return cleaned.strip()

def get_full_article(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        res = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(res.content, 'html.parser')
        
        # Rasm olish
        img = soup.find("meta", property="og:image")
        img_url = img['content'] if img else None
        
        # Matn qismlarini tozalash
        for tag in soup(['script', 'style', 'nav', 'header', 'footer', 'aside', 'form']): 
            tag.decompose()
            
        paras = soup.find_all('p')
        text = clean_text("\n".join([p.get_text() for p in paras]))
        
        # Agar matn juda qisqa bo'lsa (yoki topilmasa), bo'sh qaytaradi
        if len(text) < 150:
            return img_url, None
            
        return img_url, text[:1000] # Telegram caption limiti uchun
    except:
        return None, None

# 5. SALOMLASHISH TIZIMI
def check_greetings():
    try:
        tz = pytz.timezone('Asia/Tashkent')
        now = datetime.now(tz)
        hm = now.strftime("%H:%M")
        
        if hm == "06:00":
            bot.send_message(CHANNEL_ID, f"☀️ **Xayrli tong!**\n\n📅 Bugun: {now.strftime('%d-%m-%Y')}\nKuningiz xayrli va barokatli o'tsin! 😊", parse_mode='Markdown')
            time.sleep(60)
        elif hm == "23:59":
            bot.send_message(CHANNEL_ID, "🌙 **Xayrli tun.**\nYaxshi dam oling! ✨", parse_mode='Markdown')
            time.sleep(60)
    except: pass

# 6. ASOSIY ISHCHI
def start_bot():
    while True:
        random.shuffle(SOURCES)
        for name, url in SOURCES:
            check_greetings()
            try:
                feed = feedparser.parse(url)
                for entry in feed.entries[:2]:
                    if is_sent(entry.link): continue
                    
                    img_url, text = get_full_article(entry.link)
                    
                    # AGAR MATN TOPILMASA, POSTNI TASHLAMAYMIZ!
                    if not text:
                        continue
                    
                    title = entry.title
                    # Tarjima (Chet el manbalari)
                    if any(word in url.lower() for word in ['reuters', 'nytimes', 'ap', 'aljazeera', 'washingtonpost', 'dw', 'tass', 'techcrunch', 'artnews']):
                        try:
                            title = translator.translate(title, dest='uz').text
                            text = translator.translate(text, dest='uz').text
                        except: pass

                    caption = f"📢 **{name.upper()}**\n\n**{title}**\n\n{text}...\n\n✅ @karnayuzb — Eng so'nggi xabarlar"
                    
                    try:
                        if img_url:
                            bot.send_photo(CHANNEL_ID, img_url, caption=caption, parse_mode='Markdown')
                        else:
                            bot.send_message(CHANNEL_ID, caption, parse_mode='Markdown')
                        
                        save_sent(entry.link)
                        time.sleep(25) # Kanalda juda tiqilib ketmasligi uchun
                    except: continue
            except: continue
        time.sleep(180) # Har 3 daqiqada yangi aylanish

if __name__ == "__main__":
    keep_alive()
    start_bot()
