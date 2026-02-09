import telebot
import feedparser
import time
import urllib.parse
import re
from googletrans import Translator
from telebot import types
from flask import Flask
from threading import Thread

# 1. RENDER BEPUL REJIMDA O'CHIB QOLMASLIGI UCHUN VEB-SERVER
app = Flask('')

@app.route('/')
def home():
    return "Bot is running!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# 2. SOZLAMALAR
TOKEN = '8358476165:AAFsfhih8yADOpXaJa_JCvndQBDUUQZWmds'
CHANNEL_ID = '@karnayuzb'

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
sent_news = [] # Xabarlar takrorlanmasligi uchun

def clean_html(raw_html):
    """HTML teglarni tozalash"""
    cleanr = re.compile('<.*?>')
    return re.sub(cleanr, '', raw_html)

def get_image_url(entry):
    """Rasm havolasini topish"""
    if 'links' in entry:
        for link in entry.links:
            if 'image' in link.get('type', '') or 'media' in link.get('rel', ''):
                return link.get('href')
    if 'media_content' in entry:
        return entry.media_content[0]['url']
    return None

def process_news():
    """Yangiliklarni tekshirish va yuborish"""
    for name, url in SOURCES.items():
        
                              # ... (caption va markup yaratilgan joydan keyin)

                try:
                    print(f"Xabar tayyor, yuborishga urinish: {title}") # LOG UCHUN
                    if img_url:
                        bot.send_photo(CHANNEL_ID, img_url, caption=caption, parse_mode='Markdown', reply_markup=markup)
                    else:
                        bot.send_message(CHANNEL_ID, caption, parse_mode='Markdown', reply_markup=markup)
                    
                    print("MUVAFFAQIYATLI YUBORILDI! ✅") # AGAR BU CHIQSA, TELEGRAMNI TEKSHIRING
                    sent_news.append(entry.link)
                    if len(sent_news) > 100: sent_news.pop(0)
                    time.sleep(5) 
                except Exception as e:
                    print(f"YUBORISHDA XATO: {e}") # AGAR BU CHIQSA, MUAMMONI AYTADI
  
                title = entry.title
                description = clean_html(entry.get('description', ''))[:300] + "..."
                img_url = get_image_url(entry)
                
                # O'zbekcha bo'lmaganlarni tarjima qilish
                if name not in ['Kun.uz', 'Daryo.uz', 'Terabayt.uz']:
                    try:
                        title = translator.translate(title, dest='uz').text
                        description = translator.translate(description, dest='uz').text
                    except:
                        pass

                caption = f"📢 **{title}**\n\n📝 {description}\n\n🏛 Manba: **{name}**\n\n✅ @karnayuzb"
                
                markup = types.InlineKeyboardMarkup(row_width=2)
                btn_read = types.InlineKeyboardButton("📖 To'liq o'qish", url=entry.link)
                btn_like = types.InlineKeyboardButton("👍", callback_data="like")
                btn_dislike = types.InlineKeyboardButton("👎", callback_data="dislike")
                markup.add(btn_read)
                markup.add(btn_like, btn_dislike)

                try:
                    if img_url:
                        bot.send_photo(CHANNEL_ID, img_url, caption=caption, parse_mode='Markdown', reply_markup=markup)
                    else:
                        bot.send_message(CHANNEL_ID, caption, parse_mode='Markdown', reply_markup=markup)
                    
                    sent_news.append(entry.link)
                    if len(sent_news) > 100: sent_news.pop(0)
                    time.sleep(5) # Telegram bloklamasligi uchun
                except Exception as e:
                    print(f"Yuborishda xato: {e}")
        except Exception as e:
            print(f"Manbada xato: {e}")

# 3. ASOSIY ISHGA TUSHIRISH QISMI (XATOSIZ INDENTATION)
if __name__ == "__main__":
    keep_alive() # Veb-serverni yoqish
    print("Bot uyg'ondi!")
    
    while True:
        process_news()
        print("Tekshiruv tugadi. 10 daqiqa dam olamiz.")
        time.sleep(600) # 10 daqiqa kutish
