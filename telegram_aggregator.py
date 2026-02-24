import os
from datetime import datetime, timedelta
import feedparser
import requests
from collections import defaultdict
import socket

socket.setdefaulttimeout(10)

token = os.getenv('TELEGRAM_BOT_TOKEN')
chat = os.getenv('TELEGRAM_CHAT_ID')

print('=' * 60)
print('Starting Financial News Aggregator (DEBUG MODE)')
print('=' * 60)

# Configuration
MIN_ARTICLES_FOR_TRENDING = 50
MAX_TRENDING_TOPICS = 5

# ============================================
# LOAD RECIPIENTS
# ============================================
def load_recipients():
    recipients = []
    if chat:
        recipients.append(chat)
        print('✓ Added primary recipient from secret')
    
    try:
        with open('recipients.txt', 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#') or line == 'TELEGRAM_CHAT_ID':
                    continue
                recipients.append(line)
        print('✓ Loaded ' + str(len(recipients)) + ' total recipients')
        return recipients
    except FileNotFoundError:
        print('⚠ recipients.txt not found')
        return recipients
    except Exception as e:
        print('⚠ Error loading recipients: ' + str(e))
        return recipients

# ============================================
# LOAD KEYWORDS
# ============================================
def load_keywords():
    keywords = []
    try:
        with open('keywords.txt', 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                keywords.append(line.lower())
        print('✓ Loaded ' + str(len(keywords)) + ' keywords')
        print('  First 10 keywords:', keywords[:10])
        return keywords
    except FileNotFoundError:
        print('⚠ keywords.txt not found - using defaults')
        return ['bank', 'banking', 'finance', 'insurance', 'market', 'economy']
    except Exception as e:
        print('⚠ Error loading keywords: ' + str(e))
        return ['bank', 'banking', 'finance', 'insurance', 'market', 'economy']

# ============================================
# LOAD FEEDS
# ============================================
def load_feeds():
    feeds = {}
    try:
        with open('feeds.txt', 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                if '|' in line:
                    parts = line.split('|')
                    
                    if len(parts) == 3:
                        feed_name = parts[0].strip()
                        acronym = parts[1].strip()
                        url = parts[2].strip()
                        feeds[feed_name] = {'url': url, 'acronym': acronym}
                    elif len(parts) == 2:
                        feed_name = parts[0].strip()
                        url = parts[1].strip()
                        acronym = feed_name.split(' ')[0] if ' ' in feed_name else feed_name
                        feeds[feed_name] = {'url': url, 'acronym': acronym}
        
        print('✓ Loaded ' + str(len(feeds)) + ' RSS feeds')
        
        # DEBUG: Show BS feeds
        bs_feeds = {k: v for k, v in feeds.items() if v['acronym'] == 'BS'}
        print('  DEBUG: Found ' + str(len(bs_feeds)) + ' BS feeds:')
        for name in list(bs_feeds.keys())[:5]:
            print('    - ' + name)
        
        return feeds
    except FileNotFoundError:
        print('⚠ feeds.txt not found')
        return {}
    except Exception as e:
        print('⚠ Error loading feeds: ' + str(e))
        return {}

# ============================================
# LOAD TOPICS
# ============================================
def load_topics():
    topics = []
    try:
        with open('topics.txt', 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                if '|' in line:
                    parts = line.split('|', 1)
                    if len(parts) == 2:
                        topic_name = parts[0].strip()
                        keywords_str = parts[1].strip()
                        keywords = [kw.strip().lower() for kw in keywords_str.split(',')]
                        
                        topics.append({
                            'name': topic_name,
                            'keywords': keywords
                        })
        
        print('✓ Loaded ' + str(len(topics)) + ' topic categories')
        return topics
    except FileNotFoundError:
        print('⚠ topics.txt not found - using defaults')
        return [
            {'name': 'BANKING & FINANCE', 'keywords': ['bank', 'banking', 'loan', 'credit']},
            {'name': 'OTHER NEWS', 'keywords': ['other', 'news']}
        ]
    except Exception as e:
        print('⚠ Error loading topics: ' + str(e))
        return [{'name': 'OTHER NEWS', 'keywords': ['other', 'news']}]

# ============================================
# CATEGORIZE ARTICLE
# ============================================
def categorize_article(title, description, topics):
    text = (title + ' ' + str(description)).lower()
    topic_scores = {}
    
    for topic in topics:
        score = 0
        for keyword in topic['keywords']:
            if keyword in text:
                score += 1
        
        if score > 0:
            topic_scores[topic['name']] = score
    
    if topic_scores:
        best_topic = max(topic_scores, key=topic_scores.get)
        return best_topic
    
    return 'OTHER NEWS'

# ============================================
# TRENDING DETECTION
# ============================================
def identify_trending_topics_free(articles, top_n=5):
    if len(articles) < 10:
        return []
    
    current_month = datetime.now().month
    if 1 <= current_month <= 3:
        quarter = 'Q4'
        quarter_patterns = ['q4', 'fourth quarter', 'results', 'earnings']
    elif 4 <= current_month <= 6:
        quarter = 'Q1'
        quarter_patterns = ['q1', 'first quarter', 'results', 'earnings']
    elif 7 <= current_month <= 9:
        quarter = 'Q2'
        quarter_patterns = ['q2', 'second quarter', 'results', 'earnings']
    else:
        quarter = 'Q3'
        quarter_patterns = ['q3', 'third quarter', 'results', 'earnings']
    
    trending_themes = {
        'Trade & Tariffs': ['tariff', 'bilateral trade', 'trade deal', 'trade war', 'export', 'import', 'trade agreement'],
        f'{quarter} Earnings': quarter_patterns + ['profit', 'revenue', 'quarterly', 'beat estimates', 'miss estimates'],
        'Rate Decisions': ['rate cut', 'rate hike', 'repo rate', 'policy rate', 'monetary policy', 'interest rate decision'],
        'IPO & Listings': ['ipo', 'listing', 'issue price', 'subscription', 'grey market premium', 'allotment'],
        'Mergers & Deals': ['merger', 'acquisition', 'm&a', 'stake sale', 'buyout', 'takeover'],
        'Regulatory Actions': ['sebi action', 'irdai guideline', 'rbi circular', 'penalty', 'enforcement', 'investigation'],
    }
    
    theme_clusters = defaultdict(list)
    
    for article in articles:
        text = article['title'].lower()
        best_theme = None
        max_matches = 0
        
        for theme_name, patterns in trending_themes.items():
            matches = sum(1 for pattern in patterns if pattern in text)
            if matches > max_matches:
                max_matches = matches
                best_theme = theme_name
        
        if best_theme and max_matches > 0:
            theme_clusters[best_theme].append(article)
    
    trending = []
    for theme_name, cluster_articles in theme_clusters.items():
        if len(cluster_articles) >= 5:
            summary = generate_free_summary(theme_name, cluster_articles[:5])
            trending.append({
                'topic': theme_name,
                'count': len(cluster_articles),
                'articles': cluster_articles,
                'summary': summary
            })
    
    trending.sort(key=lambda x: x['count'], reverse=True)
    return trending[:top_n]

def generate_free_summary(topic_name, articles):
    if not articles:
        return 'Multiple developments reported.'
    
    summary_parts = []
    for article in articles[:3]:
        title = article['title']
        cleaned = title
        for prefix in ['Exclusive:', 'Breaking:', 'Opinion:', 'Analysis:', 'Update:']:
            cleaned = cleaned.replace(prefix, '').strip()
        
        if len(cleaned) > 70:
            if '.' in cleaned[:70]:
                cleaned = cleaned[:cleaned[:70].rindex('.')] + '.'
            elif ',' in cleaned[:70]:
                cleaned = cleaned[:cleaned[:70].rindex(',')] + '...'
            else:
                cleaned = cleaned[:67] + '...'
        
        summary_parts.append(cleaned)
    
    return ' • '.join(summary_parts)

# Load configuration
RECIPIENTS = load_recipients()
keywords = load_keywords()
feeds = load_feeds()
topics = load_topics()

if not feeds:
    print('ERROR: No feeds loaded!')
    exit(1)

articles = []
feed_stats = {}
seen_urls = set()

# ============================================
# PROCESS RSS FEEDS (HEAVY DEBUG)
# ============================================
print('\n' + '=' * 60)
print('FETCHING ARTICLES FROM ' + str(len(feeds)) + ' FEEDS')
print('=' * 60)

debug_feed_count = 0

for feed_name, feed_info in feeds.items():
    try:
        url = feed_info['url']
        acronym = feed_info['acronym']
        
        print('\n[' + str(debug_feed_count + 1) + '/' + str(len(feeds)) + '] ' + feed_name + ' (' + acronym + ')')
        print('  URL: ' + url[:60] + '...')
        
        # DEBUG: Focus on BS feeds
        is_bs_feed = (acronym == 'BS')
        
        try:
            feed = feedparser.parse(url, request_headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
        except socket.timeout:
            print('  ⏱️  TIMEOUT - Skipping')
            feed_stats[feed_name] = {'total': 0, 'recent': 0, 'relevant': 0}
            debug_feed_count += 1
            continue
        except Exception as e:
            print('  ❌ Parse Error: ' + str(e)[:50])
            feed_stats[feed_name] = {'total': 0, 'recent': 0, 'relevant': 0}
            debug_feed_count += 1
            continue
        
        total_entries = len(feed.entries)
        print('  Total entries: ' + str(total_entries))
        
        if not feed.entries:
            print('  ❌ No entries found')
            feed_stats[feed_name] = {'total': 0, 'recent': 0, 'relevant': 0}
            debug_feed_count += 1
            continue
        
        recent_count = 0
        source_count = 0
        
        # DEBUG: Track first BS article
        first_bs_article_shown = False
        
        for entry_idx, entry in enumerate(feed.entries[:100]):
            try:
                pub_date = None
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    try:
                        pub_date = datetime(*entry.published_parsed[:6])
                    except:
                        pass
                
                # 48-hour window
                if pub_date:
                    age_hours = (datetime.now() - pub_date).total_seconds() / 3600
                    if age_hours <= 48:
                        recent_count += 1
                    else:
                        continue
                else:
                    recent_count += 1
                
                title = entry.get('title', '').strip()
                description = entry.get('summary', '') or entry.get('description', '')
                link = entry.get('link', '').strip()
                
                if not title or not link:
                    continue
                
                if link in seen_urls:
                    continue
                
                # Keyword matching
                text = (title + ' ' + str(description)).lower()
                is_relevant = any(kw in text for kw in keywords)
                
                # DEBUG: Show first article from BS feeds
                if is_bs_feed and not first_bs_article_shown and entry_idx < 5:
                    print(f'  DEBUG Entry {entry_idx + 1}:')
                    print(f'    Title: {title[:80]}')
                    print(f'    Age: {age_hours:.1f}h' if pub_date else '    Age: Unknown')
                    print(f'    Relevant: {is_relevant}')
                    if is_relevant:
                        matching_kw = [kw for kw in keywords if kw in text]
                        print(f'    Matched keywords: {matching_kw[:5]}')
                        first_bs_article_shown = True
                
                if is_relevant:
                    seen_urls.add(link)
                    time_str = pub_date.strftime('%H:%M') if pub_date else 'Recent'
                    topic = categorize_article(title, description, topics)
                    
                    articles.append({
                        'source': feed_name,
                        'publication': acronym,
                        'title': title,
                        'url': link,
                        'time': time_str,
                        'date': pub_date or datetime.now(),
                        'topic': topic,
                        'description': description
                    })
                    
                    source_count += 1
                        
            except Exception as e:
                if is_bs_feed:
                    print(f'  ⚠️  Error processing entry: {str(e)[:40]}')
                continue
        
        feed_stats[feed_name] = {
            'total': total_entries,
            'recent': recent_count,
            'relevant': source_count
        }
        
        print('  Recent (48hrs): ' + str(recent_count))
        print('  Relevant: ' + str(source_count))
        
        if is_bs_feed and source_count == 0:
            print('  ⚠️  BS FEED WITH 0 RELEVANT ARTICLES - CHECK DEBUG OUTPUT ABOVE')
        
        debug_feed_count += 1
        
    except Exception as e:
        print('  ❌ Feed Error: ' + str(e)[:50])
        feed_stats[feed_name] = {'total': 0, 'recent': 0, 'relevant': 0}
        debug_feed_count += 1
        continue

# SUMMARY
print('\n' + '=' * 60)
print('SUMMARY BY PUBLICATION')
print('=' * 60)

all_publications = set()
for feed_name, feed_info in feeds.items():
    all_publications.add(feed_info['acronym'])

for pub in sorted(all_publications):
    pub_feeds = {k: v for k, v in feed_stats.items() if feeds.get(k, {}).get('acronym') == pub}
    if pub_feeds:
        total_rel = sum(f['relevant'] for f in pub_feeds.values())
        print(pub + ': ' + str(total_rel) + ' articles from ' + str(len(pub_feeds)) + ' feeds')

print('\nTotal unique articles: ' + str(len(articles)))

print('\n' + '=' * 60)
print('DEBUG: Articles by publication')
print('=' * 60)
by_pub = defaultdict(int)
for article in articles:
    by_pub[article['publication']] += 1

for pub in sorted(by_pub.keys()):
    print(f'{pub}: {by_pub[pub]} articles')

print('=' * 60)
print('Script completed (DEBUG MODE)')
print('=' * 60)
