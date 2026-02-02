#!/usr/bin/env python3
import os
from datetime import datetime, timedelta
import feedparser
import requests
from collections import defaultdict

BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

FEEDS = {
    'Economic Times': 'https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms',
    'Mint': 'https://www.livemint.com/rss/markets',
    'Reuters': 'https://www.reutersagency.com/feed/?taxonomy=best-sectors&post_type=best'
}

KEYWORDS = ['bank', 'banking', 'financial', 'fintech', 'credit', 'loan', 'deposit', 'rbi', 'federal reserve', 'central bank', 'payment']

def is_relevant(title, description):
    text = (title + ' ' + description).lower()
    return any(keyword in text for keyword in KEYWORDS)

def fetch_news():
    print('Fetching financial news...')
    articles = []
    for source, url in FEEDS.items():
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:20]:
                pub_date = None
                if hasattr(entry, 'published_parsed'):
                    pub_date = datetime(*entry.published_parsed[:6])
                if pub_date and (datetime.now() - pub_date) > timedelta(days=1):
                    continue
                title = entry.get('title', '')
                description = entry.get('summary', '') or entry.get('description', '')
                if not is_relevant(title, description):
                    continue
                articles.append({
                    'source': source,
                    'title': title,
                    'url': entry.get('link', ''),
                    'time': pub_date.strftime('%H:%M') if pub_date else 'Recent'
                })
            print(f'  Got {len([a for a in articles if a["source"] == source])} from {source}')
        except Exception as e:
            print(f'  Error from {source}: {e}')
    return articles

def format_message(articles):
    if not articles:
        return f'Financial News​​​​​​​​​​​​​​​​
