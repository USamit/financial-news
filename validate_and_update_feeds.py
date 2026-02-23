import feedparser
from datetime import datetime, timedelta
import socket
from collections import defaultdict
import requests
from bs4 import BeautifulSoup
import time

socket.setdefaulttimeout(10)

print('=' * 60)
print('Active Feed Discovery & Validation')
print('Finding the most active, freshest feeds')
print('=' * 60)

# ============================================
# DISCOVERY PATTERNS
# ============================================
DISCOVERY_PATTERNS = {
    'BS': {
        'name': 'Business Standard',
        'patterns': [
            'https://www.business-standard.com/rss/latest.rss',
            'https://www.business-standard.com/rss/home.rss',
            'https://www.business-standard.com/rss/markets.rss',
            'https://www.business-standard.com/rss/finance.rss',
            'https://www.business-standard.com/rss/economy.rss',
            'https://www.business-standard.com/rss/companies.rss',
            'https://www.business-standard.com/rss/banking.rss',
            'https://www.business-standard.com/rss/technology.rss',
            'https://www.business-standard.com/rss/insurance.rss',
        ]
    },
    'ET': {
        'name': 'Economic Times',
        'patterns': [
            'https://economictimes.indiatimes.com/rssfeedstopstories.cms',
            'https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms',
            'https://economictimes.indiatimes.com/industry/banking/finance/rssfeeds/13358259.cms',
            'https://economictimes.indiatimes.com/news/economy/rssfeeds/1373380680.cms',
        ]
    },
    'FT': {
        'name': 'Financial Times',
        'patterns': [
            'https://www.ft.com/?format=rss',
            'https://www.ft.com/companies?format=rss',
            'https://www.ft.com/markets?format=rss',
            'https://www.ft.com/world/economy?format=rss',
        ]
    },
    'Mint': {
        'name': 'LiveMint',
        'patterns': [
            'https://www.livemint.com/rss/homepage',
            'https://www.livemint.com/rss/markets',
            'https://www.livemint.com/rss/money',
            'https://www.livemint.com/rss/companies',
            'https://www.livemint.com/rss/economy',
        ]
    },
    'NYT': {
        'name': 'New York Times',
        'patterns': [
            'https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml',
            'https://rss.nytimes.com/services/xml/rss/nyt/Business.xml',
            'https://rss.nytimes.com/services/xml/rss/nyt/Economy.xml',
        ]
    },
    'WSJ': {
        'name': 'Wall Street Journal',
        'patterns': [
            'https://feeds.content.dowjones.io/public/rss/RSSMarketsMain',
            'https://feeds.content.dowjones.io/public/rss/WSJcomUSBusiness',
        ]
    },
    'MC': {
        'name': 'MoneyControl',
        'patterns': [
            'https://www.moneycontrol.com/rss/latestnews.xml',
            'https://www.moneycontrol.com/rss/business.xml',
            'https://www.moneycontrol.com/rss/marketreports.xml',
        ]
    }
}

# ============================================
# LOAD MASTER FEEDS
# ============================================
def load_master_feeds():
    feeds = []
    try:
        with open('feeds_master.txt', 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                if '|' in line:
                    parts = line.split('|')
                    if len(parts) == 3:
                        feeds.append({
                            'name': parts[0].strip(),
                            'acronym': parts[1].strip(),
                            'url': parts[2].strip()
                        })
        return feeds
    except:
        return []

# ============================================
# STRICT VALIDATION (ONLY FRESH FEEDS)
# ============================================
def is_feed_active(url, min_recent=3, hours=48):
    """
    Strictly validate if feed is ACTIVE
    Returns: (is_active, recent_count, total_count, freshest_age_hours)
    """
    try:
        feed = feedparser.parse(url, request_headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        if not feed.entries or len(feed.entries) < 5:
            return False, 0, 0, 999
        
        # Count RECENT articles (last 48 hours)
        recent_count = 0
        freshest_age = 999
        
        for entry in feed.entries[:50]:
            try:
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    pub_date = datetime(*entry.published_parsed[:6])
                    age_hours = (datetime.now() - pub_date).total_seconds() / 3600
                    
                    if age_hours < hours:
                        recent_count += 1
                    
                    if age_hours < freshest_age:
                        freshest_age = age_hours
            except:
                pass
        
        # Must have at least min_recent articles from last 48 hours
        is_active = recent_count >= min_recent
        
        return is_active, recent_count, len(feed.entries), freshest_age
        
    except:
        return False, 0, 0, 999

# ============================================
# DISCOVER ACTIVE FEEDS
# ============================================
def discover_active_feeds(pub_acronym):
    """
    Discover and test feeds for a publication
    Returns only ACTIVE feeds
    """
    
    if pub_acronym not in DISCOVERY_PATTERNS:
        return []
    
    config = DISCOVERY_PATTERNS[pub_acronym]
    print(f'  🔍 Discovering active feeds for {config["name"]}...')
    
    discovered = []
    
    # Test predefined patterns
    for url in config['patterns']:
        is_active, recent, total, age = is_feed_active(url)
        
        if is_active:
            # Generate name from URL
            feed_name = url.split('/')[-1].replace('.rss', '').replace('.xml', '').replace('.cms', '')
            feed_name = feed_name.replace('-', ' ').replace('_', ' ').title()
            feed_name = f'{pub_acronym} {feed_name}'
            
            discovered.append({
                'name': feed_name,
                'acronym': pub_acronym,
                'url': url,
                'recent': recent,
                'total': total,
                'age': age
            })
            
            print(f'    ✅ {feed_name}: {recent} recent articles ({age:.1f}h ago)')
    
    # Try to scrape homepage for RSS links
    try:
        base_url = config.get('base_url', f'https://www.{pub_acronym.lower()}.com')
        response = requests.get(base_url, timeout=5, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find RSS links in HTML
            for link in soup.find_all('link', type='application/rss+xml'):
                if 'href' in link.attrs:
                    url = link['href']
                    if not url.startswith('http'):
                        url = base_url + url
                    
                    # Test if active
                    is_active, recent, total, age = is_feed_active(url)
                    
                    if is_active and url not in [f['url'] for f in discovered]:
                        feed_name = link.get('title', 'RSS Feed')
                        feed_name = f'{pub_acronym} {feed_name}'
                        
                        discovered.append({
                            'name': feed_name,
                            'acronym': pub_acronym,
                            'url': url,
                            'recent': recent,
                            'total': total,
                            'age': age
                        })
                        
                        print(f'    ✅ {feed_name}: {recent} recent articles ({age:.1f}h ago)')
    except:
        pass
    
    print(f'    Found {len(discovered)} ACTIVE feeds')
    return discovered

# ============================================
# MAIN VALIDATION
# ============================================
master_feeds = load_master_feeds()

print(f'\nPhase 1: Testing {len(master_feeds)} feeds from feeds_master.txt')
print('Criteria: Must have 3+ articles from last 48 hours\n')

working_feeds = []
by_publication = defaultdict(list)

for i, feed_info in enumerate(master_feeds, 1):
    print(f'[{i}/{len(master_feeds)}] {feed_info["name"]}')
    
    is_active, recent, total, age = is_feed_active(feed_info['url'])
    
    if is_active:
        print(f'  ✅ Active: {recent} recent articles ({age:.1f}h ago)')
        feed_info['recent'] = recent
        feed_info['age'] = age
        working_feeds.append(feed_info)
        by_publication[feed_info['acronym']].append(feed_info)
    else:
        if total == 0:
            print(f'  ❌ Broken: 0 entries')
        elif recent == 0:
            print(f'  ⚠️  Stale: {total} entries but 0 from last 48h (oldest: {age:.1f}h)')
        else:
            print(f'  ⚠️  Inactive: Only {recent} recent articles (need 3+)')

# ============================================
# AUTO-DISCOVERY FOR WEAK PUBLICATIONS
# ============================================
print('\n' + '=' * 60)
print('Phase 2: Auto-Discovery for Publications with <3 Active Feeds')
print('=' * 60)

MIN_FEEDS_PER_PUB = 3

for pub_acronym, config in DISCOVERY_PATTERNS.items():
    current_count = len(by_publication.get(pub_acronym, []))
    
    if current_count < MIN_FEEDS_PER_PUB:
        print(f'\n⚠️  {config["name"]} ({pub_acronym}): Only {current_count} active feeds')
        print(f'   Target: {MIN_FEEDS_PER_PUB} feeds - discovering alternatives...')
        
        discovered = discover_active_feeds(pub_acronym)
        
        # Add discovered feeds (avoid duplicates)
        existing_urls = {f['url'] for f in by_publication[pub_acronym]}
        
        for feed_info in discovered:
            if feed_info['url'] not in existing_urls:
                working_feeds.append(feed_info)
                by_publication[pub_acronym].append(feed_info)
        
        new_count = len(by_publication[pub_acronym])
        print(f'   ✅ Now has {new_count} active feeds (+{new_count - current_count} discovered)')

# ============================================
# FINAL SUMMARY
# ============================================
print('\n' + '=' * 60)
print('FINAL SUMMARY')
print('=' * 60)

total_active = sum(len(feeds) for feeds in by_publication.values())

print(f'Total ACTIVE feeds: {total_active}')
print(f'Publications covered: {len(by_publication)}')
print(f'\n📊 BY PUBLICATION:')

for pub in sorted(by_publication.keys()):
    feeds = by_publication[pub]
    avg_recent = sum(f.get('recent', 0) for f in feeds) / len(feeds) if feeds else 0
    avg_age = sum(f.get('age', 0) for f in feeds) / len(feeds) if feeds else 0
    
    print(f'  {pub}: {len(feeds)} feeds (avg {avg_recent:.1f} recent, {avg_age:.1f}h old)')

# ============================================
# GENERATE feeds.txt (ACTIVE FEEDS ONLY)
# ============================================
print('\n' + '=' * 60)
print('GENERATING feeds.txt with ACTIVE feeds only')
print('=' * 60)

try:
    with open('feeds.txt', 'w') as f:
        f.write('# AUTO-GENERATED ACTIVE FEEDS\n')
        f.write('# Only includes feeds with 3+ articles from last 48 hours\n')
        f.write(f'# Last validated: {datetime.now().strftime("%Y-%m-%d %H:%M UTC")}\n')
        f.write(f'# Active feeds: {total_active}\n\n')
        
        for pub in sorted(by_publication.keys()):
            feeds_list = by_publication[pub]
            
            # Sort by freshness (most recent first)
            feeds_list.sort(key=lambda x: x.get('age', 999))
            
            f.write(f'# {pub} - {len(feeds_list)} active feeds\n')
            
            for feed_info in feeds_list:
                f.write(f'{feed_info["name"]}|{feed_info["acronym"]}|{feed_info["url"]}\n')
            
            f.write('\n')
    
    print(f'✅ Generated feeds.txt with {total_active} ACTIVE feeds')
    print('   All feeds have fresh content from last 48 hours')
    
except Exception as e:
    print(f'❌ Error: {str(e)}')
    exit(1)

print('\n' + '=' * 60)
print('✅ Active feed discovery complete!')
print('=' * 60)
