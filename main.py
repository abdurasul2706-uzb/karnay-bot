import telebot
import feedparser
import time
from googletrans import Translator

# SOZLAMALAR
TOKEN = '8358476165:AAFsfhih8yWO0pXaJa_JCvndQ8DUUQZWads' 
CHANNEL_ID = '@karnayuzb'

# Manbalar ro'yxati (RSS)
SOURCES = {
    'BBC World': 'http://feeds.bbci.co.uk/news/world/rss.xml',
    'Al Jazeera': 'https://www.aljazeera.com/xml/rss/all.xml',
    'Kun.uz': 'https://kun.uz/news/rss', # O'zbekcha manba
    'Daryo.uz': 'https://daryo.uz/feed/', # O'zbekcha manba
    'Reuters': 'https://www.reutersagency.com/feed/?best-topics=world-news&post_type=best',
}

bot = telebot.TeleBot(TOKEN)
translator = Translator()
sent_news = [] # Bir xil yangilikni qayta tashlamaslik uchun

def get_image_url(entry):
    """Yangilik ichidan rasm havolasini topish"""
    if 'links' in entry:
        for link in entry.links:
            if 'image' in link.get('type', '') or 'media' in link.get('rel', ''):
                return link.get('href')
    if 'media_content' in entry:
        return entry.media_content[0]['url']
    return None

def process_news():
    for name, url in SOURCES.items():
        print(f"{name} tekshirilmoqda...")
        feed = feedparser.parse(url)
        
        for entry in feed.entries[:3]: # Har bir manbadan oxirgi 3 ta yangilik
            if entry.link in sent_news:
                continue
            
            title = entry.title
            link = entry.link
            img_url = get_image_url(entry)
            
            # Agar manba o'zbekcha bo'lmasa, tarjima qilish
            if name not in ['Kun.uz', 'Daryo.uz']:
                try:
                    title = translator.translate(title, dest='uz').text
                except:
                    pass
            
            caption = f"📢 **{title}**\n\n📌 Manba: {name}\n🔗 {link}\n\n✅ @karnayuzb"
            
            try:
                if img_url:
                    bot.send_photo(CHANNEL_ID, img_url, caption=caption, parse_mode='Markdown')
                else:
                    bot.send_message(CHANNEL_ID, caption, parse_mode='Markdown', disable_web_page_preview=False)
                
                sent_news.append(entry.link)
                if len(sent_news) > 100: sent_news.pop(0) # Ro'yxatni tozalab turish
                time.sleep(5) # Telegram bloklamasligi uchun
            except Exception as e:
                print(f"Xato: {e}")

if __name__ == "__main__":
    while True:
        process_news()
        time.sleep(1800) # 30 daqiqa kutish
