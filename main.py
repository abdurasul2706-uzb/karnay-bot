import telebot
import feedparser
import time
import requests
import re
import random
from bs4 import BeautifulSoup
from googletrans import Translator
from flask import Flask
from threading import Thread
from datetime import datetime
import pytz

# 1. SERVER SOZLAMALARI
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
SENT_NEWS_CACHE = set()
GREETING_SENT = {"morning": False, "night": False}

# 3. MANBALAR (Yana 5 ta eng kuchlisi qo'shildi)
SOURCES_LIST = [
    ('Kun.uz', 'https://kun.uz/news/rss'), 
    ('Daryo.uz', 'https://daryo.uz/feed/'),
    ('BBC News', 'http://feeds.bbci.co.uk/news/world/rss.xml'), 
    ('Qalampir.uz', 'https://qalampir.uz/uz/rss'),
    ('The New York Times', 'https://rss.nytimes.com/services/xml/rss/nyt/World.xml'),
    ('Gazeta.uz', 'https://www.gazeta.uz/uz/rss/'), 
    ('Al Jazeera', 'https://www.aljazeera.com/xml/rss/all.xml'),
    ('Xabar.uz', 'https://xabar.uz/uz/rss'), 
    ('Reuters', 'https://www.reutersagency.com/feed/?best-topics=world-news&post_type=best'),
    ('Uza.uz', 'https://uza.uz/uz/rss.php'), 
    ('Championat.asia', 'https://championat.asia/uz/news/rss'),
    ('Nikkei Asia', 'https://asia.nikkei.com/rss/feed/nar'), 
    ('Terabayt.uz', 'https://www.terabayt.uz/feed'),
    ('The Guardian', 'https://www.theguardian.com/world/rss'), 
    ('Podrobno.uz', 'https://podrobno.uz/rss/'),
    ('UzNews.uz', 'https://uznews.uz/uz/rss'),
    # YANGI QO'SHILGANLAR:
    ('Associated Press', 'https://newsatme.com/go/ap/world'),
    ('The Washington Post', 'https://feeds.washingtonpost.com/rss/world'),
    ('Deutsche Welle', 'https://rss.dw.com/xml/rss-en-all'),
    ('TASS News', 'https://tass.com/rss/v2.xml'),
    ('Tribuna.uz', 'https://kun.uz/news/category/sport/rss')
]

# 4. TOZALASH FUNKSIYASI
def filter_junk_text(text):
    if not text: return ""
    blacklist = [
        'cookies', 'yaxshilash va sizga qulaylik', 'rozilik bildirasiz', 'lotinchada', 
        'na russkom', 'kecha,', 'bugun,', '©', 'tahririyat', 'barcha huquqlar', 
        'gazeta reportaji', 'muallifning', 'reklama', 'obuna bo‘ling', 'facebook', 'instagram'
    ]
    lines = text.split('\n')
    cleaned_lines = []
    for line in lines:
        line_clean = line.strip()
        if len(line_clean) < 40: continue 
        if any(bad in line_clean.lower() for bad in blacklist): continue
        cleaned_lines.append(line_clean)
    
    final_text = " ".join(cleaned_lines)
    return final_text[:950]

def get_content(url):
    try:
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=12)
        soup = BeautifulSoup(res.content, 'html.parser')
        img = soup.find("meta", property="og:image")
        img_url = img['content'] if img else None
        for junk in soup(['script', 'style', 'header', 'footer', 'nav', 'aside']):
            junk.decompose()
        paras = soup.find_all('p')
        raw_text = "\n".join([p.get_text() for p in paras])
        return img_url, filter_junk_text(raw_text)
    except: return None, ""

# 5. SALOMLASHISH TIZIMI
def check_greetings():
    uzb_tz = pytz.timezone('Asia/Tashkent')
    now = datetime.now(uzb_tz)
    h_m = now.strftime("%H:%M")
    if h_m == "06:00" and not GREETING_SENT["morning"]:
        sana = now.strftime("%d-%m-%Y")
        kunlar = {"Monday":"Dushanba","Tuesday":"Seshanba","Wednesday":"Chorshanba","Thursday":"Payshanba","Friday":"Juma","Saturday":"Shanba","Sunday":"Yakshanba"}
        hafta_kuni = kunlar.get(now.strftime("%A"), "")
        msg = f"☀️ **Xayrli tong!**\n\nBugun: {sana}\n{hafta_kuni}.\n\nKuningiz xayrli va barokatli o'tsin! 😊"
        bot.send_message(CHANNEL_ID, msg, parse_mode='Markdown')
        GREETING_SENT["morning"] = True
        GREETING_SENT["night"] = False
    if h_m == "23:59" and not GREETING_SENT["night"]:
        msg = "🌙 **Xayrli tun.**\n\nYaxshi dam oling. Ertangi kun muvaffaqiyatli kelsin! ✨"
        bot.send_message(CHANNEL_ID, msg, parse_mode='Markdown')
        GREETING_SENT["night"] = True
        GREETING_SENT["morning"] = False

# 6. ASOSIY ISHCHI
def process_news():
    random.shuffle(SOURCES_LIST)
    for name, url in SOURCES_LIST:
        check_greetings()
        try:
            feed = feedparser.parse(url)
            # Har bir manbadan 2 ta yangi xabarni tekshirish (faollik oshishi uchun)
            for entry in feed.entries[:2]:
                if entry.link in SENT_NEWS_CACHE: continue
                
                img_url, text = get_content(entry.link)
                if len(text) < 150: continue 
                
                title = entry.title
                if name not in ['Kun.uz', 'Daryo.uz', 'Gazeta.uz', 'Qalampir.uz', 'Xabar.uz', 'Uza.uz', 'Tribuna.uz', 'UzNews.uz', 'Championat.asia']:
                    try:
                        title = translator.translate(title, dest='uz').text
                        text = translator.translate(text, dest='uz').text
                    except: pass

                caption = f"📢 **{name.upper()}**\n\n"
                caption += f"**{title}**\n\n"
                caption += f"{text}...\n\n"
                caption += f"✅ @karnayuzb — Dunyo sizning qo'lingizda!\n"
                caption += f"#{name.replace(' ', '')} #yangiliklar"

                try:
                    if img_url: bot.send_photo(CHANNEL_ID, img_url, caption=caption, parse_mode='Markdown')
                    else: bot.send_message(CHANNEL_ID, caption, parse_mode='Markdown')
                    SENT_NEWS_CACHE.add(entry.link)
                    print(f"✅ {name} yuborildi.")
                    time.sleep(15) # Telegram spami oldini olish
                except: continue
        except: continue

if __name__ == "__main__":
    keep_alive()
    while True:
        process_news()
        # Tekshirish oralig'ini 5 daqiqadan 3 daqiqaga tushirdim (tezroq ishlashi uchun)
        time.sleep(180)
