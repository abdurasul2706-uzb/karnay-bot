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
def home(): return "Karnay.uzb - No Trash System Active 🚀"
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
    conn = sqlite3.connect('karnay_pro_v3.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS news (link TEXT PRIMARY KEY)''')
    conn.commit()
    conn.close()

def is_duplicate(link):
    conn = sqlite3.connect('karnay_pro_v3.db')
    c = conn.cursor()
    c.execute("SELECT * FROM news WHERE link=?", (link,))
    res = c.fetchone()
    conn.close()
    return res is not None

def save_news(link):
    conn = sqlite3.connect('karnay_pro_v3.db')
    c = conn.cursor()
    try:
        c.execute("INSERT INTO news VALUES (?)", (link,))
        conn.commit()
    except: pass
    conn.close()

# 4. MANBALAR (48 ta aralashtirilgan)
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

# 5. KUCHAYTIRILGAN TOZALASH FILTRI
def clean_and_format(text):
    if not text: return ""
    
    # Texnik axlatlar ro'yxati
    trash_patterns = [
        r"Введите почту или номер телефона.*", 
        r"вышлем код подтверждения.*",
        r"установить новый пароль.*",
        r"Если вы нашли ошибку.*", 
        r"Ctrl\+Enter.*", 
        r"cookies.*", 
        r"Lotincha", 
        r"Na russkom", 
        r"Biz sayt.*", 
        r"©.*",
        r"Все права защищены.*",
        r"Подпишитесь на наши.*",
        r"Зарегистрируйтесь.*"
    ]
    
    for pattern in trash_patterns:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE | re.DOTALL)
    
    paragraphs = [p.strip() for p in text.split('\n') if len(p.strip()) > 60]
    
    # Mazmuniy filtr (Parol va Kod so'zlari bor qatorlarni o'chirish)
    final_paragraphs = []
    for p in paragraphs:
        if any(w in p.lower() for w in ['вышлем код', 'пароль', 'password', 'confirm code']):
            continue
        final_paragraphs.append(p)
        
    return "\n\n".join(final_paragraphs[:6])

def smart_translate(text):
    if not text: return ""
    try:
        detect = translator.detect(text).lang
        if detect != 'uz':
            return translator.translate(text, dest='uz').text
        return text
    except: return text

def get_content(url):
    try:
        r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=20)
        soup = BeautifulSoup(r.content, 'html.parser')
        img = soup.find("meta", property="og:image")
        img_url = img['content'] if img else CHANNEL_LOGO
        for tag in soup(['script', 'style', 'nav', 'header', 'footer', 'aside', 'form']): tag.decompose()
        paras = soup.find_all('p')
        raw_text = "\n".join([p.get_text() for p in paras])
        return img_url, clean_and_format(raw_text)
    except: return CHANNEL_LOGO, None

# 6. TABRIKLAR
def send_greetings():
    now = datetime.now(uzb_tz).strftime("%H:%M")
    if now == "06:00":
        bot.send_message(CHANNEL_ID, "☀️ **Xayrli tong, aziz Karnay.uzb obunachilari!**\n\nBugungi kuningiz unumli va yangiliklarga boy bo'lsin! 😊🚀", parse_mode='Markdown')
        time.sleep(65)
    elif now == "23:59":
        bot.send_message(CHANNEL_ID, "🌙 **Tuningiz osuda o'tsin!**\n\nBiz bilan bo'lganingiz uchun rahmat. Ertaga uchrashguncha! ✨", parse_mode='Markdown')
        time.sleep(65)

# 7. ASOSIY SIKL
def start_bot():
    init_db()
    while True:
        random.shuffle(SOURCES)
        for name, url in SOURCES:
            send_greetings()
            try:
                feed = feedparser.parse(url)
                for entry in feed.entries[:3]:
                    if is_duplicate(entry.link): continue
                    
                    img, text = get_content(entry.link)
                    if not text or len(text) < 150: continue
                    
                    title = smart_translate(entry.title)
                    body = smart_translate(text)
                    title = re.sub(r'^(TASS|RIA|RIA NOVOSTI|KUN\.UZ):', '', title, flags=re.IGNORECASE).strip()

                    # Matnni chiroyli yakunlash (Gap o'rtasida qolmasligi uchun)
                    caption_base = f"📢 **KARNAY.UZB**\n\n⚡️ **{title.upper()}**\n\n{body}\n\n🔗 **Manba:** Karnay.uzb\n✅ @karnayuzb"
                    
                    if len(caption_base) > 1024:
                        short_body = body[:800]
                        last_dot = short_body.rfind('.')
                        body = body[:last_dot + 1] if last_dot != -1 else body[:750]
                        caption_base = f"📢 **KARNAY.UZB**\n\n⚡️ **{title.upper()}**\n\n{body}\n\n🔗 **Manba:** Karnay.uzb\n✅ @karnayuzb"

                    try:
                        bot.send_photo(CHANNEL_ID, img, caption=caption_base, parse_mode='Markdown')
                        save_news(entry.link)
                        time.sleep(50)
                    except:
                        bot.send_photo(CHANNEL_ID, CHANNEL_LOGO, caption=caption_base, parse_mode='Markdown')
                        save_news(entry.link)
                        time.sleep(50)
            except: continue
        time.sleep(200)

if __name__ == "__main__":
    keep_alive()
    start_bot()
