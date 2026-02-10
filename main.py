import telebot
import feedparser
import time
import requests
import re
from bs4 import BeautifulSoup
from googletrans import Translator
from telebot import types
from flask import Flask
from threading import Thread

app = Flask('')
@app.route('/')
def home(): return "Bot is running!"
def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run).start()

TOKEN = '8358476165:AAFsfhih8yWO0pXaJa_JCvndQ8DUUQZWads'
CHANNEL_ID = '@karnayuzb'

SOURCES = {
    'Kun.uz': 'https://kun.uz/news/rss',
    'Daryo.uz': 'https://daryo.uz/feed/',
    'BBC World': 'http://feeds.bbci.co.uk/news/world/rss.xml',
    'Terabayt.uz': 'https://www.terabayt.uz/feed'
}

bot = telebot.TeleBot(TOKEN)
translator = Translator()
SENT_NEWS_CACHE = set()

def clean_text(text):
    """Keraksiz cookie va reklama matnlarini o'chirish"""
    unwanted_phrases = [
        "cookies-fayllardan foydalanamiz",
        "Davom etish orqali siz cookies-dan",
        "Maxfiylik siyosati",
        "reklama",
        "Kun.uz", # Matn ichidagi ortiqcha nomlar
        "Daryo"
    ]
    for phrase in unwanted_phrases:
        text = re.sub(rf".*?{phrase}.*?(\.|\!)", "", text, flags=re.IGNORECASE)
    return text.strip()

def get_smart_content(url, source_name):
    """Har bir sayt uchun maxsus va kengaytirilgan skraping"""
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Rasm topish
        image = soup.find("meta", property="og:image")
        img_url = image['content'] if image else None
        
        # Sayt turiga qarab asosiy matn blokini topish
        content_selectors = [
            'div.single-content', 'div.article-body', 'div.post-content', 
            'div.news-text', 'div.content', 'article'
        ]
        
        main_content = None
        for selector in content_selectors:
            main_content = soup.select_one(selector)
            if main_content: break
        
        if not main_content: main_content = soup
        
        # Barcha paragraflarni yig'ish
        paragraphs = main_content.find_all('p')
        text_parts = []
        for p in paragraphs:
            p_text = p.get_text().strip()
            # Cookie va juda qisqa matnlarni tashlab yuborish
            if len(p_text) > 50 and "cookies-fayllardan" not in p_text:
                text_parts.append(p_text)
        
        # Eng muhim 6-7 ta paragrafni birlashtirish (Telegram limiti uchun)
        full_text = "\n\n".join(text_parts[:7])
        return img_url, clean_text(full_text)
    except Exception as e:
        print(f"Skraping xatosi ({source_name}): {e}")
        return None, ""

def process_news():
    for name, url in SOURCES.items():
        try:
            print(f"---> {name} tekshirilmoqda...")
            feed = feedparser.parse(url)
            
            for entry in feed.entries[:3]:
                if entry.link in SENT_NEWS_CACHE: continue
                
                print(f"Yangi xabar topildi: {entry.title}")
                img_url, full_text = get_smart_content(entry.link, name)
                
                title = entry.title
                # Agar saytdan matn ololmasa RSS'dagini oladi
                content = full_text if len(full_text) > 100 else entry.get('description', '')
                content = BeautifulSoup(content, "html.parser").get_text()
                
                # Chet el manbalarini tarjima qilish
                if name not in ['Kun.uz', 'Daryo.uz', 'Terabayt.uz']:
                    try:
                        title = translator.translate(title, dest='uz').text
                        content = translator.translate(content[:1500], dest='uz').text
                    except: pass

                # POST FORMATI
                caption = f"🏛 **{name.upper()}**\n\n"
                caption += f"🔥 **{title}**\n\n"
                caption += f"📝 {content[:950]}..." # Telegram rasm osti limiti
                caption += f"\n\n🔗 @karnayuzb — Eng tezkor xabarlar"

                markup = types.InlineKeyboardMarkup()
                markup.add(types.InlineKeyboardButton("Batafsil o'qish 🌐", url=entry.link))

                try:
                    if img_url:
                        bot.send_photo(CHANNEL_ID, img_url, caption=caption, parse_mode='Markdown', reply_markup=markup)
                    else:
                        bot.send_message(CHANNEL_ID, caption, parse_mode='Markdown', reply_markup=markup)
                    
                    SENT_NEWS_CACHE.add(entry.link)
                    print(f"✅ {name} xabari yuborildi.")
                    time.sleep(10) 
                except Exception as e:
                    print(f"Yuborish xatosi: {e}")
        except Exception as e:
            print(f"Manba xatosi ({name}): {e}")

if __name__ == "__main__":
    keep_alive()
    while True:
        process_news()
        print("15 daqiqa dam olamiz...")
        time.sleep(900)
