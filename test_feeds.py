import feedparser
import socket
from datetime import datetime, timedelta

# Set timeout
socket.setdefaulttimeout(10)

print('=' * 70)
print('RSS FEED VALIDATOR')
print('=' * 70)

# Load feeds
feeds = {}
try:
    with open('feeds.txt', 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '|' in line:
                parts = line.split('|', 1)
                if len(parts) == 2:
                    feeds[parts[0].strip()] = parts[1].strip()
except Exception as e:
    print('ERROR loading feeds.txt:', e)
    exit(1)

print(f'\nTesting {len(feeds)} feeds...\n')

working_feeds = []
broken_feeds = []
slow_feeds = []

for source, url in feeds.items():
    try:
        print(f'Testing: {source}...')
        
        # Parse feed
        try:
            feed = feedparser.parse(url)
        except socket.timeout:
            print(f'  ⏱️  TIMEOUT')
            slow_feeds.append((source, url, 'Timeout'))
            continue
        except Exception as e:
            print(f'  ❌ ERROR: {str(e)[:50]}')
            broken_feeds.append((source, url, str(e)[:50]))
            continue
        
        total = len(feed.entries)
        
        if total == 0:
            print(f'  ❌ BROKEN: 0 entries')
            broken_feeds.append((source, url, 'Zero entries'))
            continue
        
        # Check for recent articles (last 48 hours)
        recent = 0
        for entry in feed.entries[:20]:
            try:
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    pub_date = datetime(*entry.published_parsed[:6])
                    if (datetime.now() - pub_date) <= timedelta(days=2):
                        recent += 1
                else:
                    recent += 1  # No date = assume recent
            except:
                continue
        
        if recent == 0:
            print(f'  ⚠️  STALE: {total} total, but 0 recent (48hrs)')
            broken_feeds.append((source, url, f'{total} entries but all >48hrs old'))
        else:
            print(f'  ✅ WORKING: {total} total, {recent} recent')
            working_feeds.append((source, url))
            
    except Exception as e:
        print(f'  ❌ ERROR: {str(e)[:50]}')
        broken_feeds.append((source, url, str(e)[:50]))

# Print Summary
print('\n' + '=' * 70)
print('SUMMARY')
print('=' * 70)
print(f'\n✅ WORKING FEEDS: {len(working_feeds)}')
print(f'❌ BROKEN/STALE FEEDS: {len(broken_feeds)}')
print(f'⏱️  TIMEOUT FEEDS: {len(slow_feeds)}')

if broken_feeds:
    print('\n' + '=' * 70)
    print('BROKEN/STALE FEEDS TO REMOVE:')
    print('=' * 70)
    for source, url, reason in broken_feeds:
        print(f'\n{source}')
        print(f'  URL: {url}')
        print(f'  Issue: {reason}')

if slow_feeds:
    print('\n' + '=' * 70)
    print('TIMEOUT FEEDS (may need to remove):')
    print('=' * 70)
    for source, url, reason in slow_feeds:
        print(f'\n{source}')
        print(f'  URL: {url}')

# Generate cleaned feeds.txt
print('\n' + '=' * 70)
print('GENERATING CLEANED feeds.txt')
print('=' * 70)

cleaned_content = '# Financial News RSS Feeds - Auto-cleaned\n'
cleaned_content += '# Format: Source Name|Feed URL\n'
cleaned_content += '# Generated: ' + datetime.now().strftime('%Y-%m-%d %H:%M') + '\n'
cleaned_content += '# Working feeds only\n\n'

# Group by publication
by_pub = {}
for source, url in working_feeds:
    pub = source.split(' ')[0] if ' ' in source else source
    if pub not in by_pub:
        by_pub[pub] = []
    by_pub[pub].append((source, url))

for pub in sorted(by_pub.keys()):
    cleaned_content += f'# {pub} ({len(by_pub[pub])} feeds)\n'
    for source, url in by_pub[pub]:
        cleaned_content += f'{source}|{url}\n'
    cleaned_content += '\n'

# Save cleaned version
with open('feeds_cleaned.txt', 'w') as f:
    f.write(cleaned_content)

print(f'\n✅ Cleaned feeds saved to: feeds_cleaned.txt')
print(f'   {len(working_feeds)} working feeds')
print(f'   {len(broken_feeds) + len(slow_feeds)} broken/slow feeds removed')

print('\n' + '=' * 70)
print('NEXT STEPS:')
print('=' * 70)
print('1. Review feeds_cleaned.txt')
print('2. If satisfied, replace feeds.txt:')
print('   mv feeds_cleaned.txt feeds.txt')
print('3. Commit and push to GitHub')
print('=' * 70)
