import feedparser
from datetime import datetime, timedelta
import socket

# Set timeout
socket.setdefaulttimeout(10)

print('=' * 60)
print('RSS Feed Validator')
print('Testing all feeds from feeds.txt')
print('=' * 60)

# ============================================
# LOAD FEEDS
# ============================================
def load_feeds():
    """Load feeds from feeds.txt (supports both old and new format)"""
    feeds = []
    
    try:
        with open('feeds.txt', 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                if '|' in line:
                    parts = line.split('|')
                    
                    # New format: Feed Name|Acronym|URL
                    if len(parts) == 3:
                        feed_name = parts[0].strip()
                        acronym = parts[1].strip()
                        url = parts[2].strip()
                        feeds.append({
                            'name': feed_name,
                            'acronym': acronym,
                            'url': url
                        })
                    # Old format: Feed Name|URL
                    elif len(parts) == 2:
                        feed_name = parts[0].strip()
                        url = parts[1].strip()
                        acronym = feed_name.split(' ')[0] if ' ' in feed_name else feed_name
                        feeds.append({
                            'name': feed_name,
                            'acronym': acronym,
                            'url': url
                        })
        
        return feeds
    except FileNotFoundError:
        print('ERROR: feeds.txt not found!')
        return []
    except Exception as e:
        print(f'ERROR loading feeds: {str(e)}')
        return []

# ============================================
# TEST FEEDS
# ============================================
feeds = load_feeds()

if not feeds:
    print('No feeds loaded!')
    exit(1)

print(f'\nLoaded {len(feeds)} feeds from feeds.txt\n')

working_feeds = []
broken_feeds = []
timeout_feeds = []
stale_feeds = []

for i, feed_info in enumerate(feeds, 1):
    feed_name = feed_info['name']
    acronym = feed_info['acronym']
    url = feed_info['url']
    
    print(f'[{i}/{len(feeds)}] Testing: {feed_name}')
    
    try:
        # Parse feed
        feed = feedparser.parse(url)
        
        if not feed.entries:
            print(f'  ❌ BROKEN: 0 entries found')
            broken_feeds.append(feed_info)
            continue
        
        # Check for recent content (last 48 hours)
        recent_count = 0
        for entry in feed.entries[:20]:  # Check first 20 entries
            try:
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    pub_date = datetime(*entry.published_parsed[:6])
                    if (datetime.now() - pub_date) <= timedelta(hours=48):
                        recent_count += 1
            except:
                pass
        
        total_entries = len(feed.entries)
        
        if recent_count == 0:
            print(f'  ⚠️  STALE: {total_entries} total entries, but 0 from last 48hrs')
            stale_feeds.append(feed_info)
        else:
            print(f'  ✅ Working: {total_entries} total entries, {recent_count} recent (48hrs)')
            working_feeds.append(feed_info)
        
    except socket.timeout:
        print(f'  ⏱️  TIMEOUT: Request timed out')
        timeout_feeds.append(feed_info)
    except Exception as e:
        print(f'  ❌ ERROR: {str(e)[:50]}')
        broken_feeds.append(feed_info)

# ============================================
# SUMMARY
# ============================================
print('\n' + '=' * 60)
print('SUMMARY')
print('=' * 60)
print(f'Total feeds tested: {len(feeds)}')
print(f'✅ Working: {len(working_feeds)}')
print(f'⚠️  Stale (>48hrs): {len(stale_feeds)}')
print(f'⏱️  Timeout: {len(timeout_feeds)}')
print(f'❌ Broken: {len(broken_feeds)}')
print('=' * 60)

# Show broken feeds
if broken_feeds:
    print('\n❌ BROKEN FEEDS:')
    for feed_info in broken_feeds:
        print(f'  - {feed_info["name"]}')

# Show stale feeds
if stale_feeds:
    print('\n⚠️  STALE FEEDS (no content in last 48hrs):')
    for feed_info in stale_feeds:
        print(f'  - {feed_info["name"]}')

# Show timeout feeds
if timeout_feeds:
    print('\n⏱️  TIMEOUT FEEDS:')
    for feed_info in timeout_feeds:
        print(f'  - {feed_info["name"]}')

# ============================================
# GENERATE CLEANED FEEDS FILE
# ============================================
print('\n' + '=' * 60)
print('GENERATING CLEANED FEEDS FILE')
print('=' * 60)

# Group working feeds by publication
from collections import defaultdict
by_publication = defaultdict(list)

for feed_info in working_feeds:
    by_publication[feed_info['acronym']].append(feed_info)

# Write cleaned feeds file
try:
    with open('feeds_cleaned.txt', 'w') as f:
        f.write('# Working RSS Feeds (Auto-Generated)\n')
        f.write(f'# Validated: {datetime.now().strftime("%Y-%m-%d %H:%M")}\n')
        f.write(f'# Total: {len(working_feeds)} working feeds\n\n')
        
        for pub in sorted(by_publication.keys()):
            feeds_list = by_publication[pub]
            f.write(f'# {pub} - {len(feeds_list)} feeds\n')
            
            for feed_info in sorted(feeds_list, key=lambda x: x['name']):
                f.write(f'{feed_info["name"]}|{feed_info["acronym"]}|{feed_info["url"]}\n')
            
            f.write('\n')
    
    print(f'✅ Generated feeds_cleaned.txt with {len(working_feeds)} working feeds')
    print('   Download this file and replace your feeds.txt with it')
    
except Exception as e:
    print(f'❌ Error writing cleaned feeds: {str(e)}')

print('\n' + '=' * 60)
print('Feed validation complete!')
print('=' * 60)
