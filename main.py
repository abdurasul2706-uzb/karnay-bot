import telebot
import feedparser
import time
import requests
import os
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

# 2. SOZLAMALAR
TOKEN = '8358476165:AAFsfhih8yWO0pXaJa_JCvndQ8DUUQZWads'
CHANNEL_ID = '@karnayuzb'
DB_FILE = "sent_news.txt" # Xotira fayli

SOURCES = {
    'Kun.uz': 'https://kun.uz/news/rss',
    'Daryo.uz': 'https://daryo.uz/feed/',
    'BBC World': 'http://feeds.bbci.co.uk/news/world/rss.xml',
    'Terabayt.uz': 'https://www.terabayt.uz/feed'
}

bot = telebot.TeleBot(TOKEN)
translator = Translator()

# XOTIRA FUNKSIYALARI
def load_sent_news():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            return f.read().splitlines()
    return []

def save_sent_news(link):
    with open(DB_FILE, "a") as f:
        f.write(link + "\n")

def get_full_article(url):
    """Sayt ichidagi to'liq matn va rasmni tortish"""
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Rasm topish
        image = soup.find("meta", property="og:image")
        img_url = image['content'] if image else None
        
        # TO'LIQ MATNNI QIDIRISH (Asosiy qism)
        paragraphs = soup.find_all('p')
        full_text = ""
        for p in paragraphs:
            txt = p.get_text().strip()
            if len(txt) > 40: # Juda qisqa gaplarni tashlab ketamiz
                full_text += txt + "\n\n"
            if len(full_text) > 1500: # Telegram limiti uchun cheklov
                break
        
        return img_url, full_text
    except:
        return None, ""

def process_news():
    sent_news = load_sent_news()
    for name, url in SOURCES.items():
        try:
            print(f"---> {name} tekshirilmoqda...")
            feed = feedparser.parse(url)
            
            for entry in feed.entries[:3]:
                if entry.link in sent_news:
                    continue
                
                print(f"Yangi xabar: {entry.title}")
                img_url, full_content = get_full_article(entry.link)
                
                title = entry.title
                content = full_content if len(full_content) > 100 else entry.get('description', '')
                
                # Tarjima (Chet el manbalari uchun)
                if name not in ['Kun.uz', 'Daryo.uz', 'Terabayt.uz']:
                    try:
                        title = translator.translate(title, dest='uz').text
                        content = translator.translate(content[:2000], dest='uz').text
                    except: pass

                # POST FORMATI
                caption = f"🔥 **{title}**\n\n"
                caption += f"{content[:1000]}..." # 1000 belgi - eng optimal hajm
                caption += f"\n\n🏛 Manba: **{name}**\n👉 @karnayuzb"

                markup = types.InlineKeyboardMarkup()
                markup.add(types.InlineKeyboardButton("Batafsil (Saytda) 🌐", url=entry.link))

                try:
                    if img_url:
                        bot.send_photo(CHANNEL_ID, img_url, caption=caption, parse_mode='Markdown', reply_markup=markup)
                    else:
                        bot.send_message(CHANNEL_ID, caption, parse_mode='Markdown', reply_markup=markup)
                    
                    save_sent_news(entry.link)
                    print(f"✅ Yuborildi.")
                    time.sleep(5)
                except Exception as e:
                    print(f"Xato: {e}")
        except: pass

if __name__ == "__main__":
    keep_alive()
    while True:
        process_news()
        time.sleep(600)
