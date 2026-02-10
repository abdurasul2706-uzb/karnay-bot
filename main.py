import telebot
import feedparser
import time
import requests
import re
from bs4 import BeautifulSoup
from googletrans import Translator
from flask import Flask
from threading import Thread

# 1. SERVER
app = Flask('')
@app.route('/')
def home(): return "Bot is running!"
def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run).start()

# 2. SOZLAMALAR
TOKEN = '8358476165:AAFsfhih8yWO0pXaJa_JCvndQ8DUUQZWads'
CHANNEL_ID = '@karnayuzb'

SOURCES = {
    'Kun.uz': 'https://kun.uz/news/rss',
    'Daryo.uz': 'https://daryo.uz/feed/',
    'Gazeta.uz': 'https://www.gazeta.uz/uz/rss/',
    'BBC O‘zbek': 'https://www.bbc.com/uzbek/index.xml',
    'Qalampir.uz': 'https://qalampir.uz/uz/rss'
}

bot = telebot.TeleBot(TOKEN)
translator = Translator()
SENT_NEWS_CACHE = [] # Xotira ro'yxati

def clean_news_text(text):
    """Cookie va keraksiz texnik matnlarni butunlay tozalash"""
    # Cookie va maxfiylik haqidagi barcha gaplarni o'chiradi
    text = re.sub(r'.*?(cookies-fayllardan|foydalanishga rozilik|Maxfiylik siyosati|davom etish orqali).*?(\.|\!)', '', text, flags=re.IGNORECASE)
    # Ortiqcha bo'shliqlarni tozalash
    text = re.sub(r'\n+', '\n\n', text)
    return text.strip()

def get_full_and_clean_content(url):
    """Sayt ichidan eng to'liq va toza matnni tortish"""
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(res.content, 'html.parser')
        
        # Keraksiz bloklarni (cookie, reklama) o'chirib tashlaymiz
        for junk in soup(['script', 'style', 'aside', 'footer', 'header', '.cookie-alert', '.sharing']):
            junk.decompose()

        # Asosiy rasmni topish
        img = soup.find("meta", property="og:image")
        img_url = img['content'] if img else None
        
        # Matn yig'ish (paragrafma-paragraf)
        paragraphs = soup.find_all('p')
        content_list = []
        for p in paragraphs:
            p_text = p.get_text().strip()
            # Cookie matni bo'lsa o'tkazib yuboramiz
            if "cookies" in p_text.lower() or "rozilik" in p_text.lower():
                continue
            if len(p_text) > 40:
                content_list.append(p_text)
        
        # Maqolani birlashtiramiz
        full_text = "\n\n".join(content_list)
        return img_url, clean_news_text(full_text)
    except:
        return None, ""

def process_news():
    """Barcha manbalarni birma-bir va uzluksiz tekshirish"""
    for name, url in SOURCES.items():
        try:
            print(f"--- {name} tekshirilmoqda ---") #
            feed = feedparser.parse(url)
            
            for entry in feed.entries[:2]: # Har biridan 2 ta yangi xabar
                if entry.link in SENT_NEWS_CACHE:
                    continue
                
                img_url, full_text = get_full_and_clean_content(entry.link)
                
                # Agar saytdan matn ololmasa RSS'dagini oladi
                text = full_text if len(full_text) > 100 else entry.get('description', '')
                text = BeautifulSoup(text, "html.parser").get_text()
                
                # Chiroyli sarlavha va hashtaglar
                caption = f"🏛 **{name.upper()}**\n\n"
                caption += f"🔥 **{entry.title}**\n\n"
                caption += f"📝 {text[:950]}..." # Maksimal hajm
                caption += f"\n\n✅ @karnayuzb — Eng so'nggi xabarlar\n#yangiliklar #{name.replace('.', '')}"

                try:
                    if img_url:
                        bot.send_photo(CHANNEL_ID, img_url, caption=caption, parse_mode='Markdown')
                    else:
                        bot.send_message(CHANNEL_ID, caption, parse_mode='Markdown')
                    
                    SENT_NEWS_CACHE.append(entry.link)
                    if len(SENT_NEWS_CACHE) > 100: SENT_NEWS_CACHE.pop(0) # Xotirani tozalash
                    print(f"✅ Yuborildi: {name}")
                    time.sleep(10) # Telegram spamdan himoya
                except Exception as e:
                    print(f"Xato: {e}")
        except Exception as e:
            print(f"{name} manbasida xato: {e}")
            continue

if __name__ == "__main__":
    keep_alive()
    while True:
        process_news()
        print("Barcha manbalar tekshirildi. 15 daqiqa kutamiz...")
        time.sleep(900)
