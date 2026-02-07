import telebot
import feedparser
import time
from googletrans import Translator

# SOZLAMALAR
TOKEN = '8358476165:AAFsfhih8yWO0pXaJa_JCvndQ8DUUQZWads' 
CHANNEL_ID = '@karnayuzb'
SOURCES = [
    'http://feeds.bbci.co.uk/news/world/rss.xml',
    'https://www.reutersagency.com/feed/',
    'https://www.aljazeera.com/xml/rss/all.xml'
]

bot = telebot.TeleBot(TOKEN)
translator = Translator()

def get_news():
    for url in SOURCES:
        feed = feedparser.parse(url)
        for entry in feed.entries[:1]: # Eng so'nggi 1ta xabarni oladi
            title = entry.title
            link = entry.link
            
            # Tarjima qilish
            uz_title = translator.translate(title, dest='uz').text
            
            text = f"📢 **{uz_title}**\n\n🔗 Manba: {link}\n\n✅ @karnayuzb"
            
            bot.send_message(CHANNEL_ID, text, parse_mode='Markdown')
            time.sleep(5) # Telegram bloklamasligi uchun

if __name__ == "__main__":
    while True:
        try:
            get_news()
            time.sleep(1800) # Har 30 daqiqada yangilik qidiradi
        except:
            time.sleep(60)
