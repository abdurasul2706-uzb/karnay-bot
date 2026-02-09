import telebot
import feedparser
import time
import requests
from bs4 import BeautifulSoup
from googletrans import Translator
from telebot import types
from flask import Flask
from threading import Thread

# 1. RENDER UCHUN SERVER
app = Flask('')
@app.route('/')
def home(): return "Bot is running!"
def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run).start()

# 2. SOZLAMALAR (To'g'rilangan tokeningiz bilan)
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
sent_news = []

def get_full_content(url):
    """Sayt ichiga kirib, asosiy rasm va to'liqroq matnni olish"""
    try:
        response = requests.get(url, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Asosiy rasmni qidirish (og:image tegi orqali)
        image = soup.find("meta", property="og:image")
        img_url = image['content'] if image else None
        
        # To'liqroq tavsifni qidirish
        description = soup.find("meta", property="og:description")
        text = description['content'] if description else ""
        
        return img_url, text
    except:
        return None, ""

def process_news():
    for name, url in SOURCES.items():
        try:
            print(f"---> {name} tekshirilmoqda...")
            feed = feedparser.parse(url)
            
            for entry in feed.entries[:3]:
                if entry.link in sent_news:
                    continue
                
                # Saytdan to'liq ma'lumotni tortish
                img_url, full_text = get_full_content(entry.link)
                
                title = entry.title
                # Agar saytdan matn ololmasa, RSS'dagi qisqa matnni oladi
                description = full_text if len(full_text) > 50 else entry.get('description', '')
                
                # HTML teglardan tozalash
                description = BeautifulSoup(description, "html.parser").get_text()
                
                # Tarjima qilish (Chet el manbalari uchun)
                if name not in ['Kun.uz', 'Daryo.uz', 'Terabayt.uz']:
                    try:
                        title = translator.translate(title, dest='uz').text
                        description = translator.translate(description[:1000], dest='uz').text # Maksimal 1000 belgi
                    except: pass

                # Post formati (Chiroyli ko'rinishda)
                caption = f"🔥 **{title}**\n\n"
                caption += f"{description[:800]}...\n\n" # Uzun matn
                caption += f"🏛 Manba: **{name}**\n"
                caption += f"👉 @karnayuzb"

                markup = types.InlineKeyboardMarkup()
                markup.add(types.InlineKeyboardButton("Batafsil o'qish 🌐", url=entry.link))

                try:
                    if img_url:
                        bot.send_photo(CHANNEL_ID, img_url, caption=caption, parse_mode='Markdown', reply_markup=markup)
                    else:
                        bot.send_message(CHANNEL_ID, caption, parse_mode='Markdown', reply_markup=markup)
                    
                    print(f"✅ Yuborildi: {title[:30]}")
                    sent_news.append(entry.link)
                    time.sleep(5)
                except Exception as e:
                    print(f"Xato: {e}")
        except: pass

if __name__ == "__main__":
    keep_alive()
    while True:
        process_news()
        time.sleep(600) # 10 daqiqa tanaffus
