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

# 1. SERVER SOZLAMALARI (Bot o'chib qolmasligi uchun)
app = Flask('')
@app.route('/')
def home(): return "Karnay.uzb Professional Media System is Online"
def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run).start()

# 2. KONFIGURATSIYA
TOKEN = '8358476165:AAFsfhih8yWO0pXaJa_JCvndQ8DUUQZWads'
CHANNEL_ID = '@karnayuzb'
CHANNEL_LOGO = "https://i.postimg.cc/mD8zYpXG/Karnay-uzb.jpg" 
bot = telebot.TeleBot(TOKEN)
translator = Translator()
uzb_tz = pytz.timezone('Asia/Tashkent')

# 3. MA'LUMOTLAR BAZASI (SQLite - Takrorlanmaslik uchun eng xavfsiz yo'l)
def init_db():
    conn = sqlite3.connect('news_history.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS news (link TEXT PRIMARY KEY)''')
    conn.commit()
    conn.close()

def is_duplicate(link):
    conn = sqlite3.connect('news_history.db')
    c = conn.cursor()
    c.execute("SELECT * FROM news WHERE link=?", (link,))
    result = c.fetchone()
    conn.close()
    return result is not None

def save_to_db(link):
    conn = sqlite3.connect('news_history.db')
    c = conn.cursor()
    try:
        c.execute("INSERT INTO news VALUES (?)", (link,))
        conn.commit()
    except: pass
    conn.close()

# 4. UNIVERSAL MANBALAR RO'YXATI (48 ta nufuzli manba - aralashtirilgan)
SOURCES = [
    ('Kun.uz', 'https://kun.uz/news/rss'), ('Daryo.uz', 'https://daryo.uz/feed/'),
    ('Qalampir.uz', 'https://qalampir.uz/uz/rss'), ('Gazeta.uz', 'https://www.gazeta.uz/uz/rss/'),
    ('Xabar.uz', 'https://xabar.uz/uz/rss'), ('Uza.uz', 'https://uza.uz/uz/rss.php'),
    ('UzNews.uz', 'https://uznews.uz/uz/rss'), ('Zamon.uz', 'https://zamon.uz/uz/rss'),
    ('Bugun.uz', 'https://bugun.uz/feed/'), ('Anhor.uz', 'https://anhor.uz/feed/'),
    ('CNN', 'http://rss.cnn.com/rss/edition_world.rss'), ('NY Times', 'https://rss.nytimes.com/services/xml/rss/nyt/World.xml'),
    ('Washington Post', 'https://feeds.washingtonpost.com/rss/world'), ('ABC News', 'https://abcnews.go.com/abcnews/internationalheadlines'),
    ('USA Today', 'https://www.usatoday.com/rss/world/'), ('BBC World', 'http://feeds.bbci.co.uk/news/world/rss.xml'),
    ('The Guardian', 'https://www.theguardian.com/world/rss'), ('Euronews', 'https://www.euronews.com/rss?level=vertical&name=news'),
    ('DW News', 'https://rss.dw.com/xml/rss-en-all'), ('Le Monde', 'https://www.lemonde.fr/en/world/rss_full.xml'),
    ('TASS', 'https://tass.com/rss/v2.xml'), ('RIA Novosti', 'https://ria.ru/export/rss2/world/index.xml'),
    ('Kommersant', 'https://www.kommersant.ru/RSS/news.xml'), ('Al Jazeera', 'https://www.aljazeera.com/xml/rss/all.xml'),
    ('Nikkei Asia', 'https://asia.nikkei.com/rss/feed/nar'), ('SCMP', 'https://www.scmp.com/rss/91/feed.xml'),
    ('CNA Asia', 'https://www.channelnewsasia.com/rssfeeds/8395981'), ('Japan Times', 'https://www.japantimes.co.jp/feed/'),
    ('ESPN', 'https://www.espn.com/espn/rss/soccer/news'), ('Sky Sports', 'https://www.skysports.com/rss/12040'),
    ('Marca', 'https://e00-marca.uecdn.es/rss/en/index.xml'), ('Eurosport', 'https://www.eurosport.com/rss.xml'),
    ('Championat Asia', 'https://championat.asia/uz/news/rss'), ('ArtNews', 'https://www.artnews.com/feed/'),
    ('The Art Newspaper', 'https://www.theartnewspaper.com/rss'), ('Rolling Stone', 'https://www.rollingstone.com/feed/'),
    ('Culture.ru', 'https://www.culture.ru/rss'), ('Afisha.uz', 'https://www.afisha.uz/uz/rss/'),
    ('The Verge', 'https://www.theverge.com/rss/index.xml'), ('Wired', 'https://www.wired.com/feed/rss'),
    ('TechCrunch', 'https://techcrunch.com/feed/'), ('CNET', 'https://www.cnet.com/rss/news/'),
    ('Gizmodo', 'https://gizmodo.com/rss'), ('Politico', 'https://www.politico.com/rss/politicopicks.xml'),
    ('Foreign Affairs', 'https://www.foreignaffairs.com/rss.xml'), ('The Economist', 'https://www.economist.com/international/rss.xml'),
    ('Reuters Politics', 'https://www.reutersagency.com/feed/?best-topics=politics&post_type=best'), ('Axios', 'https://www.axios.com/feeds/feed.rss')
]
random.shuffle(SOURCES)

# 5. MATNNI TOZALASH VA TARJIMA
def clean_text(text, name):
    if not text: return None
    # Texnik axlatlarni tozalash
    text = re.sub(r'^[A-Z\s,]+.*?(\d{1,2}|TASS|RIA|RIA NOVOSTI)\s*.*?/', '', text, flags=re.IGNORECASE)
    trash = [r"Если вы нашли ошибку.*", r"Ctrl\+Enter.*", r"Выделиte фрагмент.*", r"©.*", r"Copyright.*", r"All rights reserved.*", r"Подпишитесь.*"]
    for p in trash: text = re.sub(p, "", text, flags=re.IGNORECASE | re.DOTALL)
    
    lines = [l.strip() for l in text.split('\n') if len(l.strip()) > 55]
    stop_words = ['vvedite', 'kod podtverjdeniya', 'cookies', 'nomer telefona', 'parol']
    final_lines = [l for l in lines if not any(s in l.lower() for s in stop_list)]
    
    res_text = " ".join(final_lines).strip()
    return res_text[:950] if len(res_text) > 100 else None

def translate_to_uz(text):
    try:
        if not text: return ""
        detect = translator.detect(text).lang
        if detect != 'uz':
            return translator.translate(text, dest='uz').text
        return text
    except: return text

# 6. KONTENTNI YUKLASH
def fetch_content(url, name):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        r = requests.get(url, headers=headers, timeout=20)
        soup = BeautifulSoup(r.content, 'html.parser')
        
        # Rasm topish
        img_tag = soup.find("meta", property="og:image")
        img_url = img_tag['content'] if img_tag else CHANNEL_LOGO
        
        # Matn topish
        for tag in soup(['script', 'style', 'nav', 'header', 'footer', 'form', 'aside']): tag.decompose()
        paras = soup.find_all('p')
        full_text = clean_text("\n".join([p.get_text() for p in paras]), name)
        
        return img_url, full_text
    except: return CHANNEL_LOGO, None

# 7. TABRIKLAR TIZIMI
def send_greetings():
    now = datetime.now(uzb_tz)
    hm = now.strftime("%H:%M")
    
    if hm == "06:00":
        msg = "☀️ **Xayrli tong, aziz Karnay.uzb obunachilari!**\n\nYangi kun muborak bo'lsin. Bugungi rejalaringizda omad va zafarlar sizni tark etmasin. Ishlaringizda unum va baraka tilaymiz! 😊"
        bot.send_message(CHANNEL_ID, msg, parse_mode='Markdown')
        time.sleep(65)
    elif hm == "23:59":
        msg = "🌙 **Xayrli tun, Karnay.uzb jamoasi!**\n\nBugungi kun ham o'z nihoyasiga yetdi. Tunningiz osuda o'tsin, ertangi kunga yangi kuch va shijoat bilan uyg'onish nasib qilsin. Yaxshi dam oling! ✨"
        bot.send_message(CHANNEL_ID, msg, parse_mode='Markdown')
        time.sleep(65)

# 8. ASOSIY SIKL
def start_bot():
    init_db()
    while True:
        random.shuffle(SOURCES)
        for name, url in SOURCES:
            send_greetings()
            try:
                feed = feedparser.parse(url)
                # Faqat oxirgi 3 ta xabarni tekshiramiz (eng so'nggi bo'lishi uchun)
                for entry in feed.entries[:3]:
                    if is_duplicate(entry.link): continue
                    
                    img, text = fetch_content(entry.link, name)
                    if not text: continue
                    
                    # Majburiy tarjima
                    title_uz = translate_to_uz(entry.title)
                    text_uz = translate_to_uz(text)
                    
                    # TASS/RIA nomini sarlavhadan tozalash
                    title_uz = re.sub(r'^(TASS|RIA|RIA NOVOSTI):', '', title_uz, flags=re.IGNORECASE).strip()

                    caption = f"📢 **KARNAY.UZB**\n\n**{title_uz}**\n\n{text_uz}...\n\n✅ @karnayuzb — Dunyo sizning qo'lingizda!"
                    
                    try:
                        bot.send_photo(CHANNEL_ID, img, caption=caption, parse_mode='Markdown')
                        save_to_db(entry.link)
                        time.sleep(45) # Spamsiz yuborish
                    except:
                        # Rasmda xatolik bo'lsa, logotip bilan matnni o'zini yuborish
                        bot.send_photo(CHANNEL_ID, CHANNEL_LOGO, caption=caption, parse_mode='Markdown')
                        save_to_db(entry.link)
                        time.sleep(45)
            except: continue
        time.sleep(180)

if __name__ == "__main__":
    keep_alive()
    start_bot()
