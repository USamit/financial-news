import os
from datetime import datetime, timedelta
import feedparser
import requests
from collections import defaultdict

token = os.getenv('TELEGRAM_BOT_TOKEN')
chat = os.getenv('TELEGRAM_CHAT_ID')

print('Fetching financial news...')

feeds = {
    'Economic Times - Markets': 'https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms',
    'Economic Times - Banking': 'https://economictimes.indiatimes.com/industry/banking/finance/rssfeeds/13358259.cms',
    'Economic Times - Finance': 'https://economictimes.indiatimes.com/industry/banking/finance/banking/rssfeeds/13358256.cms',
    'Mint - Markets': 'https://www.livemint.com/rss/markets',
    'Mint - Money': 'https://www.livemint.com/rss/money',
    'Mint - Banking': 'https://www.livemint.com/rss/industry/banking',
    'Financial Times - Markets': 'https://www.ft.com/markets?format=rss',
    'Financial Times - Banking': 'https://www.ft.com/companies/financials?format=rss',
    'WSJ - Markets': 'https://feeds.content.dowjones.io/public/rss/RSSMarketsMain',
    'WSJ - Finance': 'https://feeds.content.dowjones.io/public/rss/WSJcomUSBusiness',
    'Barrons - Markets': 'https://www.barrons.com/rss',
    'Reuters - Business': 'https://www.reutersagency.com/feed/?best-topics=business-finance&post_type=best',
    'MoneyControl': 'https://www.moneycontrol.com/rss/business.xml',
    'MoneyControl - Banking': 'https://www.moneycontrol.com/rss/marketedge.xml',
    'Financial Express': 'https://www.financialexpress.com/market/rss',
    'Hindu BusinessLine': 'https://www.thehindubusinessline.com/economy/?service=rss',
    'Hindu BL - Banking': 'https://www.thehindubusinessline.com/economy/banking/?service=rss',
    'CNBC Finance': 'https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10000664',
    'Bloomberg Markets': 'https://feeds.bloomberg.com/markets/news.rss',
    'Forbes Finance': 'https://www.forbes.com/finance/feed/'
}

keywords = ['bank', 'banking', 'financial', 'fintech', 'credit', 'loan', 
            'rbi', 'central bank', 'payment', 'deposit', 'sebi', 
            'investment', 'finance', 'monetary', 'fiscal', 'npa',
            'fed', 'federal reserve', 'interest rate', 'bond', 'treasury']

articles = []

for source, url in feeds.items():
    try:
        print('Fetching from ' + source + '...')
        feed = feedparser.parse(url)
        source_count = 0
        
        for entry in feed.entries[:30]:
            pub_date = None
            if hasattr(entry, 'published_parsed'):
                pub_date = datetime(*entry.published_parsed[:6])
            elif hasattr(entry, 'updated_parsed'):
                pub_date = datetime(*entry.updated_parsed[:6])
            
            if pub_date and (datetime.now() - pub_date) > timedelta(days=3):
                continue
            
            title = entry.get('title', '')
            description = entry.get('summary', '') or entry.get('description', '')
            link = entry.get('link', '')
            
            text = (title + ' ' + description).lower()
            if any(kw in text for kw in keywords):
                time_str = pub_date.strftime('%H:%M') if pub_date else 'Recent'
                articles.append({
                    'source': source,
                    'title': title,
                    'url': link,
                    'time': time_str
                })
                source_count = source_count + 1
                if source_count >= 8:
                    break
        
        print('  Got ' + str(source_count) + ' articles')
    except Exception as e:
        print('  Error: ' + str(e))

print('\nTotal articles found: ' + str(len(articles)))

if not articles:
    msg = 'Financial News Digest\n' + datetime.now().strftime('%B %d, %Y') + '\n\nNo relevant articles found.'
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
            title_short = article['title']
            if len(title_short) > 100:
                title_short = title_short[:97] + '...'
            msg = msg + str(i) + '. [' + title_short + '](' + article['url'] + ')\n'
        msg = msg + '\n'

if token and chat:
    url = 'https://api.telegram.org/bot' + token + '/sendMessage'
    data = {'chat_id': chat, 'text': msg, 'parse_mode': 'Markdown', 'disable_web_page_preview': True}
    response = requests.post(url, json=data, timeout=10)
    if response.status_code == 200:
        print('Sent to Telegram!')
    else:
        print('Error: ' + str(response.status_code))
        print(response.text)
else:
    print('No token or chat ID')
