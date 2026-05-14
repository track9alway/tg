import requests
from bs4 import BeautifulSoup
import json
import sys
import os
import argparse
from urllib.parse import quote_plus, urlparse
from datetime import datetime
import hashlib

BASE_URL = "https://www.pornhub.com" 
DOWNLOAD_DIR = "downloads"

def ensure_download_dir():
    if not os.path.exists(DOWNLOAD_DIR):
        os.makedirs(DOWNLOAD_DIR)

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
    """دانلود فایل ویدیو و ذخیره آن در پوشه downloads"""
    ensure_download_dir()
    
    # تکمیل URL در صورت نیاز
    if not video_url.startswith(('http://', 'https://')):
        video_url = BASE_URL + video_url
    
    # دریافت صفحه ویدیو برای استخراج لینک واقعی دانلود
    # (بخش اصلی که باید بر اساس ساختار سایت تکمیل شود)
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        page_resp = requests.get(video_url, headers=headers, timeout=30)
        page_resp.raise_for_status()
    except Exception as e:
        return {"error": f"خطا در دریافت صفحه: {str(e)}", "url": video_url}
    
    # در اینجا باید لینک دانلود واقعی را از صفحه استخراج کنید.
    # به دلیل محدودیت‌های امنیتی و سانسور، یک الگوی عمومی ارائه می‌شود.
    # معمولاً لینک دانلود در تگ‌های <video> یا <source> یا در یک متغیر جاوااسکریپت است.
    # نمونه فرضی:
    soup = BeautifulSoup(page_resp.text, 'html.parser')
    download_link = None
    # مثال: پیدا کردن اولین تگ video و استخراج src
    video_tag = soup.find('video')
    if video_tag and video_tag.get('src'):
        download_link = video_tag['src']
    elif soup.find('source'):
        download_link = soup.find('source').get('src')
    
    if not download_link:
        return {"error": "لینک دانلود یافت نشد", "url": video_url}
    
    if not download_link.startswith('http'):
        download_link = BASE_URL + download_link
    
    # دانلود فایل
    try:
        video_response = requests.get(download_link, headers=headers, stream=True, timeout=60)
        video_response.raise_for_status()
        
        # ایجاد نام فایل بر اساس URL یا هش
        url_hash = hashlib.md5(video_url.encode()).hexdigest()[:8]
        filename = f"{url_hash}.mp4"
        filepath = os.path.join(DOWNLOAD_DIR, filename)
        
        with open(filepath, 'wb') as f:
            for chunk in video_response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        file_size = os.path.getsize(filepath)
        return {
            "mode": "download",
            "requested_url": video_url,
            "timestamp": datetime.utcnow().isoformat(),
            "downloaded_file": filepath,
            "file_size_bytes": file_size,
            "status": "success"
        }
    except Exception as e:
        return {"error": f"خطا در دانلود فایل: {str(e)}", "url": video_url}

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
