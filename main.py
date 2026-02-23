import telebot
import feedparser
import time
import requests
import sqlite3
import random
import pytz
from bs4 import BeautifulSoup
from googletrans import Translator
from flask import Flask
from threading import Thread
from datetime import datetime, timedelta

# 1. SERVER & SOZLAMALAR
app = Flask('')
@app.route('/')
def home(): return "Karnay.uzb v11.0 - AI Translation & 48 Sources Active 🚀"
def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run).start()

TOKEN = '8358476165:AAFsfhih8yWO0pXaJa_JCvndQ8DUUQZWads'
CHANNEL_ID = '@karnayuzb'
CHANNEL_LOGO = "https://i.postimg.cc/mD8zYpXG/Karnay-uzb.jpg"
bot = telebot.TeleBot(TOKEN)
translator = Translator()
uzb_tz = pytz.timezone('Asia/Tashkent')
STANDARD_FINISH = "✨ Bilim va yangiliklar maskani — Biz bilan bo'lganingiz uchun rahmat!"

# 2. HALOL FILTR
HAROM_WORDS = ['jinsiy', 'aloqa', 'seks', 'porn', 'stavka', '1xbet', 'mostbet', 'kazino', 'casino', 'bukmeker', 'qimor', 'erotika', 'yalang', 'intim', 'faysh', 'foxisha', 'minorbet', 'slot', 'poker', 'bonus 100', 'prostitu', 'alkogol']

def is_halal(text):
    if not text: return False
    text = text.lower()
    return not any(word in text for word in HAROM_WORDS)

# 3. MATN TAYYORLASH (Limit: 980 belgi)
def get_max_caption(title, body, source_name):
    prefix = f"📢 **KARNAY.UZB**\n\n⚡️ **{title.upper()}**\n\n"
    suffix = f"\n\n🔗 **Manba:** {source_name}\n✅ @karnayuzb\n\n{STANDARD_FINISH}"
    allowed_body_len = 980 - len(prefix) - len(suffix)
    
    if len(body) > allowed_body_len:
        body = body[:allowed_body_len]
        last_punc = max(body.rfind('.'), body.rfind('!'), body.rfind('?'))
        if last_punc > (allowed_body_len * 0.7):
            body = body[:last_punc+1]
    return f"{prefix}{body}{suffix}"

# 4. MANBALAR (48 TA MANBA RO'YXATI)
SOURCES = [ 
    ('TASS', 'https://tass.com/rss/v2.xml'),
    ('Xabar.uz', 'https://xabar.uz/uz/rss'),
    ('UzNews.uz', 'https://uznews.uz/uz/rss'),
    ('Lifehacker', 'https://lifehacker.com/rss'), ('BigThink', 'https://bigthink.com/feed/'),
    ('Digital Trends', 'https://www.digitaltrends.com/feed/'),
    ('Podrobno.uz', 'https://podrobno.uz/rss/all/'),
    ('Bilasizmi', 'https://www.howstuffworks.com/rss.xml'), ('Faktlar', 'https://www.factslides.com/rss.xml'),
    ('BBC Uzbek', 'https://www.bbc.com/uzbek/index.xml'),
    ('Championat', 'https://www.championat.com/xml/rss/all.xml'),
    ('ESPN Soccer', 'https://www.espn.com/espn/rss/soccer/news'),
    ('Anhor.uz', 'https://anhor.uz/feed/'), ('CNN World', 'http://rss.cnn.com/rss/edition_world.rss'), 
    ('BBC News', 'http://feeds.bbci.co.uk/news/world/rss.xml'), 
    ('The Guardian', 'https://www.theguardian.com/world/rss'), ('Reuters', 'https://www.reutersagency.com/feed/?best-topics=world-news&post_type=best'), 
    ('Al Jazeera', 'https://www.aljazeera.com/xml/rss/all.xml'),
    ('DW News', 'https://rss.dw.com/xml/rss-en-all'),
    ('ABC News', 'https://abcnews.go.com/abcnews/internationalheadlines'), 
    ('RIA Novosti', 'https://ria.ru/export/rss2/world/index.xml'), 
    ('Championat.asia', 'https://championat.asia/uz/news/rss'), 
    ('The Economist', 'https://www.economist.com/international/rss.xml'),
    ('Bloomberg', 'https://www.bloomberg.com/politics/feeds/site.xml'), ('NASA News', 'https://www.nasa.gov/rss/dyn/breaking_news.rss'), 
    ('Nature', 'https://www.nature.com/nature.rss'), ('ScienceDaily', 'https://www.sciencedaily.com/rss/all.xml'),
    ('National Geographic', 'https://www.nationalgeographic.com/rss/index.html'),
]

# 5. BAZANI INITIALIZATSIYA QILISH
def init_db():
    conn = sqlite3.connect('karnay_final.db')
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS news (link TEXT PRIMARY KEY)')
    conn.commit()
    conn.close()

# 6. ASOSIY YANGILIKLAR LOOP
def start_news_loop():
    init_db()
    while True:
        shf = list(SOURCES)
        random.shuffle(shf)
        for name, url in shf:
            try:
                feed = feedparser.parse(url)
                for entry in feed.entries[:5]:
                    # Vaqtni tekshirish (oxirgi 24 soat)
                    pub_t = entry.get('published_parsed') or entry.get('updated_parsed')
                    if pub_t:
                        if datetime.now(pytz.utc) - datetime.fromtimestamp(time.mktime(pub_t), pytz.utc) > timedelta(hours=24):
                            continue
                    
                    # Bazada borligini tekshirish
                    conn = sqlite3.connect('karnay_final.db')
                    cur = conn.cursor()
                    cur.execute("SELECT * FROM news WHERE link=?", (entry.link,))
                    if cur.fetchone():
                        conn.close()
                        continue
                    
                    # Saytdan kontent va rasm olish
                    r = requests.get(entry.link, headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
                    soup = BeautifulSoup(r.content, 'html.parser')
                    
                    # Rasm qidirish
                    img = soup.find("meta", property="og:image")
                    img_url = img['content'] if img else CHANNEL_LOGO
                    
                    # Matn yig'ish
                    paragraphs = [p.get_text() for p in soup.find_all('p') if len(p.get_text()) > 40]
                    full_text = " ".join(paragraphs[:5]) # Dastlabki 5 ta paragraf
                    
                    if not is_halal(entry.title + full_text):
                        conn.close()
                        continue
                    
                    # Tarjima qilish (agar inglizcha bo'lsa)
                    try:
                        t_uz = translator.translate(entry.title, dest='uz').text
                        b_uz = translator.translate(full_text[:1000], dest='uz').text
                    except:
                        t_uz = entry.title
                        b_uz = full_text[:500]
                    
                    # Kanalga yuborish
                    bot.send_photo(CHANNEL_ID, img_url, caption=get_max_caption(t_uz, b_uz, name), parse_mode='Markdown')
                    
                    # Bazaga yozish
                    cur.execute("INSERT INTO news VALUES (?)", (entry.link,))
                    conn.commit()
                    conn.close()
                    time.sleep(180) # Har bir post orasida 3 daqiqa farq
            except Exception as e:
                print(f"Xato yuz berdi ({name}): {e}")
                continue
        time.sleep(300) # Manbalar ro'yxati tugagach 5 daqiqa kutish

if __name__ == "__main__":
    keep_alive()
    # Yangiliklar loopini asosiy oqimda ishga tushiramiz
    start_news_loop()
