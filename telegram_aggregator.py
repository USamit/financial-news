import os
from datetime import datetime, timedelta
import feedparser
import requests
from collections import defaultdict
import socket

# Set global timeout for all network operations
socket.setdefaulttimeout(10)

token = os.getenv('TELEGRAM_BOT_TOKEN')
chat = os.getenv('TELEGRAM_CHAT_ID')

print('=' * 60)
print('Starting Financial News Aggregator...')
print('=' * 60)

# ============================================
# CONFIGURATION
# ============================================
MIN_ARTICLES_FOR_TRENDING = 50  # Don't run trending on small batches
MAX_TRENDING_TOPICS = 5  # Show top 5 trending topics

# ============================================
# LOAD RECIPIENTS from recipients.txt
# ============================================
def load_recipients():
    """Load recipient chat IDs from recipients.txt file"""
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
# LOAD KEYWORDS from keywords.txt
# ============================================
def load_keywords():
    """Load keywords from keywords.txt file"""
    keywords = []
    
    try:
        with open('keywords.txt', 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                keywords.append(line.lower())
        print('✓ Loaded ' + str(len(keywords)) + ' keywords')
        return keywords
    except FileNotFoundError:
        print('⚠ keywords.txt not found - using minimal defaults')
        return ['bank', 'banking', 'finance', 'insurance', 'market', 'economy']
    except Exception as e:
        print('⚠ Error loading keywords: ' + str(e))
        return ['bank', 'banking', 'finance', 'insurance', 'market', 'economy']

# ============================================
# LOAD FEEDS from feeds.txt
# ============================================
def load_feeds():
    """Load RSS feeds from feeds.txt file with acronyms"""
    feeds = {}
    
    try:
        with open('feeds.txt', 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                # Expected format: Feed Name|Acronym|URL
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
        return feeds
    except FileNotFoundError:
        print('⚠ feeds.txt not found - using minimal defaults')
        return {
            'ET Markets': {'url': 'https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms', 'acronym': 'ET'}
        }
    except Exception as e:
        print('⚠ Error loading feeds: ' + str(e))
        return {}

# ============================================
# LOAD TOPICS from topics.txt
# ============================================
def load_topics():
    """Load topic categorization from topics.txt file"""
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
        print('⚠ topics.txt not found - using minimal defaults')
        return [
            {'name': 'BANKING & FINANCE', 'keywords': ['bank', 'banking', 'loan', 'credit']},
            {'name': 'OTHER NEWS', 'keywords': ['other', 'news']}
        ]
    except Exception as e:
        print('⚠ Error loading topics: ' + str(e))
        return [{'name': 'OTHER NEWS', 'keywords': ['other', 'news']}]

# ============================================
# CATEGORIZE ARTICLE BY TOPIC
# ============================================
def categorize_article(title, description, topics):
    """Categorize article using scoring"""
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
# FREE TRENDING DETECTION (MINIMAL PATTERNS)
# ============================================
def identify_trending_topics_free(articles, top_n=5):
    """
    Identify trending topics by clustering articles into news themes
    Uses minimal patterns for current events (not duplicating keywords.txt)
    """
    
    if len(articles) < 10:
        return []
    
    # Get current quarter dynamically
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
    
    # Minimal news theme patterns (these are EVENT THEMES, not keywords)
    trending_themes = {
        'Trade & Tariffs​​​​​​​​​​​​​​​​
