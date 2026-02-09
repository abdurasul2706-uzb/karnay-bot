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

# 1. RENDER UCHUN SERVER
app = Flask('')
@app.route('/')
def home(): return "Bot is running!"
def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run).start()

# 2. SOZLAMALAR
TOKEN = '8358476165:AAFsfhih8yWO0pXaJa_JCvndQ8DUUQZWads'
CHANNEL_ID = '@karnayuzb'

# Global xotira (Runtime memory)
# Professional yechim uchun bu yerda Database bo'lishi kerak
SENT_NEWS_CACHE = set() 

SOURCES = {
    'Kun.uz': 'https://kun.uz/news/rss',
    'Daryo.uz': 'https://daryo.uz/feed/',
    'BBC World': 'http://feeds.bbci.co.uk/news/world/rss.xml',
    'Terabayt.uz': 'https://www.terabayt.uz/feed'
}

bot = telebot.TeleBot(TOKEN)
translator = Translator()

def get_smart_content(url):
    """Sayt ichidagi eng muhim va to'liq matnni topish"""
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Asosiy rasm
        image = soup.find("meta", property="og:image")
        img_url = image['content'] if image else None
        
        # Matnni yig'ish (Professional skraping)
        # Saytning asosiy maqola qismini qidirish
        article_body = soup.find(['article', 'div.content', 'div.post-text', 'div.article-body'])
        if article_body:
            paragraphs = article_body.find_all('p')
        else:
            paragraphs = soup.find_all('p')
            
        text_parts = []
        for p in paragraphs:
            p_text = p.get_text().strip()
            if len(p_text) > 60: # Reklama yoki qisqa gaplarni filtrlaymiz
                text_parts.append(p_text)
            if len(text_parts) >= 5: # Eng muhim 5 ta paragraf
                break
                
        return img_url, "\n\n".join(text_parts)
    except:
        return None, ""

def process_news():
    for name, url in SOURCES.items():
        try:
            print(f"---> {name} tekshirilmoqda...")
            feed = feedparser.parse(url)
            
            # Faqat eng oxirgi 2 ta yangilikni tekshiramiz (Takrorlanishni kamaytirish uchun)
            for entry in feed.entries[:2]:
                if entry.link in SENT_NEWS_CACHE:
                    continue
                
                img_url, full_text = get_smart_content(entry.link)
                
                title = entry.title
                # Agar saytdan matn ololmasa RSS'dagini oladi
                content = full_text if len(full_text) > 150 else entry.get('description', '')
                content = re.sub('<[^<]+?>', '', content) # HTML'dan tozalash
                
                if name not in ['Kun.uz', 'Daryo.uz', 'Terabayt.uz']:
                    try:
                        title = translator.translate(title, dest='uz').text
                        content = translator.translate(content[:1500], dest='uz').text
                    except: pass

                # POST FORMATI (PROFESSIONAL)
                caption = f"🏛 **{name.upper()}**\n\n"
                caption += f"🔥 **{title}**\n\n"
                caption += f"📝 {content[:900]}..." # Telegram limiti
                caption += f"\n\n🔗 @karnayuzb — Yangiliklar kanali"

                markup = types.InlineKeyboardMarkup()
                markup.add(types.InlineKeyboardButton("Batafsil maqolani o'qish 🌐", url=entry.link))

                try:
                    if img_url:
                        bot.send_photo(CHANNEL_ID, img_url, caption=caption, parse_mode='Markdown', reply_markup=markup)
                    else:
                        bot.send_message(CHANNEL_ID, caption, parse_mode='Markdown', reply_markup=markup)
                    
                    SENT_NEWS_CACHE.add(entry.link)
                    print(f"✅ Muvaffaqiyatli yuborildi.")
                    time.sleep(10) # Blokirovka oldini olish
                except Exception as e:
                    print(f"Yuborishda xato: {e}")
        except Exception as e:
            print(f"Manba xatosi: {e}")

if __name__ == "__main__":
    keep_alive()
    while True:
        process_news()
        # Takrorlanishni kamaytirish uchun tekshiruv vaqtini 30 daqiqa qilamiz
        print("30 daqiqa tanaffus...")
        time.sleep(1800) 
