import telebot
import feedparser
import time
from googletrans import Translator
from telebot import types

# SOZLAMALAR
TOKEN = '8358476165:AAFsfhih8yWO0pXaJa_JCvndQ8DUUQZWads' 
CHANNEL_ID = '@karnayuzb'

# MANBALAR RO'YXATI (Kanal rivoji uchun ko'paytirildi)
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
sent_news = set() # Takrorlanishni oldini olish uchun "xotira"

def get_image_url(entry):
    """Rasm havolasini qidirish"""
    if 'links' in entry:
        for link in entry.links:
            if 'image' in link.get('type', '') or 'media' in link.get('rel', ''):
                return link.get('href')
    if 'media_content' in entry:
        return entry.media_content[0]['url']
    if 'description' in entry and '<img' in entry.description:
        import re
        img_src = re.search(r'<img src="([^"]+)"', entry.description)
        if img_src: return img_src.group(1)
    return None

def process_news():
    for name, url in SOURCES.items():
        print(f"{name} tekshirilmoqda...")
        feed = feedparser.parse(url)
        
        for entry in feed.entries[:5]: # Oxirgi 5 ta yangilik
            # Takrorlanishni tekshirish (Link orqali)
            if entry.link in sent_news:
                continue
            
            title = entry.title
            img_url = get_image_url(entry)
            
            # Faqat xorijiy manbalarni tarjima qilish
            if name not in ['Kun.uz', 'Daryo.uz', 'Terabayt.uz', 'Championat.asia']:
                try:
                    title = translator.translate(title, dest='uz').text
                except:
                    pass
            
            # MATN DIZAYNI (Havolasiz, faqat sayt nomi)
            caption = f"📢 **{title}**\n\n🏛 Manba: **{name}**\n\n✅ @karnayuzb"
            
            # TUGMA (Havolani tugma ichiga yashiramiz)
            markup = types.InlineKeyboardMarkup()
            btn_read = types.InlineKeyboardButton("📖 Batafsil o'qish", url=entry.link)
            markup.add(btn_read)
            
            try:
                if img_url:
                    bot.send_photo(CHANNEL_ID, img_url, caption=caption, parse_mode='Markdown', reply_markup=markup)
                else:
                    bot.send_message(CHANNEL_ID, caption, parse_mode='Markdown', reply_markup=markup)
                
                # Xotiraga saqlash
                sent_news.add(entry.link)
                # Xotira juda kattalashib ketmasligi uchun
                if len(sent_news) > 200:
                    sent_news.clear()
                    
                time.sleep(3) # Telegram chekloviga tushmaslik uchun
            except Exception as e:
                print(f"Xato yuz berdi: {e}")

if __name__ == "__main__":
    print("Bot ishga tushdi...")
    while True:
        try:
            process_news()
            time.sleep(600) # 10 daqiqa kutish (Tezkorlik uchun)
        except Exception as e:
            print(f"Global xato: {e}")
            time.sleep(60)
