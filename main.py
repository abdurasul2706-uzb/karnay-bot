import telebot
import feedparser
import time
from googletrans import Translator

# SOZLAMALAR
TOKEN = '8358476165:AAFsfhih8yWO0pXaJa_JCvndQ8DUUQZWads' 
CHANNEL_ID = '@karnayuzb'
SOURCES = [
    'http://feeds.bbci.co.uk/news/world/rss.xml',
    'https://www.aljazeera.com/xml/rss/all.xml'
]

bot = telebot.TeleBot(TOKEN)
translator = Translator()

def get_news():
    print("Yangiliklar tekshirilmoqda...")
    for url in SOURCES:
        feed = feedparser.parse(url)
        if feed.entries:
            entry = feed.entries[0]
            title = entry.title
            link = entry.link
            
            try:
                uz_title = translator.translate(title, dest='uz').text
                text = f"📢 **{uz_title}**\n\n🔗 Manba: {link}\n\n✅ @karnayuzb"
                bot.send_message(CHANNEL_ID, text, parse_mode='Markdown')
                print(f"Post jo'natildi: {uz_title}")
            except Exception as e:
                print(f"Tarjima yoki jo'natishda xato: {e}")
            
            time.sleep(5)

if __name__ == "__main__":
    while True:
        try:
            get_news()
            time.sleep(1800) # 30 daqiqa kutish
        except Exception as e:
            print(f"Global xato: {e}")
            time.sleep(60)
