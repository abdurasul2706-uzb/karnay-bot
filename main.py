import telebot
import feedparser
import time
import requests
import re
from bs4 import BeautifulSoup
from googletrans import Translator
from flask import Flask
from threading import Thread

# 1. RENDER SERVER (Uyg'oq saqlash uchun)
app = Flask('')
@app.route('/')
def home(): return "Bot is running!"
def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run).start()

# 2. SOZLAMALAR
TOKEN = '8358476165:AAFsfhih8yWO0pXaJa_JCvndQ8DUUQZWads'
CHANNEL_ID = '@karnayuzb'

# 50 ta nufuzli manbalar ro'yxati
SOURCES = {
    # O'zbekiston
    'Kun.uz': 'https://kun.uz/news/rss',
    'Daryo.uz': 'https://daryo.uz/feed/',
    'Gazeta.uz': 'https://www.gazeta.uz/uz/rss/',
    'Qalampir.uz': 'https://qalampir.uz/uz/rss',
    'Terabayt.uz': 'https://www.terabayt.uz/feed',
    'BBC O‘zbek': 'https://www.bbc.com/uzbek/index.xml',
    'Xabar.uz': 'https://xabar.uz/uz/rss',
    
    # Jahon (Ingliz tilidagi manbalar)
    'Reuters': 'https://www.reutersagency.com/feed/?best-topics=world-news&post_type=best',
    'BBC World': 'http://feeds.bbci.co.uk/news/world/rss.xml',
    'Al Jazeera': 'https://www.aljazeera.com/xml/rss/all.xml',
    'The New York Times': 'https://rss.nytimes.com/services/xml/rss/nyt/World.xml',
    'The Guardian': 'https://www.theguardian.com/world/rss',
    'The Washington Post': 'https://feeds.washingtonpost.com/rss/world',
    'CNN News': 'http://rss.cnn.com/rss/edition_world.rss',
    'Associated Press': 'https://newsatme.com/go/ap/world',
    'Forbes': 'https://www.forbes.com/real-time/feed2/',
    'Bloomberg': 'https://www.bloomberg.com/politics/feeds/site.xml',
    'TechCrunch': 'https://techcrunch.com/feed/',
    'The Verge': 'https://www.theverge.com/rss/index.xml',
    'Wired': 'https://www.wired.com/feed/rss',
    'NASA News': 'https://www.nasa.gov/rss/dyn/breaking_news.rss',
    'National Geographic': 'https://www.nationalgeographic.com/index.rss',
    'The Economist': 'https://www.economist.com/sections/world/rss.xml',
    'Wall Street Journal': 'https://feeds.a.dj.com/rss/RSSWorldNews.xml',
    'CNBC World': 'https://www.cnbc.com/id/100727338/device/rss/rss.html',
    'Euronews': 'https://www.euronews.com/rss?level=vertical&name=news',
    'France24': 'https://www.france24.com/en/rss',
    'Deutsche Welle': 'https://rss.dw.com/xml/rss-en-all',
    'Engadget': 'https://www.engadget.com/rss.xml',
    'Gizmodo': 'https://gizmodo.com/rss',
    'Scientific American': 'https://www.scientificamerican.com/section/all/rss/',
    'Nature News': 'https://www.nature.com/nature.rss',
    'Harvard Business Review': 'https://hbr.org/rss/hbr.xml',
    'Sky News': 'https://news.sky.com/feeds/rss/world.xml',
    'Fox News': 'https://feeds.foxnews.com/foxnews/world',
    'Independent': 'https://www.independent.co.uk/news/world/rss',
    'Daily Mail': 'https://www.dailymail.co.uk/news/worldnews/index.rss',
    'ABC News': 'https://abcnews.go.com/abcnews/internationalheadlines',
    'CBS News': 'https://www.cbsnews.com/latest/rss/world',
    'TASS (En)': 'https://tass.com/rss/v2.xml',
    'Interfax': 'https://interfax.com/news/rss/',
    'Anadolu Agency': 'https://www.aa.com.tr/en/rss/default?cat=world',
    'Nikkei Asia': 'https://asia.nikkei.com/rss/feed/nar',
    'SCMP News': 'https://www.scmp.com/rss/91/feed.xml',
    'Al Arabiya': 'https://english.alarabiya.net/.mrss/en/news.xml',
    'Politico': 'https://www.politico.com/rss/politicopicks.xml',
    'The Verge Tech': 'https://www.theverge.com/tech/rss/index.xml',
    'The Times of India': 'https://timesofindia.indiatimes.com/rssfeeds/296589292.cms'
}

bot = telebot.TeleBot(TOKEN)
translator = Translator()
SENT_NEWS_CACHE = set()

def clean_and_shorten(text, limit=850):
    """Matnni tozalaydi va rasm ostiga sig'adigan qilib mantiqiy qisqartiradi"""
    patterns = [r'.*?cookies.*?(\.|\!)', r'.*?davom etish.*?(\.|\!)', r'.*?rozilik.*?(\.|\!)']
    for p in patterns:
        text = re.sub(p, '', text, flags=re.IGNORECASE | re.DOTALL)
    
    text
