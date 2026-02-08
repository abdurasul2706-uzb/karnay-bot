import telebot
import feedparser
import time
import urllib.parse
import re
from googletrans import Translator
from telebot import types
from flask import Flask
from threading import Thread

# --- KICHIK VEB-SERVER (Render "Live" bo'lishi uchun) ---
app = Flask('')
@app.route('/')
def home():
    return "Bot is running!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()
# -------------------------------------------------------

TOKEN = '8358476165:AAFsfhih8yADOpXaJa_JCvndQBDUUQZWmds'
CHANNEL_ID = '@karnayuzb'

SOURCES = {
    'BBC World': 'http://feeds.bbci.co.uk/news/world/rss.xml',
    'Al Jazeera': 'https://www.aljazeera.com/xml/rss/all.xml',
    'Kun.uz': 'https://kun.uz/news/rss',
    'Daryo.uz': 'https://daryo.uz/feed/',
    'Terabayt.uz': 'https://www.terabayt.uz/feed',
    'CNN News': 'http://rss.cnn.com/rss/edition_world.rss',
    'Reuters': 'https://www.reutersagency.com/feed/?best-topics=world-news&post_type=best',
    'Championat.asia': 'https://championat.asia/uz/news/rss'
}

bot = telebot.TeleBot(TOKEN)
translator = Translator()
sent_news = set()

def clean_html(raw_html):
    cleanr = re.compile('<.*?>')
    return re.sub(cleanr, '', raw_html)

def get_ai_image(prompt):
    encoded_prompt = urllib.parse.quote(prompt)
    return f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1024&height=768&nologo=true"

def get_image_url(entry):
    if 'links' in entry:
        for link in entry.links:
            if 'image' in link.get('type', '') or 'media' in link.get('rel', ''):
                return link.get('href')
    if 'media_content' in entry:
        return entry.media_content[0]['url']
    return None

def process_news():
    for name, url in SOURCES.items():
        feed = feedparser.parse(url)
        for entry in feed.entries[:3]:
            if entry.link in sent_news:
                continue
            
            title = entry.title
            description = entry.get('description', '')
            description = clean_html(description)[:300] + "..."
            
            img_url = get_image_url(entry)
            is_uzbek = name in ['Kun.uz', 'Daryo.uz', 'Terabayt.uz', 'Championat.asia']

            if not is_uzbek:
                try:
                    title_uz = translator.translate(title, dest='uz').text
                    desc_uz = translator.translate(description, dest='uz').text
                except:
                    title_uz, desc_uz = title, description
            else:
                title_uz, desc_uz = title, description

            if not img_url:
                img_url = get_ai_image(title_uz)

            caption = f"📢 **{title_uz}**\n\n📝 {desc_uz}\n\n🏛 Manba: **{name}**\n\n✅ @karnayuzb"
            
            markup = types.InlineKeyboardMarkup(row_width=2)
            markup.add(types.InlineKeyboardButton("📖 To'liq o'qish", url=entry.link))
            markup.add(types.InlineKeyboardButton("👍", callback_data="like"), 
                       types.InlineKeyboardButton("👎", callback_data="dislike"))
            
            try:
                bot.send_photo(CHANNEL_ID, img_url, caption=caption, parse_mode='Markdown', reply_markup=markup)
                sent_news.add(entry.link)
                if len(sent_news) > 200: sent_news.clear()
                time.sleep(5)
            except:
                continue

            
            if __name__ == "__main__":
                keep_alive()  # <--- Bu yerda 4 ta bo'sh joy bo'lishi shart!
                print("Bot uyg'ondi va ishga tushdi!")
    
                while True:
                    try:
                        print("Yangiliklar tekshirilmoqda...")
                        process_news()
                        print("Tekshiruv tugadi. 5 daqiqa dam olamiz.")
                        time.sleep(300) 
                    except Exception as e:
                        print(f"Xato yuz berdi: {e}")
                        time.sleep(60)

