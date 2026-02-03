import os
from datetime import datetime, timedelta
import feedparser
import requests
from collections import defaultdict

token = os.getenv('TELEGRAM_BOT_TOKEN')
chat = os.getenv('TELEGRAM_CHAT_ID')

print('Starting Financial News Aggregator...')
print('Token present: ' + str(bool(token)))
print('Chat ID present: ' + str(bool(chat)))

feeds = {
    # Economic Times - Verified Working
    'ET Markets': 'https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms',
    'ET Banking': 'https://economictimes.indiatimes.com/industry/banking/finance/banking/rssfeeds/13358256.cms',
    'ET Finance': 'https://economictimes.indiatimes.com/industry/banking/finance/rssfeeds/13358259.cms',
    'ET Insurance': 'https://economictimes.indiatimes.com/industry/banking/finance/insure/rssfeeds/13358276.cms',
    'ET Stocks': 'https://economictimes.indiatimes.com/markets/stocks/rssfeeds/2146842.cms',
    
    # Mint - Verified Working
    'Mint Markets': 'https://www.livemint.com/rss/markets',
    'Mint Money': 'https://www.livemint.com/rss/money',
    'Mint Banking': 'https://www.livemint.com/rss/industry/banking',
    'Mint Companies': 'https://www.livemint.com/rss/companies',
    
    # MoneyControl - Verified Working
    'MC Business': 'https://www.moneycontrol.com/rss/business.xml',
    'MC Markets': 'https://www.moneycontrol.com/rss/latestnews.xml'
}

keywords = [
    'bank', 'banking', 'financial', 'finance', 'fintech', 'credit', 'loan',
    'payment', 'upi', 'market', 'stock', 'equity', 'invest', 'insurance',
    'rbi', 'sebi', 'deposit', 'nifty', 'sensex', 'ipo', 'mutual fund'
]

articles = []
total_fetched = 0

for source, url in feeds.items():
    try:
        print('\nFetching from ' + source + '...')
        feed = feedparser.parse(url)
        
        if not feed.entries:
            print('  No entries found')
            continue
            
        print('  Total entries in feed: ' + str(len(feed.entries)))
        source_count = 0
        
        for entry in feed.entries[:50]:
            try:
                pub_date = None
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    try:
                        pub_date = datetime(*entry.published_parsed[:6])
                    except:
                        pass
                
                # Skip old articles
                if pub_date and (datetime.now() - pub_date) > timedelta(days=3):
                    continue
                
                title = entry.get('title', '').strip()
                description = entry.get('summary', '') or entry.get('description', '')
                link = entry.get('link', '').strip()
                
                if not title or not link:
                    continue
                
                # Check relevance
                text = (title + ' ' + str(description)).lower()
                is_relevant = any(kw in text for kw in keywords)
                
                if is_relevant:
                    time_str = pub_date.strftime('%H:%M') if pub_date else 'Recent'
                    articles.append({
                        'source': source,
                        'title': title,
                        'url': link,
                        'time': time_str,
                        'date': pub_date or datetime.now()
                    })
                    source_count = source_count + 1
                    
                    if source_count >= 8:
                        break
                        
            except Exception as e:
                print('  Error processing entry: ' + str(e))
                continue
        
        total_fetched = total_fetched + source_count
        print('  Found ' + str(source_count) + ' relevant articles')
        
    except Exception as e:
        print('  Error fetching from ' + source + ': ' + str(e))
        continue

print('\n' + '='*50)
print('SUMMARY')
print('='*50)
print('Total articles collected: ' + str(len(articles)))
print('From ' + str(len([s for s in feeds.keys() if any(a['source'] == s for a in articles)])) + ' sources')

if not articles:
    print('\nNo articles found. Reasons could be:')
    print('1. No new articles in last 3 days')
    print('2. RSS feeds temporarily unavailable')
    print('3. Network connectivity issues')
    
    msg = '*Financial News Digest*\n'
    msg = msg + datetime.now().strftime('%B %d, %Y') + '\n\n'
    msg = msg + 'No relevant articles found today.\n'
    msg = msg + 'This could be due to:\n'
    msg = msg + '- Weekend/Holiday\n'
    msg = msg + '- RSS feeds temporarily unavailable\n'
    msg = msg + '- Network issues\n\n'
    msg = msg + 'The system will try again tomorrow.'
else:
    # Sort by date
    articles.sort(key=lambda x: x['date'], reverse=True)
    
    by_source = defaultdict(list)
    for article in articles:
        by_source[article['source']].append(article)
    
    msg = '*Financial News Digest*\n'
    msg = msg + datetime.now().strftime('%B %d, %Y') + '\n\n'
    msg = msg + '📊 ' + str(len(articles)) + ' articles from ' + str(len(by_source)) + ' sources\n'
    msg = msg + '━━━━━━━━━━━━━━━━━\n\n'
    
    # Group by publication
    et_sources = [s for s in by_source.keys() if s.startswith('ET ')]
    mint_sources = [s for s in by_source.keys() if s.startswith('Mint ')]
    mc_sources = [s for s in by_source.keys() if s.startswith('MC ')]
    
    # Economic Times
    if et_sources:
        msg = msg + '📰 *ECONOMIC TIMES*\n'
        for source in sorted(et_sources):
            items = by_source[source][:6]
            if items:
                msg = msg + '_' + source.replace('ET ', '') + '_\n'
                for i, article in enumerate(items, 1):
                    title_short = article['title']
                    if len(title_short) > 90:
                        title_short = title_short[:87] + '...'
                    msg = msg + str(i) + '. [' + title_short + '](' + article['url'] + ')\n'
        msg = msg + '\n'
    
    # Mint
    if mint_sources:
        msg = msg + '📰 *MINT*\n'
        for source in sorted(mint_sources):
            items = by_source[source][:6]
            if items:
                msg = msg + '_' + source.replace('Mint ', '') + '_\n'
                for i, article in enumerate(items, 1):
                    title_short = article['title']
                    if len(title_short) > 90:
                        title_short = title_short[:87] + '...'
                    msg = msg + str(i) + '. [' + title_short + '](' + article['url'] + ')\n'
        msg = msg + '\n'
    
    # MoneyControl
    if mc_sources:
        msg = msg + '📰 *MONEYCONTROL*\n'
        for source in sorted(mc_sources):
            items = by_source[source][:6]
            if items:
                msg = msg + '_' + source.replace('MC ', '') + '_\n'
                for i, article in enumerate(items, 1):
                    title_short = article['title']
                    if len(title_short) > 90:
                        title_short = title_short[:87] + '...'
                    msg = msg + str(i) + '. [' + title_short + '](' + article['url'] + ')\n'
        msg = msg + '\n'

# Send to Telegram
if not token or not chat:
    print('\n❌ ERROR: Token or Chat ID missing!')
    print('Token: ' + str(token[:10] if token else 'None') + '...')
    print('Chat ID: ' + str(chat))
else:
    try:
        print('\n📤 Sending to Telegram...')
        url = 'https://api.telegram.org/bot' + token + '/sendMessage'
        data = {
            'chat_id': chat,
            'text': msg,
            'parse_mode': 'Markdown',
            'disable_web_page_preview': True
        }
        
        response = requests.post(url, json=data, timeout=30)
        
        print('Response status: ' + str(response.status_code))
        
        if response.status_code == 200:
            print('✅ Successfully sent to Telegram!')
        else:
            print('❌ Telegram API Error:')
            print('Status: ' + str(response.status_code))
            print('Response: ' + response.text[:500])
            
    except Exception as e:
        print('❌ Error sending to Telegram: ' + str(e))

print('\n' + '='*50)
print('Script completed')
print('='*50)
