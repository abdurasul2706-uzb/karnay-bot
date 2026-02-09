import telebot
import feedparser
import time
import urllib.parse
import re
from googletrans import Translator
from telebot import types
from flask import Flask
from threading import Thread

# 1. RENDERDA 24/7 ISHLASH UCHUN KICHIK SERVER
app = Flask('')

@app.route('/')
def home():
    return "Bot is running!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# 2. ASOSIY SOZLAMALAR
TOKEN = '8358476165:AAFsfhih8yWO0pXaJa_JCvndQ8DUUQZWads' 
CHANNEL_ID = '@karnayuzb' # Kanal userneymi to'g'riligini tekshiring!

SOURCES = {
    'BBC World': 'http://feeds.bbci.co.uk/news/world/rss.xml',
    'Al Jazeera': 'https://www.aljazeera.com/xml/rss/all.xml',
    'Kun.uz': 'https://kun.uz/news/rss',
    'Daryo.uz': 'https://daryo.uz/feed/',
    'Terabayt.uz': 'https://www.terabayt.uz/feed',
    'Reuters': 'https://www.reutersagency.com/feed/?best-topics=world-news&post_type=best'
}

bot = telebot.TeleBot(TOKEN)
translator = Translator()
sent_news = [] # Xabarlar xotirasi

def clean_html(raw_html):
    """HTML belgilarni tozalash"""
    cleanr = re.compile('<.*?>')
    return re.sub(cleanr, '', raw_html)

def get_image_url(entry):
    """RSS ichidan rasm topish"""
    if 'links' in entry:
        for link in entry.links:
            if 'image' in link.get('type', '') or 'media' in link.get('rel', ''):
                return link.get('href')
    if 'media_content' in entry:
        return entry.media_content[0]['url']
    return None

def process_news():
    """Yangiliklarni o'qish va yuborish"""
    for name, url in SOURCES.items():
        try:
            print(f"---> {name} tekshirilmoqda...")
            feed = feedparser.parse(url)
            
            for entry in feed.entries[:2]: # Har bir manbadan 2 ta yangilik
                if entry.link in sent_news:
                    continue
                
                print(f"Yangi xabar topildi: {entry.title[:30]}...")
                
                title = entry.title
                description = clean_html(entry.get('description', ''))[:250] + "..."
                img_url = get_image_url(entry)
                
                # CHET EL YANGILIKLARINI TARJIMA QILISH
                if name not in ['Kun.uz', 'Daryo.uz', 'Terabayt.uz']:
                    print("Tarjima qilinmoqda...")
                    try:
                        title_uz = translator.translate(title, dest='uz').text
                        desc_uz = translator.translate(description, dest='uz').text
                        title, description = title_uz, desc_uz
                        print("Tarjima muvaffaqiyatli.")
                    except Exception as e:
                        print(f"Tarjimada kechikish bo'ldi (original tilda yuboriladi): {e}")

                caption = f"📢 **{title}**\n\n📝 {description}\n\n🏛 Manba: **{name}**\n\n✅ @karnayuzb"
                
                # TUGMALAR
                markup = types.InlineKeyboardMarkup(row_width=2)
                markup.add(types.InlineKeyboardButton("📖 To'liq o'qish", url=entry.link))
                markup.add(types.InlineKeyboardButton("👍", callback_data="l"), 
                           types.InlineKeyboardButton("👎", callback_data="d"))

                # TELEGRAMGA YUBORISH
                try:
                    print("Telegramga yuborish urinishi...")
                    if img_url:
                        bot.send_photo(CHANNEL_ID, img_url, caption=caption, parse_mode='Markdown', reply_markup=markup)
                    else:
                        bot.send_message(CHANNEL_ID, caption, parse_mode='Markdown', reply_markup=markup)
                    
                    print("✅ XABAR KANALGA CHIQDI!")
                    sent_news.append(entry.link)
                    if len(sent_news) > 100: sent_news.pop(0)
                    time.sleep(5) 
                except Exception as e:
                    print(f"❌ YUBORISHDA XATO (Adminlikni tekshiring): {e}")

        except Exception as e:
            print(f"❗ Manba bilan ulanishda xato ({name}): {e}")

# ASOSIY QISM
if __name__ == "__main__":
    print("Boshlanmoqda...")
    keep_alive() # Veb-serverni yoqish (Render uchun)
    
    while True:
        try:
            process_news()
            print("Tekshiruv yakunlandi. 10 daqiqa tanaffus.")
            time.sleep(600) # 10 daqiqa kutish
        except Exception as e:
            print(f"Kutilmagan xato: {e}")
            time.sleep(60)
