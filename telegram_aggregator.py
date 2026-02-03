import os
import feedparser
import requests

token = os.getenv('TELEGRAM_BOT_TOKEN')
chat = os.getenv('TELEGRAM_CHAT_ID')

articles = []
feed = feedparser.parse('https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms')

for entry in feed.entries[:10]:
    title = entry.get('title', '')
    if 'bank' in title.lower():
        articles.append(title)

msg = 'Financial News:\n\n'
for i, title in enumerate(articles, 1):
    msg = msg + str(i) + '. ' + title + '\n'

if token and chat:
    url = 'https://api.telegram.org/bot' + token + '/sendMessage'
    requests.post(url, json={'chat_id': chat, 'text': msg})
    print('Sent to Telegram!')
else:
    print('No token/chat ID')
