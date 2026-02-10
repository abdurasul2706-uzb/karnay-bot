import telebot
import feedparser
import time
import requests
import re
from bs4 import BeautifulSoup
from googletrans import Translator
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

# 50 ta manba (O'zbekiston va Dunyo)
SOURCES = {
    'Kun.uz': 'https://kun.uz/news/rss',
    'Daryo.uz': 'https://daryo.uz/feed/',
    'Gazeta.uz': 'https://www.gazeta.uz/uz/rss/',
    'Qalampir.uz': 'https://qalampir.uz/uz/rss',
    'Terabayt.uz': 'https://www.terabayt.uz/feed',
    'BBC O‘zbek': 'https://www.bbc.com/uzbek/index.xml',
    'Reuters (World)': 'https://www.reutersagency.com/feed/?best-topics=world-news&post_type=best',
    'Al Jazeera': 'https://www.aljazeera.com/xml/rss/all.xml',
    'The New York Times': 'https://rss.nytimes.com/services/xml/rss/nyt/World.xml',
    'The Wall Street Journal': 'https://feeds.a.dj.com/rss/RSSWorldNews.xml',
    'The Washington Post': 'https://feeds.washingtonpost.com/rss/world',
    'CNN International': 'http://rss.cnn.com/rss/edition_world.rss',
    'Associated Press (AP)': 'https://newsatme.com/go/ap/world',
    'The Guardian': 'https://www.theguardian.com/world/rss',
    'Bloomberg': 'https://www.bloomberg.com/politics/feeds/site.xml',
    'Forbes': 'https://www.forbes.com/real-time/feed2/',
    'National Geographic': 'https://www.nationalgeographic.com/index.rss',
    'Nature': 'https://www.nature.com/nature.rss',
    'NASA News': 'https://www.nasa.gov/rss/dyn/breaking_news.rss',
    'TechCrunch': 'https://techcrunch.com/feed/',
    'The Verge': 'https://www.theverge.com/rss/index.xml',
    'Wired': 'https://www.wired.com/feed/rss',
    'Harvard Business Review': 'https://hbr.org/rss/hbr.xml',
    'Euronews': 'https://www.euronews.com/rss?level=vertical&name=news',
    'France24': 'https://www.france24.com/en/rss',
    'Deutsche Welle (DW)': 'https://rss.dw.com/xml/rss-en-all',
    'CNET': 'https://www.cnet.com/rss/news/',
    'Engadget': 'https://www.engadget.com/rss.xml',
    'Gizmodo': 'https://gizmodo.com/rss',
    'Scientific American': 'https://www.scientificamerican.com/section/all/rss/',
    'The Economist': 'https://www.economist.com/sections/world/rss.xml',
    'Independent': 'https://www.independent.co.uk/news/world/rss',
    'Daily Mail': 'https://www.dailymail.co.uk/news/worldnews/index.rss',
    'Sky News': 'https://news.sky.com/feeds/rss/world.xml',
    'Fox News': 'https://feeds.foxnews.com/foxnews/world',
    'ABC News': 'https://abcnews.go.com/abcnews/internationalheadlines',
    'CBS News': 'https://www.cbsnews.com/latest/rss/world',
    'Nikkei Asia': 'https://asia.nikkei.com/rss/feed/nar',
    'South China Morning Post': 'https://www.scmp.com/rss/91/feed.xml',
    'Al Arabiya': 'https://english.alarabiya.net/.mrss/en/news.xml',
    'TASS (English)': 'https://tass.com/rss/v2.xml',
    'Interfax (English)': 'https://interfax.com/news/rss/',
    'Anadolu Agency': 'https://www.aa.com.tr/en/rss/default?cat=world',
    'Haaretz': 'https://www.haaretz.com/cmlink/1.4623547',
    'The Times of India': 'https://timesofindia.indiatimes.com/rssfeeds/296589292.cms',
    'Politico': 'https://www.politico.com/rss/politicopicks.xml'
}

bot = telebot.TeleBot(TOKEN)
translator = Translator()
SENT_NEWS_CACHE = set()

def clean_text(text):
    """Cookie, reklama va ortiqcha gaplarni tozalash"""
    patterns = [
        r'.*?cookies-fayllardan.*?(\.|\!)',
        r'.*?davom etish orqali.*?(\.|\!)',
        r'.*?rozilik bildirasiz.*?(\.|\!)',
        r'.*?Maxfiylik siyosati.*?(\.|\!)',
        r'.*?cookies.*?(\.|\!)',
    ]
    for pattern in patterns:
        text = re.sub(pattern, '', text, flags=re.IGNORECASE | re.DOTALL)
    return text.strip()

def get_full_content(url):
    """Sayt ichiga kirib, butun matnni yig'ish"""
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.content, 'html.parser')
        
        # Rasm
        img = soup.find("meta", property="og:image")
        img_url = img['content'] if img else None
        
        # Matn yig'ish
        paras = soup.find_all('p')
        text_list = []
        for p in paras:
            p_text = p.get_text().strip()
            if len(p_text) > 60:
                text_list.append(p_text)
        
        return img_url, "\n\n".join(text_list)
    except:
        return None, ""

def process_news():
    for name, url in SOURCES.items():
        try:
            print(f"---> {name} tekshirilmoqda...")
            feed = feedparser.parse(url)
            
            for entry in feed.entries[:1]: # Har safar faqat eng yangisini
                if entry.link in SENT_NEWS_CACHE: continue
                
                img_url, full_text = get_full_content(entry.link)
                title = entry.title
                
                # Agar matn yo'q bo'lsa RSS tavsifini olish
                text = full_text if len(full_text) > 100 else entry.get('summary', '')
                text = clean_text(BeautifulSoup(text, "html.parser").get_text())

                # DUNYO YANGILIKLARINI TARJIMA QILISH
                if name not in ['Kun.uz', 'Daryo.uz', 'Gazeta.uz', 'Qalampir.uz', 'Terabayt.uz']:
                    try:
                        title = translator.translate(title, dest='uz').text
                        # Tarjima 3000 belgidan oshmasligi kerak
                        text = translator.translate(text[:3000], dest='uz').text
                    except: pass

                # XABARNI TAYYORLASH
                header = f"🏛 **{name.upper()}**\n🔥 **{title}**\n\n"
                footer = f"\n\n📢 @karnayuzb — Dunyo yangiliklari\n#dunyo #{name.replace(' ', '')}"

                # AGAR MATN JUDA UZUN BO'LSA (TELEGRAM LIMITI 4096)
                total_message = header + text + footer
                
                try:
                    if img_url:
                        # Rasm bilan birga (Limit 1024)
                        if len(total_message) < 1000:
                            bot.send_photo(CHANNEL_ID, img_url, caption=total_message, parse_mode='Markdown')
                        else:
                            # Rasm alohida, matn alohida (To'liq chiqishi uchun)
                            bot.send_photo(CHANNEL_ID, img_url)
                            # Matnni 4000 belgilik bo'laklarga bo'lib yuborish
                            for i in range(0, len(total_message), 4000):
                                bot.send_message(CHANNEL_ID, total_message[i:i+4000], parse_mode='Markdown')
                    else:
                        for i in range(0, len(total_message), 4000):
                            bot.send_message(CHANNEL_ID, total_message[i:i+4000], parse_mode='Markdown')
                    
                    SENT_NEWS_CACHE.add(entry.link)
                    print(f"✅ Yuborildi: {name}")
                    time.sleep(2) # Tezkor yuborish uchun kamaytirildi
                except Exception as e:
                    print(f"Yuborishda xato: {e}")
        except: continue

if __name__ == "__main__":
    keep_alive()
    while True:
        process_news()
        time.sleep(60) # Har daqiqada yangi manbalarni tekshirish
