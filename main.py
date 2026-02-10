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

# 1. SERVER SOZLAMALARI
app = Flask('')
@app.route('/')
def home(): return "Bot is running!"
def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run).start()

# 2. BOT VA MANBALAR
TOKEN = '8358476165:AAFsfhih8yWO0pXaJa_JCvndQ8DUUQZWads'
CHANNEL_ID = '@karnayuzb'

SOURCES = {
    'Kun.uz': 'https://kun.uz/news/rss',
    'Daryo.uz': 'https://daryo.uz/feed/',
    'Gazeta.uz': 'https://www.gazeta.uz/uz/rss/',
    'Terabayt.uz': 'https://www.terabayt.uz/feed',
    'BBC O‘zbek': 'https://www.bbc.com/uzbek/index.xml',
    'Qalampir.uz': 'https://qalampir.uz/uz/rss',
    'Reuters (Dunyo)': 'http://feeds.reuters.com/reuters/worldNews',
    'BBC World': 'http://feeds.bbci.co.uk/news/world/rss.xml'
}

bot = telebot.TeleBot(TOKEN)
translator = Translator()
SENT_NEWS_CACHE = set()

def clean_text(text):
    """Keraksiz cookie va ortiqcha matnlarni filtrlaydi"""
    phrases = ["cookies-fayllardan foydalanamiz", "rozilik bildirasiz", "Maxfiylik siyosati"]
    for p in phrases:
        text = text.replace(p, "")
    return text.strip()

def get_content(url):
    """Saytdan rasm va to'liqroq matnni tortish"""
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.content, 'html.parser')
        
        # Rasm
        img = soup.find("meta", property="og:image")
        img_url = img['content'] if img else None
        
        # Matn (Barcha paragraflarni yig'ish)
        paras = soup.find_all('p')
        content = "\n\n".join([p.get_text() for p in paras if len(p.get_text()) > 50][:5])
        return img_url, clean_text(content)
    except:
        return None, ""

def send_to_channel(name, entry):
    """Bitta xabarni kanalga yuborish logikasi"""
    try:
        img_url, full_text = get_content(entry.link)
        title = entry.title
        text = full_text if len(full_text) > 100 else entry.get('description', '')
        text = BeautifulSoup(text, "html.parser").get_text()

        # Tarjima (O'zbekcha bo'lmaganlar uchun)
        if any(x in name for x in ['BBC World', 'Reuters']):
            try:
                title = translator.translate(title, dest='uz').text
                text = translator.translate(text[:1500], dest='uz').text
            except: pass

        caption = f"🏛 **{name.upper()}**\n\n🔥 **{title}**\n\n📝 {text[:900]}...\n\n👉 @karnayuzb"
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("To'liq o'qish 🌐", url=entry.link))

        if img_url:
            bot.send_photo(CHANNEL_ID, img_url, caption=caption, parse_mode='Markdown', reply_markup=markup)
        else:
            bot.send_message(CHANNEL_ID, caption, parse_mode='Markdown', reply_markup=markup)
        
        return True
    except Exception as e:
        print(f"Yuborishda xato: {e}")
        return False

def process_news():
    """Asosiy sikl: Saytlarni birma-bir aylanish"""
    for name, url in SOURCES.items():
        try:
            print(f"--- {name} tekshirilmoqda ---") #
            feed = feedparser.parse(url)
            
            # Har bir manbadan eng yangi 1 tasini olamiz
            if feed.entries:
                entry = feed.entries[0]
                if entry.link not in SENT_NEWS_CACHE:
                    if send_to_channel(name, entry):
                        SENT_NEWS_CACHE.add(entry.link)
                        time.sleep(5)
        except Exception as e:
            print(f"!!! {name} saytida xatolik: {e}. Keyingisiga o'tiladi.")
            continue # Xato bo'lsa keyingi saytga o'tish

if __name__ == "__main__":
    keep_alive()
    while True:
        process_news()
        print("Sikl tugadi. 15 daqiqa kutish...")
        time.sleep(900)
