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

# 1. SERVER
app = Flask('')
@app.route('/')
def home(): return "Karnay.uzb - 48 Sources Active 🚀"
def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run).start()

# 2. SOZLAMALAR
TOKEN = '8358476165:AAFsfhih8yWO0pXaJa_JCvndQ8DUUQZWads'
CHANNEL_ID = '@karnayuzb'
CHANNEL_LOGO = "https://i.postimg.cc/mD8zYpXG/Karnay-uzb.jpg"
bot = telebot.TeleBot(TOKEN)
translator = Translator()
uzb_tz = pytz.timezone('Asia/Tashkent')

# 3. BAZA
def init_db():
    conn = sqlite3.connect('karnay_max_sources.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS news (link TEXT PRIMARY KEY)''')
    conn.commit()
    conn.close()

def is_duplicate(link):
    conn = sqlite3.connect('karnay_max_sources.db')
    c = conn.cursor()
    c.execute("SELECT * FROM news WHERE link=?", (link,))
    res = c.fetchone()
    conn.close()
    return res is not None

def save_news(link):
    conn = sqlite3.connect('karnay_max_sources.db')
    c = conn.cursor()
    try:
        c.execute("INSERT INTO news VALUES (?)", (link,))
        conn.commit()
    except: pass
    conn.close()

# 4. VAQT FILTRI
def is_recent(entry):
    try:
        published_parsed = entry.get('published_parsed') or entry.get('updated_parsed')
        if not published_parsed: return True
        dt = datetime.fromtimestamp(time.mktime(published_parsed), pytz.utc)
        return (datetime.now(pytz.utc) - dt).total_seconds() < 86400
    except: return True

# 5. MANBALAR RO'YXATI (48 TA)
SOURCES = [
    # O'zbekiston (10 ta)
    ('Kun.uz', 'https://kun.uz/news/rss'), ('Daryo.uz', 'https://daryo.uz/feed/'),
    ('Qalampir.uz', 'https://qalampir.uz/uz/rss'), ('Gazeta.uz', 'https://www.gazeta.uz/uz/rss/'),
    ('Xabar.uz', 'https://xabar.uz/uz/rss'), ('Uza.uz', 'https://uza.uz/uz/rss.php'),
    ('UzNews.uz', 'https://uznews.uz/uz/rss'), ('Zamon.uz', 'https://zamon.uz/uz/rss'),
    ('Bugun.uz', 'https://bugun.uz/feed/'), ('Anhor.uz', 'https://anhor.uz/feed/'),
    
    # Jahon - Global (10 ta)
    ('CNN World', 'http://rss.cnn.com/rss/edition_world.rss'), ('NY Times', 'https://rss.nytimes.com/services/xml/rss/nyt/World.xml'),
    ('BBC News', 'http://feeds.bbci.co.uk/news/world/rss.xml'), ('The Guardian', 'https://www.theguardian.com/world/rss'),
    ('Reuters', 'https://www.reutersagency.com/feed/?best-topics=world-news&post_type=best'), ('Al Jazeera', 'https://www.aljazeera.com/xml/rss/all.xml'),
    ('Euronews', 'https://www.euronews.com/rss?level=vertical&name=news'), ('DW News', 'https://rss.dw.com/xml/rss-en-all'),
    ('Washington Post', 'https://feeds.washingtonpost.com/rss/world'), ('ABC News', 'https://abcnews.go.com/abcnews/internationalheadlines'),
    
    # Rossiya va MDH (5 ta)
    ('TASS', 'https://tass.com/rss/v2.xml'), ('RIA Novosti', 'https://ria.ru/export/rss2/world/index.xml'),
    ('Kommersant', 'https://www.kommersant.ru/RSS/news.xml'), ('RT News', 'https://www.rt.com/rss/news/'), ('Lenta.ru', 'https://lenta.ru/rss/news'),
    
    # Texnologiya (8 ta)
    ('The Verge', 'https://www.theverge.com/rss/index.xml'), ('TechCrunch', 'https://techcrunch.com/feed/'),
    ('Wired', 'https://www.wired.com/feed/rss'), ('Engadget', 'https://www.engadget.com/rss.xml'),
    ('CNET', 'https://www.cnet.com/rss/news/'), ('Gizmodo', 'https://gizmodo.com/rss'),
    ('Terabayt.uz', 'https://www.terabayt.uz/feed'), ('Mashable', 'https://mashable.com/feeds/rss/all'),
    
    # Sport (7 ta)
    ('ESPN', 'https://www.espn.com/espn/rss/soccer/news'), ('Sky Sports', 'https://www.skysports.com/rss/12040'),
    ('Marca', 'https://e00-marca.uecdn.es/rss/en/index.xml'), ('Championat.asia', 'https://championat.asia/uz/news/rss'),
    ('Eurosport', 'https://www.eurosport.com/rss.xml'), ('Goal.com', 'https://www.goal.com/en/feeds/news'), ('Sports.uz', 'https://sports.uz/rss'),
    
    # Iqtisodiyot va Siyosat (8 ta)
    ('The Economist', 'https://www.economist.com/international/rss.xml'), ('Forbes', 'https://www.forbes.com/news/feed/'),
    ('Bloomberg', 'https://www.bloomberg.com/politics/feeds/site.xml'), ('Financial Times', 'https://www.ft.com/?format=rss'),
    ('Politico', 'https://www.politico.com/rss/politicopicks.xml'), ('Foreign Affairs', 'https://www.foreignaffairs.com/rss.xml'),
    ('Axios', 'https://www.axios.com/feeds/feed.rss'), ('Harvard Business', 'https://hbr.org/rss/all.xml')
]

# 6. MATNNI TOZALASH VA TAYYORLASH
def ultimate_clean(text):
    if not text: return ""
    trash = [r"Введите почту.*", r"вышлем код.*", r"установить новый пароль.*", r"cookies.*", r"©.*", r"Tahririyat fikri.*"]
    for p in trash: text = re.sub(p, "", text, flags=re.IGNORECASE | re.DOTALL)
    paragraphs = [p.strip() for p in text.split('\n') if len(p.strip()) > 70]
    return "\n\n".join(paragraphs[:6])

def smart_translate(text):
    if not text: return ""
    try:
        return translator.translate(text, dest='uz').text
    except: return text

def get_data(url):
    try:
        r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=20)
        soup = BeautifulSoup(r.content, 'html.parser')
        img = soup.find("meta", property="og:image")
        img_url = img['content'] if img else CHANNEL_LOGO
        for tag in soup(['script', 'style', 'nav', 'header', 'footer', 'form', 'aside']): tag.decompose()
        paras = soup.find_all('p')
        raw_text = "\n".join([p.get_text() for p in paras])
        return img_url, ultimate_clean(raw_text)
    except: return CHANNEL_LOGO, ""

# 7. ASOSIY SIKL
def start_bot():
    init_db()
    while True:
        # Manbalarni har safar aralashtiramiz (Randomlik uchun)
        current_sources = list(SOURCES)
        random.shuffle(current_sources)
        
        for name, url in current_sources:
            try:
                feed = feedparser.parse(url)
                for entry in feed.entries[:3]:
                    if is_duplicate(entry.link) or not is_recent(entry):
                        continue
                    
                    img, text = get_data(entry.link)
                    if not text or len(text) < 150: continue
                    
                    title = smart_translate(entry.title)
                    body = smart_translate(text)
                    
                    # Sarlavhadagi "TASS:", "RIA:" kabi keraksiz qismlarni olib tashlash
                    title = re.sub(r'^[A-Z. ]+:', '', title).strip()

                    caption = f"📢 **KARNAY.UZB**\n\n⚡️ **{title.upper()}**\n\n{body}\n\n🔗 **Manba:** Karnay.uzb\n✅ @karnayuzb"

                    if len(caption) > 1024:
                        short_body = body[:750]
                        last_dot = short_body.rfind('.')
                        body = body[:last_dot + 1] if last_dot != -1 else body[:700]
                        caption = f"📢 **KARNAY.UZB**\n\n⚡️ **{title.upper()}**\n\n{body}\n\n🔗 **Manba:** Karnay.uzb\n✅ @karnayuzb"

                    try:
                        bot.send_photo(CHANNEL_ID, img, caption=caption, parse_mode='Markdown')
                        save_news(entry.link)
                        print(f"✅ {name} dan xabar olindi.")
                        time.sleep(120) # Har 2 daqiqada bitta post (kanal "spam" bo'lmasligi uchun)
                    except:
                        bot.send_photo(CHANNEL_ID, CHANNEL_LOGO, caption=caption, parse_mode='Markdown')
                        save_news(entry.link)
                        time.sleep(120)
            except: continue
        time.sleep(300)

if __name__ == "__main__":
    keep_alive()
    start_bot()
