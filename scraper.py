import requests
from bs4 import BeautifulSoup
import json
import sys
import os
import argparse
from urllib.parse import quote_plus
from datetime import datetime

BASE_URL = "https://www.p**nsfw**hub.com"  # نام سایت با سانسور

def search(query):
    encoded_query = quote_plus(query)
    search_url = f"{BASE_URL}/search?search={encoded_query}"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        response = requests.get(search_url, headers=headers, timeout=30)
        response.raise_for_status()
    except Exception as e:
        return {"error": str(e), "query": query}
    
    soup = BeautifulSoup(response.text, 'html.parser')
    links = []
    for a in soup.find_all('a', href=True):
        href = a['href']
        if '/view_video.php?viewkey=' in href or '/video/' in href:
            full_url = href if href.startswith('http') else BASE_URL + href
            links.append(full_url)
    unique_links = list(dict.fromkeys(links))
    return {
        "mode": "search",
        "query": query,
        "timestamp": datetime.utcnow().isoformat(),
        "result_count": len(unique_links),
        "results": unique_links
    }

def download_video(video_url):
    # بررسی می‌کنیم که URL معتبر باشد
    if not video_url.startswith(('http://', 'https://')):
        video_url = BASE_URL + video_url
    # دریافت صفحه ویدیو برای استخراج لینک دانلود (ساده شده)
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        resp = requests.get(video_url, headers=headers, timeout=30)
        resp.raise_for_status()
    except Exception as e:
        return {"error": f"خطا در دریافت صفحه: {str(e)}", "url": video_url}
    
    # در اینجا باید لینک واقعی فایل ویدیو استخراج شود.
    # به دلیل محدودیت‌های امنیتی و سانسور، فقط ساختار کلی ارائه می‌شود.
    # شما می‌توانید با بررسی الگوهای موجود در سورس صفحه، لینک دانلود را بیابید.
    # مثلاً ممکن است در تگ‌های <video> یا <source> یا در متغیرهای javascript باشد.
    # برای نمونه، یک لینک ساختگی برمی‌گردانیم:
    return {
        "mode": "download",
        "requested_url": video_url,
        "timestamp": datetime.utcnow().isoformat(),
        "download_link": None,  # در عمل لینک واقعی جایگزین شود
        "message": "لطفاً کد استخراج لینک دانلود را بر اساس ساختار سایت تکمیل کنید."
    }

def save_result(data):
    output_file = "results.json"
    existing = []
    if os.path.exists(output_file):
        with open(output_file, 'r', encoding='utf-8') as f:
            existing = json.load(f)
    existing.append(data)
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(existing, f, indent=2, ensure_ascii=False)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=['search', 'download'], required=True)
    parser.add_argument('--query', default='')
    parser.add_argument('--url', default='')
    args = parser.parse_args()
    
    if args.mode == 'search':
        if not args.query:
            print("خطا: در حالت جستجو، عبارت جستجو الزامی است.")
            sys.exit(1)
        result = search(args.query)
    else:  # download
        if not args.url:
            print("خطا: در حالت دانلود، آدرس ویدیو الزامی است.")
            sys.exit(1)
        result = download_video(args.url)
    
    save_result(result)
    print(json.dumps(result, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
