import feedparser
import socket
from datetime import datetime

socket.setdefaulttimeout(10)

print('=' * 70)
print('RSS FEED DISCOVERY TOOL')
print('=' * 70)

# Define publications and their potential feed URLs to test
publications = {
    'Economic Times': {
        'base_url': 'https://economictimes.indiatimes.com',
        'patterns': [
            '/markets/rssfeeds/1977021501.cms',
            '/industry/banking/finance/banking/rssfeeds/13358256.cms',
            '/industry/banking/finance/rssfeeds/13358259.cms',
            '/industry/banking/finance/insure/rssfeeds/13358276.cms',
            '/markets/stocks/rssfeeds/2146842.cms',
            '/news/economy/rssfeeds/1373380680.cms',
            '/wealth/rssfeeds/837555174.cms',
            '/tech/rssfeeds/13357270.cms',
            '/small-biz/rssfeeds/11324812.cms',
            '/jobs/rssfeeds/107115618.cms',
            '/industry/telecom/rssfeeds/13357555.cms',
            '/industry/energy/rssfeeds/13358225.cms',
            '/industry/healthcare/biotech/rssfeeds/13358080.cms',
        ]
    },
    
    'LiveMint': {
        'base_url': 'https://www.livemint.com/rss',
        'patterns': [
            '/markets',
            '/money',
            '/industry/banking',
            '/insurance',
            '/companies',
            '/news/india',
            '/technology',
            '/industry',
            '/opinion',
            '/politics',
            '/ai',
            '/mutual-fund',
            '/personal-finance',
            '/budget',
            '/premium',
            '/news/world',
            '/elections',
            '/economy',
            '/auto-news',
            '/education',
            '/sports',
            '/latest-news',
            '/homepage',
        ]
    },
    
    'Financial Times': {
        'base_url': 'https://www.ft.com',
        'patterns': [
            '/markets?format=rss',
            '/companies/financials?format=rss',
            '/world/economy?format=rss',
            '/companies?format=rss',
            '/india?format=rss',
            '/markets/asia-pacific?format=rss',
            '/technology?format=rss',
            '/equities?format=rss',
            '/currencies?format=rss',
            '/commodities?format=rss',
            '/opinion?format=rss',
            '/lex?format=rss',
            '/world/uk?format=rss',
            '/world/us?format=rss',
            '/climate-capital?format=rss',
            '/cryptocurrencies?format=rss',
            '/energy?format=rss',
        ]
    },
    
    'Wall Street Journal': {
        'base_url': 'https://feeds.content.dowjones.io/public/rss',
        'patterns': [
            '/RSSMarketsMain',
            '/WSJcomUSBusiness',
            '/RSSWorldNews',
            '/WSJcomIndia',
            '/WSJcomAsia',
            '/WSJcomTech',
            '/WSJcomOpinion',
            '/RSSWSJD',
            '/RSSLifestyle',
        ]
    },
    
    'Business Standard': {
        'base_url': 'https://www.business-standard.com/rss',
        'patterns': [
            '/finance-bs-banking-finance-101.rss',
            '/markets-106.rss',
            '/economy-policy-102.rss',
            '/companies-101.rss',
            '/finance-bs-insurance-103.rss',
            '/finance-news-101.rss',
            '/technology-108.rss',
            '/international-109.rss',
            '/opinion-103.rss',
            '/current-affairs-news-114.rss',
        ]
    },
    
    'MoneyControl': {
        'base_url': 'https://www.moneycontrol.com/rss',
        'patterns': [
            '/marketreports.xml',
            '/latestnews.xml',
            '/mutualfunds.xml',
            '/business.xml',
            '/stocksexpertsviews.xml',
            '/technicals.xml',
            '/MCNews.xml',
            '/commodities.xml',
            '/IPO.xml',
            '/forex.xml',
        ]
    },
    
    'New York Times': {
        'base_url': 'https://rss.nytimes.com/services/xml/rss/nyt',
        'patterns': [
            '/Business.xml',
            '/Economy.xml',
            '/DealBook.xml',
            '/YourMoney.xml',
            '/Technology.xml',
            '/Markets.xml',
            '/SmallBusiness.xml',
            '/InternationalBusiness.xml',
            '/World.xml',
            '/Politics.xml',
            '/Science.xml',
            '/Health.xml',
            '/Climate.xml',
        ]
    },
    
    'Reuters': {
        'base_url': 'https://www.reuters.com/rssfeed',
        'patterns': [
            '/businessNews',
            '/marketsNews',
            '/financialsNews',
            '/economyNews',
            '/technologyNews',
            '/companyNews',
        ]
    },
    
    'Bloomberg': {
        'base_url': 'https://www.bloomberg.com/feed',
        'patterns': [
            '/podcast/markets.xml',
            '/podcast/technology.xml',
            '/podcast/politics.xml',
        ]
    },
}

discovered_feeds = []
broken_feeds = []

print(f'\nTesting {sum(len(p["patterns"]) for p in publications.values())} potential feed URLs...\n')

for pub_name, pub_info in publications.items():
    print(f'\n{"=" * 70}')
    print(f'{pub_name}')
    print(f'{"=" * 70}')
    
    for pattern in pub_info['patterns']:
        url = pub_info['base_url'] + pattern
        
        # Extract feed name from pattern
        feed_name = pattern.split('/')[-1].replace('.rss', '').replace('.xml', '').replace('.cms', '').replace('?format=rss', '')
        
        try:
            feed = feedparser.parse(url)
            
            total = len(feed.entries)
            
            if total == 0:
                print(f'❌ {feed_name}: No entries')
                broken_feeds.append((pub_name, feed_name, url, 'No entries'))
            else:
                # Check for recent content
                recent = 0
                for entry in feed.entries[:10]:
                    try:
                        if hasattr(entry, 'published_parsed') and entry.published_parsed:
                            pub_date = datetime(*entry.published_parsed[:6])
                            if (datetime.now() - pub_date).days <= 7:
                                recent += 1
                        else:
                            recent += 1
                    except:
                        continue
                
                status = '✅' if recent > 0 else '⚠️'
                print(f'{status} {feed_name}: {total} entries, {recent} recent (7d)')
                
                if recent > 0:
                    discovered_feeds.append({
                        'publication': pub_name,
                        'name': feed_name,
                        'url': url,
                        'total': total,
                        'recent': recent
                    })
                    
        except socket.timeout:
            print(f'⏱️  {feed_name}: Timeout')
            broken_feeds.append((pub_name, feed_name, url, 'Timeout'))
        except Exception as e:
            print(f'❌ {feed_name}: {str(e)[:30]}')
            broken_feeds.append((pub_name, feed_name, url, str(e)[:30]))

# Print summary
print('\n' + '=' * 70)
print('DISCOVERY SUMMARY')
print('=' * 70)
print(f'\n✅ WORKING FEEDS DISCOVERED: {len(discovered_feeds)}')
print(f'❌ BROKEN/UNAVAILABLE: {len(broken_feeds)}')

# Generate feeds.txt format
print('\n' + '=' * 70)
print('SUGGESTED FEEDS TO ADD')
print('=' * 70)

# Group by publication
by_pub = {}
for feed in discovered_feeds:
    pub = feed['publication']
    if pub not in by_pub:
        by_pub[pub] = []
    by_pub[pub].append(feed)

output_content = '# Discovered RSS Feeds\n'
output_content += f'# Generated: {datetime.now().strftime("%Y-%m-%d %H:%M")}\n'
output_content += f'# Total: {len(discovered_feeds)} working feeds\n\n'

for pub in sorted(by_pub.keys()):
    feeds = by_pub[pub]
    output_content += f'# {pub} - {len(feeds)} feeds\n'
    
    for feed in feeds:
        feed_label = f"{pub} {feed['name'].title()}"
        output_content += f'{feed_label}|{feed["url"]}\n'
    
    output_content += '\n'

# Save to file
with open('feeds_discovered.txt', 'w') as f:
    f.write(output_content)

print(f'\n✅ Discovered feeds saved to: feeds_discovered.txt')
print(f'\nTop feeds by activity:')
top_feeds = sorted(discovered_feeds, key=lambda x: x['recent'], reverse=True)[:10]
for i, feed in enumerate(top_feeds, 1):
    print(f"{i}. {feed['publication']} - {feed['name']}: {feed['recent']} recent articles")

print('\n' + '=' * 70)
