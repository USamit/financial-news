import os
from datetime import datetime, timedelta
import feedparser
import requests
from collections import defaultdict

token = os.getenv('TELEGRAM_BOT_TOKEN')
chat = os.getenv('TELEGRAM_CHAT_ID')

print('Starting Financial News Aggregator...')
print('=' * 60)

feeds = {
    'ET Markets': 'https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms',
    'ET Banking': 'https://economictimes.indiatimes.com/industry/banking/finance/banking/rssfeeds/13358256.cms',
    'ET Finance': 'https://economictimes.indiatimes.com/industry/banking/finance/rssfeeds/13358259.cms',
    'ET Insurance': 'https://economictimes.indiatimes.com/industry/banking/finance/insure/rssfeeds/13358276.cms',
    'ET Stocks': 'https://economictimes.indiatimes.com/markets/stocks/rssfeeds/2146842.cms',
    'ET Economy': 'https://economictimes.indiatimes.com/news/economy/rssfeeds/1373380680.cms',

    'Mint Markets': 'https://www.livemint.com/rss/markets',
    'Mint Money': 'https://www.livemint.com/rss/money',
    'Mint Banking': 'https://www.livemint.com/rss/industry/banking',
    'Mint Insurance': 'https://www.livemint.com/rss/insurance',
    'Mint Companies': 'https://www.livemint.com/rss/companies',
    'Mint Economy': 'https://www.livemint.com/rss/news/india',

    'MC Business': 'https://www.moneycontrol.com/rss/business.xml',
    'MC Markets': 'https://www.moneycontrol.com/rss/marketedge.xml',
    'MC Stocks': 'https://www.moneycontrol.com/rss/latestnews.xml',
    'MC Banking': 'https://www.moneycontrol.com/rss/MCtopnews.xml',

    'FT Markets': 'https://www.ft.com/markets?format=rss',
    'FT Banking': 'https://www.ft.com/companies/financials?format=rss',
    'FT World Economy': 'https://www.ft.com/world/economy?format=rss',
    'FT Companies': 'https://www.ft.com/companies?format=rss',
    'FT India': 'https://www.ft.com/india?format=rss',
    'FT Asia Markets': 'https://www.ft.com/markets/asia-pacific?format=rss',

    'WSJ Markets': 'https://feeds.content.dowjones.io/public/rss/RSSMarketsMain',
    'WSJ Finance': 'https://feeds.content.dowjones.io/public/rss/WSJcomUSBusiness',
    'WSJ Economy': 'https://feeds.content.dowjones.io/public/rss/RSSWorldNews',
    'WSJ India': 'https://feeds.content.dowjones.io/public/rss/WSJcomIndia',
    'WSJ Asia': 'https://feeds.content.dowjones.io/public/rss/WSJcomAsia',

    'Barrons Markets': 'https://www.barrons.com/rss',
    'Barrons Asia': 'https://www.barrons.com/articles/asia?mod=rss_asia'
}

keywords = [
    'bank', 'banking', 'financial', 'finance', 'fintech', 'credit', 'loan',
    'payment', 'market', 'stock', 'equity', 'invest', 'insurance', 'bond',
    'rbi', 'sebi', 'fed', 'economy', 'economic', 'trade', 'business',
    'shares', 'fund', 'asset', 'capital', 'fiscal', 'monetary',
    'lender', 'rates', 'yield', 'spread', 'liquidity', 'npa'
]

articles = []
feed_stats = {}

for source, url in feeds.items():
    print('\n' + source + ':')

    try:
        feed = feedparser.parse(url)

        # Retry with browser headers if feed is malformed
        if feed.bozo and not feed.entries:
            resp = requests.get(
                url,
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=15
            )
            feed = feedparser.parse(resp.content)

        print('  Bozo:', feed.bozo)
        total_entries = len(feed.entries)
        print('  Total entries:', total_entries)

        if not feed.entries:
            print('  ❌ No entries found')
            feed_stats[source] = {'total': 0, 'recent': 0, 'relevant': 0}
            continue

        recent_count = 0
        source_count = 0

        for entry in feed.entries[:50]:
            try:
                pub_date = None

                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    pub_date = datetime(*entry.published_parsed[:6])
                elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                    pub_date = datetime(*entry.updated_parsed[:6])

                if pub_date:
                    if datetime.now() - pub_date > timedelta(days=2):
                        continue
                recent_count += 1

                title = entry.get('title', '').strip()
                link = entry.get('link', '').strip()

                description = (
                    entry.get('summary', '') or
                    entry.get('description', '') or
                    (entry.content[0].value if hasattr(entry, 'content') else '')
                )

                if not title or not link:
                    continue

                text = (title + ' ' + description).lower()

                if any(kw in text for kw in keywords):
                    articles.append({
                        'source': source,
                        'title': title,
                        'url': link,
                        'time': pub_date.strftime('%H:%M') if pub_date else 'Recent',
                        'date': pub_date or datetime.now()
                    })
                    source_count += 1

                if source_count >= 8:
                    break

            except Exception:
                continue

        feed_stats[source] = {
            'total': total_entries,
            'recent': recent_count,
            'relevant': source_count
        }

        print('  Recent (2 days):', recent_count)
        print('  ✅ Relevant:', source_count)

    except Exception as e:
        print('  ❌ Error:', e)
        feed_stats[source] = {'total': 0, 'recent': 0, 'relevant': 0}

print('\nScript completed')