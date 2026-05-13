#!/usr/bin/env python3
"""
واکشی پیشرفته و کامل کانال تلگرام از t.me/s/<channel>
با پیمایش صفحه‌بندی، استخراج تمام رسانه‌ها و ذخیره‌سازی بهینه
"""

import sys
import os
import argparse
import re
import time
import random
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

BASE_URL = "https://t.me/s/"

# ----------------------------------------------------------------------
#  توابع کمکی
# ----------------------------------------------------------------------
def fetch_with_retry(url, headers=None, max_tries=3, delay=2):
    """درخواست GET با تلاش مجدد در صورت خطا"""
    if headers is None:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
        }
    for attempt in range(1, max_tries+1):
        try:
            resp = requests.get(url, headers=headers, timeout=15)
            if resp.status_code == 429:
                wait = 10 * attempt
                print(f"⚠️ Rate limited, waiting {wait}s...")
                time.sleep(wait)
                continue
            resp.raise_for_status()
            return resp
        except Exception as e:
            if attempt == max_tries:
                raise
            print(f"🔄 Attempt {attempt} failed ({e}), retrying...")
            time.sleep(delay * attempt)
    return None

def extract_media(wrap):
    """استخراج تمام انواع رسانه از یک بستهٔ پیام"""
    media = None
    media_type = None
    media_name = None
    download_link = None

    # عکس
    photo_wrap = wrap.select_one('.tgme_widget_message_photo_wrap')
    if photo_wrap:
        img = photo_wrap.select_one('img')
        if img and img.get('src'):
            media = img['src']
            media_type = 'photo'
            download_link = media  # لینک مستقیم
        video_tag = photo_wrap.select_one('video')
        if video_tag and video_tag.get('src'):
            media = video_tag['src']
            media_type = 'video'
            download_link = media

    # فایل / سند
    doc_wrap = wrap.select_one('.tgme_widget_message_document')
    if doc_wrap:
        link = doc_wrap.select_one('a.tgme_widget_message_document_link')
        if link and link.get('href'):
            download_link = link['href']
            media = download_link
            media_type = 'file'
            # نام فایل از داخل <span class="tgme_widget_message_document_title">
            name_tag = doc_wrap.select_one('.tgme_widget_message_document_title')
            if name_tag:
                media_name = name_tag.get_text(strip=True)
            else:
                media_name = download_link.split('/')[-1].split('?')[0]

    # گیف / استیکر
    if not media:
        gif = wrap.select_one('.tgme_widget_message_roundvideo, video[src*=".mp4"]')
        if gif and gif.get('src'):
            media = gif['src']
            media_type = 'video'   # گیف معمولاً mp4
            download_link = media

    # لینک پیش‌نمایش (وب‌سایت)
    if not media:
        preview = wrap.select_one('.tgme_widget_message_link_preview')
        if preview:
            img = preview.select_one('img')
            if img and img.get('src'):
                media = img['src']
                media_type = 'photo'
                download_link = media

    return media, media_type, media_name, download_link

def extract_views(wrap):
    """استخراج تعداد بازدید"""
    views_el = wrap.select_one('.tgme_widget_message_views')
    if views_el:
        text = views_el.get_text(strip=True)
        # فقط اعداد را جدا می‌کنیم
        nums = re.sub(r'[^\d]', '', text)
        if nums:
            return nums
    return None

def extract_reactions(wrap):
    """استخراج واکنش‌ها"""
    reactions = []
    reaction_tags = wrap.select('.tgme_widget_message_reaction')
    for r in reaction_tags:
        emoji_el = r.select_one('.emoji')
        count_el = r.select_one('.tgme_widget_message_reaction_count')
        if emoji_el and count_el:
            emoji = emoji_el.get_text(strip=True)
            count = count_el.get_text(strip=True)
            reactions.append({'emoji': emoji, 'count': count})
    return reactions

def extract_message_data(wrap):
    """استخراج کامل اطلاعات یک پیام از المنت HTML"""
    data = {}

    # شناسه پیام
    data_post = wrap.get('data-post', '')
    # فرمت: channel/12345
    parts = data_post.split('/')
    if len(parts) == 2 and parts[1].isdigit():
        data['id'] = int(parts[1])
    else:
        return None  # پیام نامعتبر

    # متن
    text_el = wrap.select_one('.tgme_widget_message_text')
    data['text'] = text_el.get_text('\n', strip=True) if text_el else ''

    # رسانه
    media, media_type, media_name, download_link = extract_media(wrap)
    data['media'] = media
    data['media_type'] = media_type
    data['media_name'] = media_name
    data['download_link'] = download_link

    # بازدید
    data['views'] = extract_views(wrap)

    # واکنش‌ها
    data['reactions'] = extract_reactions(wrap)

    # تاریخ (اختیاری) - می‌توان از تگ time استفاده کرد
    time_tag = wrap.select_one('time')
    if time_tag and time_tag.get('datetime'):
        data['date'] = time_tag['datetime']
    else:
        data['date'] = None

    return data

def parse_page(html):
    """پارس صفحه و بازگرداندن لیست پیام‌ها + لینک before"""
    soup = BeautifulSoup(html, 'lxml')
    msgs = soup.select('.tgme_widget_message_wrap')
    messages = []
    for w in msgs:
        msg_data = extract_message_data(w)
        if msg_data:
            messages.append(msg_data)

    # یافتن لینک "older messages"
    # معمولاً در div.tgme_widget_message_bubble_container یک a با href حاوی ?before=
    page_before = None
    # جستجوی لینک "before"
    for a in soup.find_all('a', href=True):
        href = a['href']
        if 'before=' in href:
            # href ممکن است نسبی باشد
            page_before = urljoin(BASE_URL, href)
            break
    return messages, page_before

# ----------------------------------------------------------------------
#  تابع اصلی دریافت پیام‌ها با پیمایش
# ----------------------------------------------------------------------
def get_messages(channel, count=100):
    """
    دریافت تا count پیام از کانال با دنبال کردن لینک‌های 'before'
    """
    base_url = f"{BASE_URL}{channel}"
    all_messages = []
    current_url = base_url
    seen_ids = set()

    print(f"📡 شروع واکشی از {base_url}")
    while len(all_messages) < count:
        resp = fetch_with_retry(current_url)
        if not resp:
            print("❌ درخواست ناموفق، توقف.")
            break

        page_msgs, next_before = parse_page(resp.text)
        new_msgs = 0
        for msg in page_msgs:
            if msg['id'] not in seen_ids:
                seen_ids.add(msg['id'])
                all_messages.append(msg)
                new_msgs += 1

        print(f"   ✔ {len(page_msgs)} پیام در این صفحه، {new_msgs} پیام جدید (کل: {len(all_messages)})")

        if not next_before:
            print("🏁 به ابتدای کانال رسیدیم.")
            break

        # تاخیر تصادفی برای جلوگیری از تشخیص ربات
        delay = random.uniform(1.5, 3.0)
        time.sleep(delay)

        current_url = next_before

    # برگرداندن فقط تعداد خواسته شده
    return all_messages[:count]

# ----------------------------------------------------------------------
#  ذخیره‌سازی به صورت Markdown
# ----------------------------------------------------------------------
def format_message_md(msg):
    """تبدیل یک پیام به رشته مارک‌داون (سازگار با parse_message_md)"""
    lines = []

    # رسانه
    if msg['media']:
        media_url = msg['media']
        media_type = msg['media_type']
        if media_type in ('photo', 'video'):
            lines.append(f"![{media_type}]({media_url})")
        else:
            name = msg.get('media_name', 'فایل')
            lines.append(f"[📎 {name}]({media_url})")
        if msg.get('download_link') and msg['download_link'] != msg['media']:
            lines.append(f"download: {msg['download_link']}")
        elif msg.get('download_link'):
            lines.append(f"download: {msg['download_link']}")

    # متن
    if msg['text']:
        lines.append(msg['text'])

    # تاریخ (در صورت وجود) به عنوان توضیح
    if msg.get('date'):
        lines.append(f"📅 {msg['date']}")

    # بازدیدها
    if msg['views']:
        lines.append(f"👁 {msg['views']}")

    # واکنش‌ها
    if msg['reactions']:
        react_str = ' '.join([f"{r['emoji']} {r['count']}" for r in msg['reactions']])
        lines.append(react_str)

    return '\n'.join(lines)

def main():
    parser = argparse.ArgumentParser(description='واکشی کامل کانال تلگرام')
    parser.add_argument('--channel', required=True, help='نام کاربری کانال بدون @')
    parser.add_argument('--count', type=int, default=100, help='تعداد پیام‌های مورد نظر')
    args = parser.parse_args()

    channel = args.channel.lstrip('@')
    count = args.count

    print(f"🚀 واکشی تا {count} پیام از @{channel} ...")
    try:
        messages = get_messages(channel, count)
    except Exception as e:
        sys.exit(f"❌ خطای واکشی: {e}")

    if not messages:
        print("⚠️ هیچ پیامی یافت نشد.")
        sys.exit(1)

    # ساخت پوشه
    out_dir = os.path.join('channels', channel)
    os.makedirs(out_dir, exist_ok=True)

    # ذخیره
    for msg in messages:
        fname = f"{msg['id']}.md"
        fpath = os.path.join(out_dir, fname)
        content = format_message_md(msg)
        with open(fpath, 'w', encoding='utf-8') as f:
            f.write(content)

    print(f"✅ {len(messages)} پیام در '{out_dir}' ذخیره شد.")

if __name__ == '__main__':
    main()
