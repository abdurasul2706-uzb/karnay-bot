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

# 1. SERVER (Render o'chirib yubormasligi uchun)
app = Flask('')
@app.route('/')
def home(): return "Karnay.uzb Professional Media System is Live 🚀"
def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run).start()

# 2. SOZLAMALAR
TOKEN = '8358476165:AAFsfhih8yWO0pXaJa_JCvndQ8DUUQZWads'
CHANNEL_ID = '@karnayuzb'
CHANNEL_LOGO = "https://i.postimg.cc/mD8zYpXG/Karnay-uzb.jpg" # O'zingiz tashlagan logotip linki
bot = telebot.TeleBot(TOKEN)
translator = Translator()
uzb_tz = pytz.timezone('Asia/Tashkent')

# 3. MA'LUMOTLAR BAZASI (SQLite - Takrorlanmaslik uchun)
def init_db():
    conn = sqlite3.connect('karnay_news.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS news (link TEXT PRIMARY KEY)''')
    conn.commit()
    conn.close()

def is_duplicate(link):
    conn = sqlite3.connect('karnay_news.db')
    c = conn.cursor()
    c.execute("SELECT * FROM news WHERE link=?", (link,))
    res = c.fetchone()
    conn.close()
    return res is not None

def save_news(link):
    conn = sqlite3.connect('karnay_news.db')
    c = conn.cursor()
    try:
        c.execute("INSERT INTO news VALUES (?)", (link,))
        conn.commit()
    except: pass
    conn.close()

# 4. MANBALAR (Siz so'ragan barcha 48 ta nufuzli manba)
SOURCES = [
    # O'zbekiston (10 ta)
    ('Kun.uz', 'https://kun.uz/news/rss'), ('Daryo.uz', 'https://daryo.uz/feed/'),
    ('Qalampir.uz', 'https://qalampir.uz/uz/rss'), ('Gazeta.uz', 'https://www.gazeta.uz/uz/rss/'),
    ('Xabar.uz', 'https://xabar.uz/uz/rss'), ('Uza.uz', 'https://uza.uz/uz/rss.php'),
    ('UzNews.uz', 'https://uznews.uz/uz/rss'), ('Zamon.uz', 'https://zamon.uz/uz/rss'),
    ('Bugun.uz', 'https://bugun.uz/feed/'), ('Anhor.uz', 'https://anhor.uz/feed/'),
    # Amerika (5 ta)
    ('CNN', 'http://rss.cnn.com/rss/edition_world.rss'), ('NY Times', 'https://rss.nytimes.com/services/xml/rss/nyt/World.xml'),
    ('Washington Post', 'https://feeds.washingtonpost.com/rss/world'), ('ABC News', 'https://abcnews.go.com/abcnews/internationalheadlines'),
    ('USA Today', 'https://www.usatoday.com/rss/world/'),
    # Yevropa (5 ta)
    ('BBC News', 'http://feeds.bbci.co.uk/news/world/rss.xml'), ('The Guardian', 'https://www.theguardian.com/world/rss'),
    ('Euronews', 'https://www.euronews.com/rss?level=vertical&name=news'), ('DW', 'https://rss.dw.com/xml/rss-en-all'),
    ('Le Monde', 'https://www.lemonde.fr/en/world/rss_full.xml'),
    # Rossiya (3 ta)
    ('TASS', 'https://tass.com/rss/v2.xml'), ('RIA Novosti', 'https://ria.ru/export/rss2/world/index.xml'),
    ('Kommersant', 'https://www.kommersant.ru/RSS/news.xml'),
    # Osiyo (5 ta)
    ('Al Jazeera', 'https://www.aljazeera.com/xml/rss/all.xml'), ('Nikkei Asia', 'https://asia.nikkei.com/rss/feed/nar'),
    ('SCMP', 'https://www.scmp.com/rss/91/feed.xml'), ('CNA', 'https://www.channelnewsasia.com/rssfeeds/8395981'),
    ('Japan Times', 'https://www.japantimes.co.jp/feed/'),
    # Sport (5 ta)
    ('ESPN', 'https://www.espn.com/espn/rss/soccer/news'), ('Sky Sports', 'https://www.skysports.com/rss/12040'),
    ('Marca', 'https://e00-marca.uecdn.es/rss/en/index.xml'), ('Eurosport', 'https://www.eurosport.com/rss.xml'),
    ('Championat Asia', 'https://championat.asia/uz/news/rss'),
    # San'at/Madaniyat (5 ta)
    ('ArtNews', 'https://www.artnews.com/feed/'), ('The Art Newspaper', 'https://www.theartnewspaper.com/rss'),
    ('Culture.ru', 'https://www.culture.ru/rss'), ('Rolling Stone', 'https://www.rollingstone.com/feed/'),
    ('Afisha.uz', 'https://www.afisha.uz/uz/rss/'),
    # Texnika (5 ta)
    ('The Verge', 'https://www.theverge.com/rss/index.xml'), ('Wired', 'https://www.wired.com/feed/rss'),
    ('CNET', 'https://www.cnet.com/rss/news/'), ('Gizmodo', 'https://gizmodo.com/rss'),
    ('Terabayt.uz', 'https://www.terabayt.uz/feed'),
    # Siyosat (5 ta)
    ('Politico', 'https://www.politico.com/rss/politicopicks.xml'), ('Foreign Affairs', 'https://www.foreignaffairs.com/rss.xml'),
    ('The Economist', 'https://www.economist.com/international/rss.xml'), ('Axios', 'https://www.axios.com/feeds/feed.rss'),
    ('Reuters Politics', 'https://www.reutersagency.com/feed/?best-topics=politics&post_type=best')
]

# 5. TOZALASH VA TARJIMA FUNKSIYASI
def ultimate_clean(text, name):
    if not text: return None
    # 1. Boshidagi MOSKVA/Sana larni tozalash
    text = re.sub(r'^[A-Z\s,]+.*?(\d{1,2}|TASS|RIA)\s*.*?/', '', text, flags=re.IGNORECASE)
    # 2. Skrinshotingizdagi "Cookies", "Lotincha", "Na russkom" kabi axlatlarni tozalash
    trash_words = [
        r"Biz sayt ishlashini yaxshilash.*", r"cookies-dan foydalanishga rozilik.*",
        r"Lotincha", r"Kecha, \d{2}:\d{2}", r"Жамият", r"Сиёсат", r"Na russkom yazyke",
        r"Если вы нашли ошибку.*", r"Ctrl\+Enter.*", r"Barcha huquqlar himoyalangan.*", r"©.*"
    ]
    for pattern in trash_words:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE | re.DOTALL)
    
    lines = [l.strip() for l in text.split('\n') if len(l.strip()) > 50]
    result = " ".join(lines).strip()
    return result[:950] if len(result) > 100 else None

def translate_msg(text):
    try:
        if not text: return ""
        if translator.detect(text).lang != 'uz':
            return translator.translate(text, dest='uz').text
        return text
    except: return text

def get_content(url, name):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        r = requests.get(url, headers=headers, timeout=20)
        soup = BeautifulSoup(r.content, 'html.parser')
        
        # Rasm topish yoki logotip qo'yish
        img_tag = soup.find("meta", property="og:image")
        img_url = img_tag['content'] if img_tag else CHANNEL_LOGO
        
        # Matnni yig'ish
        for tag in soup(['script', 'style', 'nav', 'header', 'footer', 'form', 'aside']): tag.decompose()
        paras = soup.find_all('p')
        raw_text = "\n".join([p.get_text() for p in paras])
        cleaned = ultimate_clean(raw_text, name)
        
        return img_url, cleaned
    except: return CHANNEL_LOGO, None

# 6. TABRIKLAR TIZIMI
def daily_greetings():
    now = datetime.now(uzb_tz).strftime("%H:%M")
    if now == "06:00":
        bot.send_message(CHANNEL_ID, "☀️ **Xayrli tong, aziz Karnay.uzb obunachilari!**\n\nYangi kun muborak bo'lsin. Bugun omad sizga yor bo'lishini, barcha ezgu ishlaringizda unum bo'lishini tilab qolamiz! 🚀", parse_mode='Markdown')
        time.sleep(61)
    elif now == "23:59":
        bot.send_message(CHANNEL_ID, "🌙 **Xayrli tun!**\n\nKuningiz mazmunli o'tgan bo'lsa xursandmiz. Yaxshi dam oling, ertangi kun yangi zafarlar kuni bo'lsin! ✨", parse_mode='Markdown')
        time.sleep(61)

# 7. ASOSIY ISHCHI
def start_bot():
    init_db()
    while True:
        random.shuffle(SOURCES)
        for name, url in SOURCES:
            daily_greetings()
            try:
                feed = feedparser.parse(url)
                # Faqat eng yangi 3 tasini tekshiramiz
                for entry in feed.entries[:3]:
                    if is_duplicate(entry.link): continue
                    
                    img, text = get_content(entry.link, name)
                    if not text: continue
                    
                    title = translate_msg(entry.title)
                    desc = translate_msg(text)
                    
                    # Sarlavhadagi keraksiz nomlarni tozalash
                    title = re.sub(r'^(TASS|RIA|RIA NOVOSTI|KUN\.UZ):', '', title, flags=re.IGNORECASE).strip()

                    caption = f"📢 **KARNAY.UZB**\n\n**{title}**\n\n{desc}...\n\n✅ @karnayuzb — Dunyo sizning qo'lingizda!"
                    
                    try:
                        bot.send_photo(CHANNEL_ID, img, caption=caption, parse_mode='Markdown')
                        save_news(entry.link)
                        time.sleep(50) 
                    except:
                        bot.send_photo(CHANNEL_ID, CHANNEL_LOGO, caption=caption, parse_mode='Markdown')
                        save_news(entry.link)
                        time.sleep(50)
            except: continue
        time.sleep(180)

if __name__ == "__main__":
    keep_alive()
    start_bot()
