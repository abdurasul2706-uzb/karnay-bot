import telebot
import feedparser
import time
import requests
import re
from bs4 import BeautifulSoup
from googletrans import Translator
from flask import Flask
from threading import Thread

# 1. SERVER (Render uxlab qolmasligi uchun)
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
SENT_NEWS_CACHE = []

def deep_clean_text(text):
    """Cookie, reklama va keraksiz gaplarni butunlay qirqib tashlaydi"""
    # Cookie va rozilik haqidagi barcha gaplarni o'chirish (Regex orqali)
    patterns = [
        r'.*?cookies-fayllardan.*?(\.|\!)',
        r'.*?davom etish orqali.*?(\.|\!)',
        r'.*?rozilik bildirasiz.*?(\.|\!)',
        r'.*?Maxfiylik siyosati.*?(\.|\!)',
        r'Kun\.uz', r'Daryo', r'Gazeta\.uz' # Sayt nomlarini matn ichidan tozalash
    ]
    for pattern in patterns:
        text = re.sub(pattern, '', text, flags=re.IGNORECASE | re.DOTALL)
    
    # Ortiqcha bo'shliqlar va yangi qatorlarni tozalash
    text = re.sub(r'\n+', '\n\n', text)
    return text.strip()

def get_full_article(url):
    """Sayt ichiga kirib, eng asosiy maqola qismini ajratib oladi"""
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        res = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(res.content, 'html.parser')
        
        # Keraksiz HTML elementlarni olib tashlash
        for tag in soup(['script', 'style', 'header', 'footer', 'aside', 'nav', 'form']):
            tag.decompose()

        # Asosiy rasmni qidirish
        img = soup.find("meta", property="og:image")
        img_url = img['content'] if img else None
        
        # Maqola matni joylashgan ehtimoliy bloklarni qidirish
        content_area = soup.find(['article', 'div.single-content', 'div.article-body', 'div.post-content'])
        if not content_area:
            content_area = soup

        paragraphs = content_area.find_all('p')
        cleaned_paragraphs = []
        
        for p in paragraphs:
            p_text = p.get_text().strip()
            # Qisqa va keraksiz paragraflarni filtrlaymiz
            if len(p_text) > 40 and not any(word in p_text.lower() for word in ['cookies', 'copyright', 'all rights']):
                cleaned_paragraphs.append(p_text)
        
        full_text = "\n\n".join(cleaned_paragraphs)
        return img_url, deep_clean_text(full_text)
    except:
        return None, ""

def process_news():
    """Manbalarni birma-bir, to'xtovsiz tekshirish"""
    for name, url in SOURCES.items():
        try:
            print(f"Skanerlanmoqda: {name}...")
            feed = feedparser.parse(url)
            
            for entry in feed.entries[:2]:
                if entry.link in SENT_NEWS_CACHE:
                    continue
                
                img_url, main_text = get_full_article(entry.link)
                
                # Agar saytdan matn ololmasa, sarlavhani o'zini yuboradi
                display_text = main_text if len(main_text) > 50 else entry.get('description', '')
                
                # Telegram limiti: 1024 belgi. Biz 1000 belgi qilib kesamiz.
                if len(display_text) > 1000:
                    display_text = display_text[:997] + "..."

                caption = f"🏛 **{name.upper()}**\n\n"
                caption += f"🔥 **{entry.title}**\n\n"
                caption += f"📝 {display_text}\n\n"
                caption += f"✅ @karnayuzb — Eng tezkor xabarlar"

                try:
                    if img_url:
                        bot.send_photo(CHANNEL_ID, img_url, caption=caption, parse_mode='Markdown')
                    else:
                        bot.send_message(CHANNEL_ID, caption, parse_mode='Markdown')
                    
                    SENT_NEWS_CACHE.append(entry.link)
                    if len(SENT_NEWS_CACHE) > 100: SENT_NEWS_CACHE.pop(0)
                    print(f"✅ Yuborildi: {entry.title[:30]}")
                    time.sleep(5)
                except Exception as e:
                    print(f"Yuborishda xato: {e}")
        except Exception as e:
            print(f"{name} manbasida muammo: {e}")
            continue

if __name__ == "__main__":
    keep_alive()
    while True:
        process_news()
        print("Barcha manbalar ko'rildi. 10 daqiqa kutamiz.")
        time.sleep(600)
