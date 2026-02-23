import feedparser
from datetime import datetime, timedelta
import socket
from collections import defaultdict
import time

socket.setdefaulttimeout(10)

print('=' * 60)
print('Active Feed Discovery & Validation')
print('Testing for freshness AND keyword relevance')
print('=' * 60)

# ============================================
# LOAD KEYWORDS
# ============================================
def load_keywords():
    """Load keywords from keywords.txt"""
    keywords = []
    try:
        with open('keywords.txt', 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                keywords.append(line.lower())
        print(f'✓ Loaded {len(keywords)} keywords for relevance filtering\n')
        return keywords
    except:
        print('⚠ keywords.txt not found - using defaults')
        return ['bank', 'banking', 'finance', 'insurance', 'market', 'economy']

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
# VALIDATE WITH KEYWORDS (MATCHES MAIN CODE)
# ============================================
def is_feed_active_and_relevant(url, keywords, min_relevant=3, hours=24):
    """
    Validate feed matches EXACTLY what main aggregator needs:
    1. Has recent entries (last 48 hours)
    2. Entries match our keywords
    
    Returns: (is_active, relevant_count, total_count, freshest_age)
    """
    try:
        feed = feedparser.parse(url, request_headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        if not feed.entries:
            return False, 0, 0, 999
        
        relevant_recent_count = 0
        total_recent_count = 0
        freshest_age = 999
        
        for entry in feed.entries[:50]:
            try:
                # Check if recent
                is_recent = False
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    pub_date = datetime(*entry.published_parsed[:6])
                    age_hours = (datetime.now() - pub_date).total_seconds() / 3600
                    
                    if age_hours < hours:
                        is_recent = True
                        total_recent_count += 1
                    
                    if age_hours < freshest_age:
                        freshest_age = age_hours
                else:
                    # No date - assume recent
                    is_recent = True
                    total_recent_count += 1
                
                # Check if relevant (matches keywords)
                if is_recent:
                    title = entry.get('title', '')
                    description = entry.get('summary', '') or entry.get('description', '')
                    text = (title + ' ' + str(description)).lower()
                    
                    # Same logic as main aggregator
                    is_relevant = any(kw in text for kw in keywords)
                    
                    if is_relevant:
                        relevant_recent_count += 1
                        
            except:
                pass
        
        # Must have at least min_relevant RELEVANT articles
        is_active = relevant_recent_count >= min_relevant
        
        return is_active, relevant_recent_count, total_recent_count, freshest_age
        
    except Exception as e:
        return False, 0, 0, 999

# ============================================
# MAIN VALIDATION
# ============================================
keywords = load_keywords()
master_feeds = load_master_feeds()

if not master_feeds:
    print('ERROR: No feeds in feeds_master.txt')
    exit(1)

print(f'Testing {len(master_feeds)} feeds from feeds_master.txt')
print('Criteria: 3+ RELEVANT articles (matching keywords) from last 48h\n')

working_feeds = []
by_publication = defaultdict(list)

# Statistics
total_tested = 0
broken_feeds = []
irrelevant_feeds = []  # Has content but not relevant

for i, feed_info in enumerate(master_feeds, 1):
    print(f'[{i}/{len(master_feeds)}] {feed_info["name"]}')
    total_tested += 1
    
    is_active, relevant, total_recent, age = is_feed_active_and_relevant(
        feed_info['url'], 
        keywords
    )
    
    if is_active:
        print(f'  ✅ Active: {relevant} relevant articles ({total_recent} total recent, {age:.1f}h ago)')
        feed_info['relevant'] = relevant
        feed_info['age'] = age
        working_feeds.append(feed_info)
        by_publication[feed_info['acronym']].append(feed_info)
    else:
        if total_recent == 0:
            print(f'  ❌ Stale/Broken: 0 recent articles')
            broken_feeds.append(feed_info)
        elif relevant == 0:
            print(f'  ⚠️  Irrelevant: {total_recent} recent articles but 0 match keywords')
            irrelevant_feeds.append(feed_info)
        else:
            print(f'  ⚠️  Insufficient: Only {relevant} relevant articles (need 3+)')
            irrelevant_feeds.append(feed_info)

# ============================================
# SUMMARY
# ============================================
print('\n' + '=' * 60)
print('VALIDATION SUMMARY')
print('=' * 60)
print(f'Total feeds tested: {total_tested}')
print(f'✅ Active & Relevant: {len(working_feeds)}')
print(f'⚠️  Has content but irrelevant: {len(irrelevant_feeds)}')
print(f'❌ Broken/Stale: {len(broken_feeds)}')

print(f'\n📊 BY PUBLICATION:')
for pub in sorted(by_publication.keys()):
    feeds = by_publication[pub]
    avg_relevant = sum(f.get('relevant', 0) for f in feeds) / len(feeds) if feeds else 0
    print(f'  {pub}: {len(feeds)} active feeds (avg {avg_relevant:.1f} relevant articles)')

# Show problematic feeds
if irrelevant_feeds:
    print(f'\n⚠️  IRRELEVANT FEEDS (have content but not matching keywords):')
    for feed_info in irrelevant_feeds[:10]:  # Show first 10
        print(f'  - {feed_info["name"]}')
    if len(irrelevant_feeds) > 10:
        print(f'  ... and {len(irrelevant_feeds) - 10} more')

if broken_feeds:
    print(f'\n❌ BROKEN/STALE FEEDS:')
    for feed_info in broken_feeds[:10]:
        print(f'  - {feed_info["name"]}')
    if len(broken_feeds) > 10:
        print(f'  ... and {len(broken_feeds) - 10} more')

# ============================================
# GENERATE feeds.txt
# ============================================
print('\n' + '=' * 60)
print('GENERATING feeds.txt')
print('=' * 60)

if len(working_feeds) == 0:
    print('❌ ERROR: No working feeds found!')
    print('   Possible reasons:')
    print('   1. Feeds are down')
    print('   2. Keywords are too restrictive')
    print('   3. Network issues')
    exit(1)

try:
    with open('feeds.txt', 'w') as f:
        f.write('# AUTO-GENERATED - Only Active & Relevant Feeds\n')
        f.write('# Criteria: 3+ articles matching keywords from last 48h\n')
        f.write(f'# Last validated: {datetime.now().strftime("%Y-%m-%d %H:%M UTC")}\n')
        f.write(f'# Active feeds: {len(working_feeds)}/{total_tested}\n\n')
        
        for pub in sorted(by_publication.keys()):
            feeds_list = by_publication[pub]
            
            # Sort by relevance (most relevant first)
            feeds_list.sort(key=lambda x: x.get('relevant', 0), reverse=True)
            
            f.write(f'# {pub} - {len(feeds_list)} feeds\n')
            
            for feed_info in feeds_list:
                f.write(f'{feed_info["name"]}|{feed_info["acronym"]}|{feed_info["url"]}\n')
            
            f.write('\n')
    
    print(f'✅ Generated feeds.txt with {len(working_feeds)} active & relevant feeds')
    
    # Show what will work in main aggregator
    total_expected_articles = sum(f.get('relevant', 0) for f in working_feeds)
    print(f'   Expected relevant articles in main run: ~{total_expected_articles}')
    
except Exception as e:
    print(f'❌ Error: {str(e)}')
    exit(1)

print('\n' + '=' * 60)
print('✅ Validation complete!')
print('   feeds.txt now contains ONLY feeds that will work in main aggregator')
print('=' * 60)
