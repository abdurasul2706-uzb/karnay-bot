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

# 3. MANBALAR (Siz aytgan tarkib bo'yicha)
SOURCES_LIST = [
    ('Kun.uz', 'https://kun.uz/news/rss'), ('The New York Times', 'https://rss.nytimes.com/services/xml/rss/nyt/World.xml'),
    ('Daryo.uz', 'https://daryo.uz/feed/'), ('BBC News', 'http://feeds.bbci.co.uk/news/world/rss.xml'),
    ('Qalampir.uz', 'https://qalampir.uz/uz/rss'), ('Al Jazeera', 'https://www.aljazeera.com/xml/rss/all.xml'),
    ('Gazeta.uz', 'https://www.gazeta.uz/uz/rss/'), ('Reuters', 'https://www.reutersagency.com/feed/?best-topics=world-news&post_type=best'),
    ('Xabar.uz', 'https://xabar.uz/uz/rss'), ('The Guardian', 'https://www.theguardian.com/world/rss'),
    ('Championat.asia', 'https://championat.asia/uz/news/rss'), ('Nikkei Asia', 'https://asia.nikkei.com/rss/feed/nar'),
    ('Uza.uz', 'https://uza.uz/uz/rss.php'), ('The Washington Post', 'https://feeds.washingtonpost.com/rss/world'),
    ('Terabayt.uz', 'https://www.terabayt.uz/feed'), ('South China Morning Post', 'https://www.scmp.com/rss/91/feed.xml'),
    ('Podrobno.uz', 'https://podrobno.uz/rss/'), ('Euronews', 'https://www.euronews.com/rss?level=vertical&name=news'),
    ('Artnews.com', 'https://www.artnews.com/feed/'), ('Sputnik O‘zbekiston', 'https://uz.sputniknews.ru/export/rss2/archive/index.xml'),
    ('CNA Asia', 'https://www.channelnewsasia.com/rssfeeds/8395981'), ('UzNews.uz', 'https://uznews.uz/uz/rss'),
    ('Nuz.uz', 'https://nuz.uz/feed')
]

# 4. FILTRLASH (Siz ko'rsatgan xatolarni yo'qotish uchun)
def filter_junk_text(text):
    """Rasmdagi xunuk matnlarni (cookie, lotincha, sana) butunlay yo'qotish"""
    if not text: return ""
    
    # Qora ro'yxat: Bu so'zlar bor gaplar o'chirib tashlanadi
    blacklist = [
        'cookies-dan foydalanishga rozilik', 'biz sayt ishlashini yaxshilash', 
        'lotinchada', 'na russkom', 'kecha,', 'bugun,', 'soat ', '©', 
        'muallifning xabarlari', 'ruxsatingiz yo‘q', 'xavfsizlik nuqtai nazaridan',
        'obuna bo‘ling', 'reklama', 'tahririyat', 'barcha huquqlar', 'gazeta reportaji'
    ]
    
    lines = text.split('\n')
    cleaned_lines = []
    for line in lines:
        line_lower = line.lower().strip()
        # Agar gap juda qisqa bo'lsa yoki ichida taqiqlangan so'z bo'lsa - o'chiramiz
        if len(line_lower) < 30: continue 
        if any(bad_word in line_lower for bad_word in blacklist): continue
        cleaned_lines.append(line.strip())
    
    # Gaplarni birlashtirish (zich holatga keltirish)
    result = " ".join(cleaned_lines)
    result = re.sub(r'\s+', ' ', result) # Ortiqcha bo'shliqlarni yo'qotish
    return result

def get_content(url):
    """Saytdan rasm va toza matn olish"""
    try:
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
        soup = BeautifulSoup(res.content, 'html.parser')
        
        # Rasm topish
        img = soup.find("meta", property="og:image")
        img_url = img['content'] if img else None
        
        # Matn qismini topish (faqat asosiy maqolani skanerlash)
        main_body = soup.find(['article', 'main', 'div[class*="content"]'])
        paras = main_body.find_all('p') if main_body else soup.find_all('p')
        
        full_text = "\n".join([p.get_text() for p in paras])
        return img_url, filter_junk_text(full_text)
    except: return None, ""

# 5. SALOMLASHISH TIZIMI
def check_greetings():
    uzb_tz = pytz.timezone('Asia/Tashkent')
    now = datetime.now(uzb_tz)
    current_time = now.strftime("%H:%M")
    today_date = now.strftime("%d-%m-%Y")
    weekday = now.strftime("%A").replace("Monday", "Dushanba").replace("Tuesday", "Seshanba").replace("Wednesday", "Chorshanba").replace("Thursday", "Payshanba").replace("Friday", "Juma").replace("Saturday", "Shanba").replace("Sunday", "Yakshanba")

    if "06:00" <= current_time <= "06:10" and not GREETING_SENT["morning"]:
        msg = f"☀️ **Xayrli tong!**\n\n📅 Bugun: {today_date}\n🗓 Haftaning kuni: {weekday}\n\nKuningiz xayrli va barokatli o'tsin! 😊"
        bot.send_message(CHANNEL_ID, msg, parse_mode='Markdown')
        GREETING_SENT["morning"] = True
        GREETING_SENT["night"] = False # Kechki uchun joy ochamiz

    if "23:58" <= current_time <= "23:59" and not GREETING_SENT["night"]:
        msg = f"🌙 **Xayrli tun!**\n\nYaxshi dam oling, aziz obunachilar. Ertangi kun yanada muvaffaqiyatli kelsin! ✨"
        bot.send_message(CHANNEL_ID, msg, parse_mode='Markdown')
        GREETING_SENT["night"] = True
        GREETING_SENT["morning"] = False # Ertangi uchun joy ochamiz

# 6. ASOSIY ISHCHI FUNKSIYA
def process_news():
    random.shuffle(SOURCES_LIST)
    for name, url in SOURCES_LIST:
        check_greetings() # Har bir manba orasida vaqtni tekshiradi
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:1]:
                if entry.link in SENT_NEWS_CACHE: continue
                
                img_url, text = get_content(entry.link)
                if not text or len(text) < 100: continue
                
                title = entry.title
                # Chet el manbalari uchun tarjima
                if name not in ['Kun.uz', 'Daryo.uz', 'Gazeta.uz', 'Qalampir.uz', 'Xabar.uz']:
                    try:
                        title = translator.translate(title, dest='uz').text
                        text = translator.translate(text[:1000], dest='uz').text
                    except: pass

                # POST TAYYORLASH
                caption = f"📢 **{name.upper()}**\n\n"
                caption += f"**{title}**\n\n"
                caption += f"{text[:900]}...\n\n"
                caption += f"✅ @karnayuzb — Dunyo sizning qo'lingizda!\n"
                caption += f"#{name.replace(' ', '')} #yangiliklar"

                if img_url:
                    bot.send_photo(CHANNEL_ID, img_url, caption=caption, parse_mode='Markdown')
                else:
                    bot.send_message(CHANNEL_ID, caption, parse_mode='Markdown')

                SENT_NEWS_CACHE.add(entry.link)
                time.sleep(10)
        except: continue

if __name__ == "__main__":
    keep_alive()
    while True:
        process_news()
        time.sleep(300)
