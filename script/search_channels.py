#!/usr/bin/env python3
"""
جستجوی پیشرفته کانال/گروه تلگرام با Lyzem.com (بهینه‌شده)
"""

import sys
import argparse
import re
import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote, urljoin

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
}

# ---------- جستجو در Lyzem ----------
def lyzem_search(query, num=10):
    """جستجوی کانال‌ها در lyzem.com و استخراج usernameها"""
    search_url = f'https://lyzem.com/search?q={quote(query)}'
    try:
        resp = requests.get(search_url, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            print(f"   [!] Lyzem returned {resp.status_code}")
            return []
        soup = BeautifulSoup(resp.text, 'html.parser')
        usernames = set()
        # لینک‌های t.me/username
        for a in soup.select('a[href^="https://t.me/"]'):
            href = a['href']
            if '/s/' in href or '/c/' in href or '/proxy' in href:
                continue
            m = re.search(r't\.me/([a-zA-Z][\w]{3,31})', href)
            if m:
                usernames.add(m.group(1))
        return list(usernames)[:num]
    except Exception as e:
        print(f"   [✗] Lyzem error: {e}")
        return []

# ---------- جستجوی Google به عنوان پشتیبان ----------
def google_search(query, num=10):
    """جستجوی گوگل با تنظیمات بهبودیافته"""
    search_query = f'site:t.me {query}'
    url = f'https://www.google.com/search?q={quote(search_query)}&num={num}'
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        if resp.status_code != 200:
            return []
        soup = BeautifulSoup(resp.text, 'html.parser')
        usernames = set()
        for a in soup.find_all('a', href=True):
            href = a['href']
            # برخی لینک‌ها ممکن است redirect داشته باشند
            if '/url?q=' in href:
                real = re.search(r'url\?q=(https?://[^&]+)', href)
                if real:
                    href = real.group(1)
            if 't.me/' in href and not any(x in href for x in ['/s/', '/c/', '/proxy']):
                m = re.search(r't\.me/([a-zA-Z][\w]{3,31})', href)
                if m:
                    usernames.add(m.group(1))
        return list(usernames)[:num]
    except:
        return []

# ---------- دریافت اطلاعات کانال ----------
def get_channel_info(username):
    """عنوان و تعداد اعضا از t.me/s/<username>"""
    url = f'https://t.me/s/{username}'
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        if resp.status_code != 200:
            return {'title': f'@{username}', 'members': '?'}
        soup = BeautifulSoup(resp.text, 'html.parser')
        # عنوان کانال
        title_tag = soup.find('div', class_='tgme_page_title')
        title = title_tag.get_text(strip=True) if title_tag else f'@{username}'
        # تعداد اعضا
        extra_tag = soup.find('div', class_='tgme_page_extra')
        members = '?'
        if extra_tag:
            text = extra_tag.get_text(strip=True)
            m = re.search(r'([\d,.]+[KMB]?)\s*(?:members|subscribers)', text, re.IGNORECASE)
            if m:
                members = m.group(1).replace(',', '.')
        return {'title': title, 'members': members}
    except:
        return {'title': f'@{username}', 'members': '?'}

# ---------- ذخیره‌سازی ----------
def save_results(channels, output_file):
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("# نتایج جستجو\n\n")
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

    # اولویت با Lyzem
    usernames = lyzem_search(query, num=10)

    # اگر Lyzem خالی بود، گوگل را امتحان کن
    if not usernames:
        print("   ↪ تلاش با Google...")
        usernames = google_search(query, num=10)

    if not usernames:
        print("❌ هیچ کانالی پیدا نشد.")
        sys.exit(1)

    print(f"   ✔ {len(usernames)} کانال پیدا شد.")

    # دریافت اطلاعات دقیق برای هر کانال
    channels = []
    for uname in usernames:
        print(f"   ⏳ دریافت اطلاعات @{uname} ...")
        info = get_channel_info(uname)
        channels.append({
            'username': uname,
            'title': info['title'],
            'members': info['members']
        })
        time.sleep(0.6)  # مکث برای جلوگیری از rate limit

    save_results(channels, args.output)
    print(f"✅ {len(channels)} کانال با اطلاعات کامل در {args.output} ذخیره شد.")

if __name__ == '__main__':
    main()
