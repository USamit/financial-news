#!/usr/bin/env python3
import os
from datetime import datetime, timedelta
import feedparser
import requests
from collections import defaultdict

BOT_TOKEN = os.getenv(‘TELEGRAM_BOT_TOKEN’)
CHAT_ID = os.getenv(‘TELEGRAM_CHAT_ID’)

FEEDS = {
‘Economic Times’: ‘https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms’,
‘Mint’: ‘https://www.livemint.com/rss/markets’,
‘Reuters’: ‘https://www.reutersagency.com/feed/?taxonomy=best-sectors&post_type=best’
}

KEYWORDS = [‘bank’, ‘banking’, ‘financial’, ‘fintech’, ‘credit’, ‘loan’, ‘deposit’, ‘rbi’, ‘federal reserve’, ‘central bank’, ‘payment’]

def is_relevant(title, description):
text = (title + ’ ’ + description).lower()
return any(keyword in text for keyword in KEYWORDS)

def fetch_news():
print(‘Fetching financial news…’)
articles = []
for source, url in FEEDS.items():
try:
feed = feedparser.parse(url)
for entry in feed.entries[:20]:
pub_date = None
if hasattr(entry, ‘published_parsed’):
pub_date = datetime(*entry.published_parsed[:6])
if pub_date and (datetime.now() - pub_date) > timedelta(days=1):
continue
title = entry.get(‘title’, ‘’)
description = entry.get(‘summary’, ‘’) or entry.get(‘description’, ‘’)
if not is_relevant(title, description):
continue
articles.append({
‘source’: source,
‘title’: title,
‘url’: entry.get(‘link’, ‘’),
‘time’: pub_date.strftime(’%H:%M’) if pub_date else ‘Recent’
})
print(f’  Got {len([a for a in articles if a[“source”] == source])} from {source}’)
except Exception as e:
print(f’  Error from {source}: {e}’)
return articles

def format_message(articles):
if not articles:
return f’Financial News Digest\n{datetime.now().strftime(”%B %d, %Y”)}\n\nNo relevant articles found today.’
by_source = defaultdict(list)
for article in articles:
by_source[article[‘source’]].append(article)
msg = f’*Financial News Digest*\n{datetime.now().strftime(”%B %d, %Y”)}\n\n’
msg += f’{len(articles)} articles from {len(by_source)} sources\n\n’
for source in sorted(by_source.keys()):
source_articles = by_source[source][:5]
msg += f’*{source}* ({len(source_articles)})\n’
for i, article in enumerate(source_articles, 1):
msg += f’\n{i}. [{article[“title”]}]({article["url"]})\n’
msg += f’   {article[“time”]}\n’
msg += ‘\n’
return msg

def send_telegram(message):
if not BOT_TOKEN or not CHAT_ID:
print(‘ERROR: Bot token or chat ID not set!’)
return False
url = f’https://api.telegram.org/bot{BOT_TOKEN}/sendMessage’
data = {‘chat_id’: CHAT_ID, ‘text’: message, ‘parse_mode’: ‘Markdown’, ‘disable_web_page_preview’: False}
try:
print(‘Sending to Telegram…’)
response = requests.post(url, json=data, timeout=10)
response.raise_for_status()
print(‘Message sent!’)
return True
except Exception as e:
print(f’Error: {e}’)
return False

def main():
print(’=’*50)
print(‘Financial News Aggregator’)
print(’=’*50)
articles = fetch_news()
print(f’\nFound {len(articles)} articles’)
message = format_message(articles)
send_telegram(message)
print(’\nDone!’)

if **name** == ‘**main**’:
main()
