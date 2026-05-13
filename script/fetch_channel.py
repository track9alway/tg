#!/usr/bin/env python3
"""
جستجوی پیشرفته کانال/گروه تلگرام با استفاده از چند موتور جستجو
و غنی‌سازی نتایج با اطلاعات واقعی از صفحه عمومی کانال
ذخیره در search_results.md با فرمت:
- [@username](https://t.me/username) **عنوان** | اعضا: ۱۲٬۳۴۵
"""

import sys
import argparse
import re
import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote

# ---------- توابع جستجو ----------
def google_search(query, num=10):
    """جستجو در Google (ساده) و استخراج لینک‌های t.me"""
    search_query = f'site:t.me {query}'
    url = f'https://www.google.com/search?q={quote(search_query)}&num={num}'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    try:
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code != 200:
            return []
        soup = BeautifulSoup(r.text, 'html.parser')
        usernames = set()
        for a in soup.find_all('a', href=True):
            href = a['href']
            # Google ممکن است لینک‌ها را به صورت absolute ندهد
            if 't.me/' in href and not any(x in href for x in ['/s/', '/c/', '/proxy']):
                # استخراج username
                m = re.search(r'(?:https?://)?t\.me/([a-zA-Z][\w]{3,31})', href)
                if m:
                    usernames.add(m.group(1))
        return list(usernames)[:num]
    except:
        return []

def bing_search(query, num=10):
    """جستجو در Bing"""
    search_query = f'site:t.me {query}'
    url = f'https://www.bing.com/search?q={quote(search_query)}&count={num}'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    try:
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code != 200:
            return []
        soup = BeautifulSoup(r.text, 'html.parser')
        usernames = set()
        for a in soup.find_all('a', href=True):
            href = a['href']
            if 't.me/' in href and not any(x in href for x in ['/s/', '/c/']):
                m = re.search(r'(?:https?://)?t\.me/([a-zA-Z][\w]{3,31})', href)
                if m:
                    usernames.add(m.group(1))
        return list(usernames)[:num]
    except:
        return []

def duckduckgo_search(query, num=10):
    """جستجو در DuckDuckGo با استفاده از API رایگان (Instant Answer)"""
    search_query = f'site:t.me {query}'
    url = 'https://api.duckduckgo.com/'
    params = {
        'q': search_query,
        'format': 'json',
        'no_html': 1,
        'skip_disambig': 1
    }
    try:
        r = requests.get(url, params=params, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
        if r.status_code != 200:
            return []
        data = r.json()
        usernames = set()
        # نتایج در بخش Results یا RelatedTopics هستند
        for topic in data.get('Results', []) + data.get('RelatedTopics', []):
            if 'FirstURL' in topic:
                href = topic['FirstURL']
                if 't.me/' in href:
                    m = re.search(r't\.me/([a-zA-Z][\w]{3,31})', href)
                    if m:
                        usernames.add(m.group(1))
        return list(usernames)[:num]
    except:
        return []

# ---------- دریافت اطلاعات یک کانال ----------
def get_channel_info(username):
    """دریافت عنوان و تعداد اعضا از صفحه عمومی t.me/s/username"""
    url = f'https://t.me/s/{username}'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    try:
        r = requests.get(url, headers=headers, timeout=8)
        if r.status_code != 200:
            return {'title': f'@{username}', 'members': '?'}
        soup = BeautifulSoup(r.text, 'html.parser')
        # عنوان کانال معمولاً در div.tgme_page_title
        title_tag = soup.find('div', class_='tgme_page_title')
        title = title_tag.get_text(strip=True) if title_tag else f'@{username}'
        # تعداد اعضا: div.tgme_page_extra
        extra_tag = soup.find('div', class_='tgme_page_extra')
        members = '?'
        if extra_tag:
            text = extra_tag.get_text(strip=True)
            # متن معمولاً "12.3K members" یا "1.234.567 subscribers" است
            m = re.search(r'([\d.,]+[KMB]?)\s*(?:members|subscribers)', text, re.IGNORECASE)
            if m:
                members = m.group(1).replace(',', '.')
        return {'title': title, 'members': members}
    except:
        return {'title': f'@{username}', 'members': '?'}

# ---------- ذخیره‌سازی ----------
def save_results(channels, output_file):
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(f"# نتایج جستجو\n\n")
        for ch in channels:
            members_str = f" | اعضا: {ch['members']}" if ch['members'] != '?' else ''
            f.write(f"- [@{ch['username']}](https://t.me/{ch['username']}) **{ch['title']}**{members_str}\n")

# ---------- main ----------
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--query', required=True, help='عبارت جستجو')
    parser.add_argument('--output', default='search_results.md', help='فایل خروجی')
    args = parser.parse_args()

    query = args.query
    print(f"🔎 جستجوی کانال‌ها با عبارت: {query}")

    # ۱. گرفتن usernameها از موتورهای جستجو
    usernames = []
    for engine in (duckduckgo_search, google_search, bing_search):
        try:
            result = engine(query, num=10)
            if result:
                print(f"   ✔ {len(result)} نتیجه از {engine.__name__.replace('_search','')}")
                usernames = result
                break  # اولین موتور موفق کافیست
        except Exception as e:
            print(f"   ✗ {engine.__name__}: {e}")

    if not usernames:
        print("❌ هیچ کانالی پیدا نشد.")
        sys.exit(1)

    # ۲. استخراج اطلاعات دقیق برای هر کانال
    channels = []
    for uname in usernames:
        print(f"   ⏳ دریافت اطلاعات @{uname} ...")
        info = get_channel_info(uname)
        channels.append({
            'username': uname,
            'title': info['title'],
            'members': info['members']
        })
        time.sleep(0.5)  # مکث کوتاه برای جلوگیری از Rate Limit

    save_results(channels, args.output)
    print(f"✅ {len(channels)} کانال با اطلاعات کامل در {args.output} ذخیره شد.")

if __name__ == '__main__':
    main()
