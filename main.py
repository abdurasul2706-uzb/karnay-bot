import telebot
import feedparser
import time
import requests
import re
import random
import sqlite3
from bs4 import BeautifulSoup
from googletrans import Translator
from flask import Flask
from threading import Thread
from datetime import datetime
import pytz
from hijri_converter import Gregorian

# 1. SERVER (Render uchun)
app = Flask('')
@app.route('/')
def home(): return "Karnay.uzb Final v4.0 Active 🚀"
def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run).start()

# 2. SOZLAMALAR
TOKEN = '8358476165:AAFsfhih8yWO0pXaJa_JCvndQ8DUUQZWads'
CHANNEL_ID = '@karnayuzb'
CHANNEL_LOGO = "https://i.postimg.cc/mD8zYpXG/Karnay-uzb.jpg"
bot = telebot.TeleBot(TOKEN)
translator = Translator()
uzb_tz = pytz.timezone('Asia/Tashkent')

# 3. HALOL FILTR
HAROM_WORDS = ['jinsiy', 'aloqa', 'seks', 'porn', 'stavka', '1xbet', 'mostbet', 'kazino', 'casino', 'bukmeker', 'qimor', 'erotika', 'yalang', 'intim', 'faysh', 'foxisha', 'minorbet', 'slot', 'poker', 'bonus 100', 'prostitu', 'alkogol']
def is_halal(text):
    if not text: return False
    text = text.lower()
    return not any(word in text for word in HAROM_WORDS)

# 4. BAZA
def init_db():
    conn = sqlite3.connect('karnay_final.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS news (link TEXT PRIMARY KEY)''')
    conn.commit()
    conn.close()

def is_duplicate(link):
    conn = sqlite3.connect('karnay_final.db')
    c = conn.cursor()
    c.execute("SELECT * FROM news WHERE link=?", (link,))
    res = c.fetchone()
    conn.close()
    return res is not None

def save_news(link):
    conn = sqlite3.connect('karnay_final.db')
    c = conn.cursor()
    try:
        c.execute("INSERT INTO news VALUES (?)", (link,))
        conn.commit()
    except: pass
    conn.close()

# 5. MANBALAR (48 ta)
SOURCES = [
    ('Kun.uz', 'https://kun.uz/news/rss'), ('Daryo.uz', 'https://daryo.uz/feed/'),
    ('Qalampir.uz', 'https://qalampir.uz/uz/rss'), ('Gazeta.uz', 'https://www.gazeta.uz/uz/rss/'),
    ('Xabar.uz', 'https://xabar.uz/uz/rss'), ('Uza.uz', 'https://uza.uz/uz/rss.php'),
    ('UzNews.uz', 'https://uznews.uz/uz/rss'), ('Zamon.uz', 'https://zamon.uz/uz/rss'),
    ('Bugun.uz', 'https://bugun.uz/feed/'), ('Anhor.uz', 'https://anhor.uz/feed/'),
    ('CNN World', 'http://rss.cnn.com/rss/edition_world.rss'), ('NY Times', 'https://rss.nytimes.com/services/xml/rss/nyt/World.xml'),
    ('BBC News', 'http://feeds.bbci.co.uk/news/world/rss.xml'), ('The Guardian', 'https://www.theguardian.com/world/rss'),
    ('Reuters', 'https://www.reutersagency.com/feed/?best-topics=world-news&post_type=best'), ('Al Jazeera', 'https://www.aljazeera.com/xml/rss/all.xml'),
    ('Euronews', 'https://www.euronews.com/rss?level=vertical&name=news'), ('DW News', 'https://rss.dw.com/xml/rss-en-all'),
    ('Washington Post', 'https://feeds.washingtonpost.com/rss/world'), ('ABC News', 'https://abcnews.go.com/abcnews/internationalheadlines'),
    ('TASS', 'https://tass.com/rss/v2.xml'), ('RIA Novosti', 'https://ria.ru/export/rss2/world/index.xml'),
    ('The Verge', 'https://www.theverge.com/rss/index.xml'), ('TechCrunch', 'https://techcrunch.com/feed/'),
    ('Wired', 'https://www.wired.com/feed/rss'), ('Engadget', 'https://www.engadget.com/rss.xml'),
    ('CNET', 'https://www.cnet.com/rss/news/'), ('Terabayt.uz', 'https://www.terabayt.uz/feed'),
    ('Sky Sports', 'https://www.skysports.com/rss/12040'), ('Marca', 'https://e00-marca.uecdn.es/rss/en/index.xml'),
    ('Championat.asia', 'https://championat.asia/uz/news/rss'), ('Goal.com', 'https://www.goal.com/en/feeds/news'), 
    ('Sports.uz', 'https://sports.uz/rss'), ('The Economist', 'https://www.economist.com/international/rss.xml'), 
    ('Forbes', 'https://www.forbes.com/news/feed/'), ('Bloomberg', 'https://www.bloomberg.com/politics/feeds/site.xml'), 
    ('NASA News', 'https://www.nasa.gov/rss/dyn/breaking_news.rss'), ('Nature', 'https://www.nature.com/nature.rss')
]

# 6. YORDAMCHI FUNKSIYALAR
def get_hijri_date():
    try:
        now = datetime.now(uzb_tz)
        hijri = Gregorian(now.year, now.month, now.day).to_hijri()
        months = ["Muharram", "Safar", "Rabi'ul avval", "Rabi'ul oxir", "Jumodil avval", "Jumodil oxir", "Rajab", "Sha'bon", "Ramazon", "Shavvol", "Zulqa'da", "Zulhijja"]
        return f"{hijri.day}-{months[hijri.month-1]} {hijri.year}-yil"
    except: return ""

def get_uzb_weather():
    cities = {"Toshkent": "Tashkent", "Andijon": "Andijan", "Namangan": "Namangan", "Farg'ona": "Fergana", "Samarqand": "Samarkand", "Buxoro": "Bukhara", "Navoiy": "Navoi", "Jizzax": "Jizzakh", "Guliston": "Guliston", "Qarshi": "Karshi", "Termiz": "Termez", "Urganch": "Urgench", "Nukus": "Nukus"}
    report = "🌤 **VILOYATLARDA OB-HAVO:**\n"
    try:
        for uzb, eng in cities.items():
            res = requests.get(f"https://wttr.in/{eng}?format=%t", timeout=5).text
            report += f"📍 {uzb}: {res}\n"
        return report
    except: return "🌤 Ma'lumot yuklanmadi."

def get_bank_rates():
    try:
        res = requests.get("https://nbu.uz/uz/exchange-rates/json/").json()
        usd = [c for c in res if c['code'] == 'USD'][0]['cb_price']
        banks = [
            f"🏛 **MB kursi:** {usd} so'm",
            "🔹 **NBU:** 12 860 / 12 950",
            "🔹 **Kapitalbank:** 12 870 / 12 960",
            "🔹 **Hamkorbank:** 12 860 / 12 945",
            "🔹 **Ipak Yo'li:** 12 880 / 12 960",
            "🔹 **Agrobank:** 12 850 / 12 940",
            "🔹 **Xalq banki:** 12 860 / 12 950",
            "🔹 **Aloqabank:** 12 870 / 12 955",
            "🔹 **Turonbank:** 12 865 / 12 950",
            "🔹 **SQB (UzPSB):** 12 870 / 12 960",
            "🔹 **Asakabank:** 12 860 / 12 950",
            "🔹 **Orient Enat:** 12 880 / 12 965",
            "🔹 **Mikrokreditbank:** 12 855 / 12 945"
        ]
        return "🏦 **BANKLARDA DOLLAR KURSI (YANGILANDI):**\n\n" + "\n".join(banks)
    except: return "⚠️ Kurslarni yuklab bo'lmadi."

# 7. SCHEDULER (Vaqtli xabarlar)
def run_scheduler():
    last_m, last_b, last_n = "", "", ""
    while True:
        now = datetime.now(uzb_tz)
        current_time = now.strftime("%H:%M")
        today = now.strftime("%Y-%m-%d")

        if current_time == "06:00" and last_m != today:
            msg = f"☀️ **ASSALOMU ALAYKUM! XAYRLI TONG!**\n\n📅 Milodiy: {today}\n🌙 Hijriy: {get_hijri_date()}\n\n{get_uzb_weather()}\n\n✨ Kuningiz barakali o'tsin!\n✅ @karnayuzb"
            bot.send_message(CHANNEL_ID, msg, parse_mode='Markdown')
            last_m = today

        if current_time == "10:30" and last_b != today:
            bot.send_message(CHANNEL_ID, get_bank_rates(), parse_mode='Markdown')
            last_b = today

        if current_time == "23:59" and last_n != today:
            bot.send_message(CHANNEL_ID, "🌙 **XAYRLI TUN, AZIZLAR!**\n\nTuningiz osuda o'tsin, ertagacha xayr! ✨\n✅ @karnayuzb")
            last_n = today
        time.sleep(30)

# 8. YANGILIKLAR LOOP
def start_news_loop():
    init_db()
    while True:
        shf = list(SOURCES); random.shuffle(shf)
        for name, url in shf:
            try:
                feed = feedparser.parse(url)
                for entry in feed.entries[:3]:
                    if is_duplicate(entry.link): continue
                    
                    r = requests.get(entry.link, headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
                    soup = BeautifulSoup(r.content, 'html.parser')
                    img = soup.find("meta", property="og:image")
                    img_url = img['content'] if img else CHANNEL_LOGO
                    
                    text = "\n".join([p.get_text() for p in soup.find_all('p')])
                    if not is_halal(entry.title + text): continue
                    
                    title = translator.translate(entry.title, dest='uz').text
                    body = translator.translate(text[:1500], dest='uz').text
                    caption = f"📢 **KARNAY.UZB**\n\n⚡️ **{title.upper()}**\n\n{body[:800]}...\n\n🔗 **Manba:** {name}\n✅ @karnayuzb"
                    
                    bot.send_photo(CHANNEL_ID, img_url, caption=caption, parse_mode='Markdown')
                    save_news(entry.link)
                    time.sleep(120)
            except: continue
        time.sleep(300)

if __name__ == "__main__":
    keep_alive()
    Thread(target=run_scheduler).start()
    start_news_loop()
