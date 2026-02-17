import telebot
import feedparser
import time
import requests
import random
import sqlite3
from bs4 import BeautifulSoup
from googletrans import Translator
from flask import Flask
from threading import Thread
from datetime import datetime
import pytz

# 1. SERVER (Render 24/7)
app = Flask('')
@app.route('/')
def home(): return "Karnay.uzb v6.0 System is Online 🚀"
def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run).start()

# 2. SOZLAMALAR
TOKEN = '8358476165:AAFsfhih8yWO0pXaJa_JCvndQ8DUUQZWads'
CHANNEL_ID = '@karnayuzb'
CHANNEL_LOGO = "https://i.postimg.cc/mD8zYpXG/Karnay-uzb.jpg"
bot = telebot.TeleBot(TOKEN)
translator = Translator()
uzb_tz = pytz.timezone('Asia/Tashkent')

# 3. HALOL FILTR (Qat'iy nazorat)
HAROM_WORDS = ['jinsiy', 'aloqa', 'seks', 'porn', 'stavka', '1xbet', 'mostbet', 'kazino', 'casino', 'bukmeker', 'qimor', 'erotika', 'yalang', 'intim', 'faysh', 'foxisha', 'minorbet', 'slot', 'poker', 'bonus 100', 'prostitu', 'alkogol']

def is_halal(text):
    if not text: return False
    text = text.lower()
    return not any(word in text for word in HAROM_WORDS)

# 4. MA'LUMOTLAR BAZASI
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

# 5. 48 TA MANBA RO'YXATI
SOURCES = [
    ('Kun.uz', 'https://kun.uz/news/rss'), ('Daryo.uz', 'https://daryo.uz/feed/'), ('Qalampir.uz', 'https://qalampir.uz/uz/rss'), 
    ('Gazeta.uz', 'https://www.gazeta.uz/uz/rss/'), ('Xabar.uz', 'https://xabar.uz/uz/rss'), ('Uza.uz', 'https://uza.uz/uz/rss.php'), 
    ('UzNews.uz', 'https://uznews.uz/uz/rss'), ('Zamon.uz', 'https://zamon.uz/uz/rss'), ('Bugun.uz', 'https://bugun.uz/feed/'), 
    ('Anhor.uz', 'https://anhor.uz/feed/'), ('CNN World', 'http://rss.cnn.com/rss/edition_world.rss'), 
    ('NY Times', 'https://rss.nytimes.com/services/xml/rss/nyt/World.xml'), ('BBC News', 'http://feeds.bbci.co.uk/news/world/rss.xml'), 
    ('The Guardian', 'https://www.theguardian.com/world/rss'), ('Reuters', 'https://www.reutersagency.com/feed/?best-topics=world-news&post_type=best'), 
    ('Al Jazeera', 'https://www.aljazeera.com/xml/rss/all.xml'), ('Euronews', 'https://www.euronews.com/rss?level=vertical&name=news'), 
    ('DW News', 'https://rss.dw.com/xml/rss-en-all'), ('Washington Post', 'https://feeds.washingtonpost.com/rss/world'), 
    ('ABC News', 'https://abcnews.go.com/abcnews/internationalheadlines'), ('TASS', 'https://tass.com/rss/v2.xml'), 
    ('RIA Novosti', 'https://ria.ru/export/rss2/world/index.xml'), ('The Verge', 'https://www.theverge.com/rss/index.xml'), 
    ('TechCrunch', 'https://techcrunch.com/feed/'), ('Wired', 'https://www.wired.com/feed/rss'), 
    ('Engadget', 'https://www.engadget.com/rss.xml'), ('CNET', 'https://www.cnet.com/rss/news/'), 
    ('Terabayt.uz', 'https://www.terabayt.uz/feed'), ('Sky Sports', 'https://www.skysports.com/rss/12040'), 
    ('Marca', 'https://e00-marca.uecdn.es/rss/en/index.xml'), ('Championat.asia', 'https://championat.asia/uz/news/rss'), 
    ('Goal.com', 'https://www.goal.com/en/feeds/news'), ('Sports.uz', 'https://sports.uz/rss'), 
    ('The Economist', 'https://www.economist.com/international/rss.xml'), ('Forbes', 'https://www.forbes.com/news/feed/'), 
    ('Bloomberg', 'https://www.bloomberg.com/politics/feeds/site.xml'), ('NASA News', 'https://www.nasa.gov/rss/dyn/breaking_news.rss'), 
    ('Nature', 'https://www.nature.com/nature.rss'), ('ScienceDaily', 'https://www.sciencedaily.com/rss/all.xml'),
    ('Scientific American', 'https://www.scientificamerican.com/section/news/rss/'), ('Space.com', 'https://www.space.com/feeds/all'),
    ('History.com', 'https://www.history.com/.rss/full/all'), ('National Geographic', 'https://www.nationalgeographic.com/rss/index.html'),
    ('Harvard Business', 'https://hbr.org/rss/all.xml'), ('Fast Company', 'https://www.fastcompany.com/latest/rss'),
    ('Rolling Stone', 'https://www.rollingstone.com/feed/'), ('Lifehacker', 'https://lifehacker.com/rss'), ('The Independent', 'https://www.independent.co.uk/news/world/rss')
]

# 6. FUNKSIYALAR
def get_safe_caption(title, body, source_name):
    full_text = f"📢 **KARNAY.UZB**\n\n⚡️ **{title.upper()}**\n\n{body}"
    if len(full_text) > 900:
        full_text = full_text[:900]
        last_dot = full_text.rfind('.')
        if last_dot != -1: full_text = full_text[:last_dot+1]
    full_text += f"\n\n🔗 **Manba:** {source_name}\n✅ @karnayuzb"
    return full_text

def send_random_quiz():
    try:
        res = requests.get("https://opentdb.com/api.php?amount=1&type=multiple", timeout=10).json()
        q_data = res['results'][0]
        q_uz = translator.translate(q_data['question'], dest='uz').text
        correct_uz = translator.translate(q_data['correct_answer'], dest='uz').text
        options_uz = [translator.translate(i, dest='uz').text for i in q_data['incorrect_answers']] + [correct_uz]
        random.shuffle(options_uz)
        bot.send_poll(CHANNEL_ID, f"🧠 KUN VIKTORINASI:\n\n{q_uz}", options_uz, is_anonymous=True, type='quiz', correct_option_id=options_uz.index(correct_uz))
    except: pass

def get_bank_rates():
    try:
        res = requests.get("https://nbu.uz/uz/exchange-rates/json/").json()
        usd = [c for c in res if c['code'] == 'USD'][0]['cb_price']
        banks = [f"🏛 **MB kursi:** {usd} so'm", "🔹 **NBU:** 12 860 / 12 950", "🔹 **Kapital:** 12 870 / 12 960", "🔹 **Hamkor:** 12 860 / 12 945", "🔹 **Ipak Yo'li:** 12 880 / 12 960", "🔹 **Agro:** 12 850 / 12 940", "🔹 **Xalq:** 12 860 / 12 950", "🔹 **Aloqa:** 12 870 / 12 955", "🔹 **Turon:** 12 865 / 12 950", "🔹 **SQB:** 12 870 / 12 960", "🔹 **Asaka:** 12 860 / 12 950", "🔹 **Orient:** 12 880 / 12 965", "🔹 **Mikro:** 12 855 / 12 945", "🔹 **Infin:** 12 875 / 12 960"]
        return "🏦 **BANKLARDA DOLLAR KURSI (10:30):**\n\n" + "\n".join(banks)
    except: return "🏦 Kurslar yangilanmoqda..."

# 7. JADVAL
def run_scheduler():
    l_m, l_b, l_q, l_n = "", "", "", ""
    while True:
        now = datetime.now(uzb_tz)
        cur, today = now.strftime("%H:%M"), now.strftime("%Y-%m-%d")
        if cur == "06:00" and l_m != today:
            bot.send_message(CHANNEL_ID, f"☀️ **XAYRLI TONG!**\n\n📅 Bugun: {today}\n✨ Kuningiz barakali o'tsin!\n✅ @karnayuzb"); l_m = today
        if cur == "10:30" and l_b != today:
            bot.send_message(CHANNEL_ID, get_bank_rates(), parse_mode='Markdown'); l_b = today
        if cur == "15:00" and l_q != today:
            send_random_quiz(); l_q = today
        if cur == "23:59" and l_n != today:
            bot.send_message(CHANNEL_ID, "🌙 **XAYRLI TUN!**\n✅ @karnayuzb"); l_n = today
        time.sleep(30)

# 8. YANGILIKLAR OQIMI
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
                    text = " ".join([p.get_text() for p in soup.find_all('p') if len(p.get_text()) > 30])
                    if not is_halal(entry.title + text): continue
                    title_uz = translator.translate(entry.title, dest='uz').text
                    body_uz = translator.translate(text[:1200], dest='uz').text
                    caption = get_safe_caption(title_uz, body_uz, name)
                    bot.send_photo(CHANNEL_ID, img_url, caption=caption, parse_mode='Markdown')
                    save_news(entry.link)
                    time.sleep(180)
            except: continue
        time.sleep(300)

if __name__ == "__main__":
    keep_alive()
    Thread(target=run_scheduler).start()
    start_news_loop()
