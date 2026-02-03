import os
from datetime import datetime, timedelta
import feedparser
import requests
from collections import defaultdict

token = os.getenv('TELEGRAM_BOT_TOKEN')
chat = os.getenv('TELEGRAM_CHAT_ID')

print('Fetching financial news...')

feeds = {
    'Economic Times': 'https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms',
    'Mint': 'https://www.livemint.com/rss/markets',
    'Reuters': 'https://www.reutersagency.com/feed/?taxonomy=best-sectors&post_type=best'
}

keywords = ['bank', 'banking', 'financial', 'fintech', 'credit', 'loan', 'rbi', 'central bank', 'payment', 'deposit']

articles = []

for source, url in feeds.items():
    try:
        feed = feedparser.parse(url)
        for entry in feed.entries[:20]:
            pub_date = None
            if hasattr(entry, 'published_parsed'):
                pub_date = datetime(*entry.published_parsed[:6])
            
            if pub_date and (datetime.now() - pub_date) > timedelta(days=1):
                continue
            
            title = entry.get('title', '')
            link = entry.get('link', '')
            
            if any(kw in title.lower() for kw in keywords):
                time_str = pub_date.strftime('%H:%M') if pub_date else 'Recent'
                articles.append({
                    'source': source,
                    'title': title,
                    'url': link,
                    'time': time_str
                })
        print('Got ' + str(len([a for a in articles if a['source'] == source])) + ' from ' + source)
    except Exception as e:
        print('Error from ' + source + ': ' + str(e))

if not articles:
    msg = 'Financial News Digest\n' + datetime.now().strftime('%B %d, %Y') + '\n\nNo relevant articles found today.'
else:
    by_source = defaultdict(list)
    for article in articles:
        by_source[article['source']].append(article)
    
    msg = '*Financial News Digest*\n' + datetime.now().strftime('%B %d, %Y') + '\n\n'
    msg = msg + str(len(articles)) + ' articles from ' + str(len(by_source)) + ' sources\n\n'
    
    for source in sorted(by_source.keys()):
        items = by_source[source][:5]
        msg = msg + '*' + source + '*\n'
        for i, article in enumerate(items, 1):
            msg = msg + str(i) + '. [' + article['title'] + '](' + article['url'] + ')\n'
            msg = msg + '   ' + article['time'] + '\n\n'

if token and chat:
    url = 'https://api.telegram.org/bot' + token + '/send​​​​​​​​​​​​​​​​
