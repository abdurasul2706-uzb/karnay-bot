import telebot
import feedparser
import time
import re
import urllib.parse
from googletrans import Translator
from telebot import types

# SOZLAMALAR
TOKEN = '8358476165:AAFsfhih8yWO0pXaJa_JCvndQ8DUUQZWads' 
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

def get_ai_image(prompt):
    """Agar rasm bo'lmasa, AI orqali rasm yasash (Tekin)"""
    encoded_prompt = urllib.parse.quote(prompt)
    return f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1024&height=768&nologo=true"

def get_image_url(entry):
    """Rasm havolasini qidirish"""
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
        for entry in feed.entries[:5]:
            if entry.link in sent_news:
                continue
            
            title = entry.title
            img_url = get_image_url(entry)
            
            # Tarjima qilish
            is_uzbek = name in ['Kun.uz', 'Daryo.uz', 'Terabayt.uz', 'Championat.asia']
            if not is_uzbek:
                try:
                    title_uz = translator.translate(title, dest='uz').text
                except:
                    title_uz = title
            else:
                title_uz = title

            # AI rasm yasash (agar rasm yo'q bo'lsa)
            if not img_url:
                img_url = get_ai_image(title)

            # MATN: Havola yo'q, faqat sayt nomi
            caption = f"📢 **{title_uz}**\n\n🏛 Manba: **{name}**\n\n✅ @karnayuzb"
            
            # TUGMA
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("📖 Batafsil o'qish", url=entry.link))
            
            try:
                bot.send_photo(CHANNEL_ID, img_url, caption=caption, parse_mode='Markdown', reply_markup=markup)
                sent_news.add(entry.link)
                if len(sent_news) > 200: sent_news.clear()
                time.sleep(5)
            except:
                continue

def send_daily_info():
    """Valyuta va Ob-havo (Soddalashtirilgan ko'rinishda)"""
    text = "🌤 **Xayrli tong! Bugungi ma'lumotlar:**\n\n"
    text += "💵 USD: 12 950 so'm\n" # Buni API orqali ham qilish mumkin
    text += "🌍 Toshkent: +12°C, Ochiq havo\n\n"
    text += "✅ @karnayuzb - Karnay kabi yangraymiz!"
    bot.send_message(CHANNEL_ID, text, parse_mode='Markdown')

if __name__ == "__main__":
    print("Bot ishga tushdi...")
    # Kunlik ma'lumotni bot yoqilganda bir marta yuboradi
    send_daily_info() 
    while True:
        try:
            process_news()
            time.sleep(600) # 10 daqiqa
        except Exception as e:
            print(f"Xato: {e}")
            time.sleep(60)
