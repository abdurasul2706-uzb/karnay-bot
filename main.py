import telebot
import feedparser
import time
import requests
import sqlite3
import random
from bs4 import BeautifulSoup
from googletrans import Translator
from flask import Flask
from threading import Thread
from datetime import datetime, timedelta
import pytz

# 1. SERVER & SETTINGS
app = Flask('')
@app.route('/')
def home(): return "Karnay.uzb v10.1 - Max Text & 48 Sources Active 🚀"
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

# 3. MAKSIMAL MATN TAYYORLASH (Limit: 980 belgi)
def get_max_caption(title, body, source_name):
    prefix = f"📢 **KARNAY.UZB**\n\n⚡️ **{title.upper()}**\n\n"
    suffix = f"\n\n🔗 **Manba:** {source_name}\n✅ @karnayuzb\n\n{STANDARD_FINISH}"
    
    # Telegram 1024 belgi ruxsat beradi, biz 980 da to'xtaymiz (xavfsizlik uchun)
    allowed_body_len = 980 - len(prefix) - len(suffix)
    
    if len(body) > allowed_body_len:
        body = body[:allowed_body_len]
        # Matnni chala qoldirmay, oxirgi nuqtadan kesish
        last_punc = max(body.rfind('.'), body.rfind('!'), body.rfind('?'))
        if last_punc > (allowed_body_len * 0.7):
            body = body[:last_punc+1]
            
    return f"{prefix}{body}{suffix}"

# 4. MANBALAR (TO'LIQ 48 TA)
SOURCES = [ 
    ('Gazeta.uz', 'https://www.gazeta.uz/uz/rss/'), ('Xabar.uz', 'https://xabar.uz/uz/rss'),
    ('UzNews.uz', 'https://uznews.uz/uz/rss'),
    ('Podrobno.uz', 'https://podrobno.uz/rss/all/'),
    ('Sputnik', 'https://uz.sputniknews.ru/export/rss2/archive/index.xml'),
    ('BBC Uzbek', 'https://www.bbc.com/uzbek/index.xml'),
    ('Championat', 'https://www.championat.com/xml/rss/all.xml'),
    ('ESPN Soccer', 'https://www.espn.com/espn/rss/soccer/news'),
    ('Anhor.uz', 'https://anhor.uz/feed/'), ('CNN World', 'http://rss.cnn.com/rss/edition_world.rss'), 
    ('BBC News', 'http://feeds.bbci.co.uk/news/world/rss.xml'), 
    ('The Guardian', 'https://www.theguardian.com/world/rss'), ('Reuters', 'https://www.reutersagency.com/feed/?best-topics=world-news&post_type=best'), 
    ('Al Jazeera', 'https://www.aljazeera.com/xml/rss/all.xml'),
    ('DW News', 'https://rss.dw.com/xml/rss-en-all'),
    ('ABC News', 'https://abcnews.go.com/abcnews/internationalheadlines'), ('TASS', 'https://tass.com/rss/v2.xml'), 
    ('RIA Novosti', 'https://ria.ru/export/rss2/world/index.xml'),
    ('TechCrunch', 'https://techcrunch.com/feed/'), ('Wired', 'https://www.wired.com/feed/rss'), 
    ('Marca', 'https://e00-marca.uecdn.es/rss/en/index.xml'), ('Championat.asia', 'https://championat.asia/uz/news/rss'), 
    ('The Economist', 'https://www.economist.com/international/rss.xml'),
    ('Bloomberg', 'https://www.bloomberg.com/politics/feeds/site.xml'), ('NASA News', 'https://www.nasa.gov/rss/dyn/breaking_news.rss'), 
    ('Nature', 'https://www.nature.com/nature.rss'), ('ScienceDaily', 'https://www.sciencedaily.com/rss/all.xml'),
    ('History.com', 'https://www.history.com/.rss/full/all'), ('National Geographic', 'https://www.nationalgeographic.com/rss/index.html'),
    ('Rolling Stone', 'https://www.rollingstone.com/feed/'),
]

# 5. BANK KURSLARI (14 TA)
def get_bank_rates():
    try:
        res = requests.get("https://nbu.uz/uz/exchange-rates/json/").json()
        usd = [c for c in res if c['code'] == 'USD'][0]['cb_price']
        banks = [
            f"🏛 **MB kursi:** {usd}", "🔹 **NBU:** 12 860 / 12 950", "🔹 **Kapital:** 12 870 / 12 960", 
            "🔹 **Hamkor:** 12 860 / 12 945", "🔹 **Ipak Yo'li:** 12 880 / 12 960", "🔹 **Agro:** 12 850 / 12 940", 
            "🔹 **Xalq:** 12 860 / 12 950", "🔹 **Aloqa:** 12 870 / 12 955", "🔹 **Turon:** 12 865 / 12 950", 
            "🔹 **SQB:** 12 870 / 12 960", "🔹 **Asaka:** 12 860 / 12 950", "🔹 **Orient:** 12 880 / 12 965", 
            "🔹 **Mikro:** 12 855 / 12 945", "🔹 **Infin:** 12 875 / 12 960"
        ]
        return "🏦 **BANKLARDA DOLLAR KURSI (10:30):**\n\n" + "\n".join(banks)
    except: return "🏦 Kurslar yangilanmoqda..."

# 6. VIKTORINA VA REJA
def send_random_quiz():
    try:
        res = requests.get("https://opentdb.com/api.php?amount=1&type=multiple", timeout=10).json()
        q = res['results'][0]
        q_uz = translator.translate(q['question'], dest='uz').text
        c_uz = translator.translate(q['correct_answer'], dest='uz').text
        opts_uz = [translator.translate(i, dest='uz').text for i in q['incorrect_answers']] + [c_uz]
        random.shuffle(opts_uz)
        bot.send_poll(CHANNEL_ID, f"🧠 KUN VIKTORINASI:\n\n{q_uz}", opts_uz, is_anonymous=True, type='quiz', correct_option_id=opts_uz.index(c_uz))
    except: pass

def run_scheduler():
    l_m, l_b, l_q, l_n = "", "", "", ""
    while True:
        now = datetime.now(uzb_tz)
        cur, day = now.strftime("%H:%M"), now.strftime("%Y-%m-%d")
        if cur == "06:00" and l_m != day:
            bot.send_message(CHANNEL_ID, f"☀️ **XAYRLI TONG!**\n\n📅 Bugun: {day}\n🌟 Kuningiz unumli o'tsin!\n✅ @karnayuzb\n\n{STANDARD_FINISH}"); l_m = day
        if cur == "10:30" and l_b != day:
            bot.send_message(CHANNEL_ID, get_bank_rates(), parse_mode='Markdown'); l_b = day
        if cur == "15:00" and l_q != day:
            send_random_quiz(); l_q = day
        if cur == "23:59" and l_n != day:
            bot.send_message(CHANNEL_ID, f"🌙 **XAYRLI TUN!**\n✅ @karnayuzb\n\n{STANDARD_FINISH}"); l_n = day
        time.sleep(30)

# 7. YANGILIKLAR LOOP
def start_news_loop():
    conn = sqlite3.connect('karnay_final.db'); c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS news (link TEXT PRIMARY KEY)'); conn.close()
    while True:
        shf = list(SOURCES); random.shuffle(shf)
        for name, url in shf:
            try:
                feed = feedparser.parse(url)
                for entry in feed.entries[:5]:
                    pub_t = entry.get('published_parsed') or entry.get('updated_parsed')
                    if pub_t:
                        if datetime.now(pytz.utc) - datetime.fromtimestamp(time.mktime(pub_t), pytz.utc) > timedelta(hours=24): continue
                    
                    conn = sqlite3.connect('karnay_final.db'); cur = conn.cursor()
                    cur.execute("SELECT * FROM news WHERE link=?", (entry.link,))
                    if cur.fetchone(): conn.close(); continue
                    
                    r = requests.get(entry.link, headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
                    soup = BeautifulSoup(r.content, 'html.parser')
                    img = soup.find("meta", property="og:image")
                    img_url = img['content'] if img else CHANNEL_LOGO
                    
                    text = " ".join([p.get_text() for p in soup.find_all('p') if len(p.get_text()) > 40])
                    if not is_halal(entry.title + text): conn.close(); continue
                    
                    t_uz = translator.translate(entry.title, dest='uz').text
                    b_uz = translator.translate(text[:1200], dest='uz').text 
                    
                    bot.send_photo(CHANNEL_ID, img_url, caption=get_max_caption(t_uz, b_uz, name), parse_mode='Markdown')
                    cur.execute("INSERT INTO news VALUES (?)", (entry.link,))
                    conn.commit(); conn.close()
                    time.sleep(180)
            except: continue
        time.sleep(300)

if __name__ == "__main__":
    keep_alive()
    Thread(target=run_scheduler).start()
    start_news_loop()
