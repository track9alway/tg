import requests
from bs4 import BeautifulSoup
import json
import sys
import re
import os
from urllib.parse import quote_plus
from datetime import datetime

def search_and_scrape(query):
    encoded_query = quote_plus(query)
    base_url = "https://www.pornhub.com"
    search_url = f"{base_url}/search?search={encoded_query}"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    try:
        response = requests.get(search_url, headers=headers, timeout=30)
        response.raise_for_status()
    except requests.RequestException as e:
        return {"error": str(e), "query": query}
    
    soup = BeautifulSoup(response.text, 'html.parser')
    links = []
    
    for a in soup.find_all('a', href=True):
        href = a['href']
        if '/view_video.php?viewkey=' in href or '/video/' in href:
            full_url = href if href.startswith('http') else base_url + href
            links.append(full_url)
    
    unique_links = list(dict.fromkeys(links))
    
    return {
        "query": query,
        "timestamp": datetime.utcnow().isoformat(),
        "result_count": len(unique_links),
        "results": unique_links
    }

def save_results(data):
    output_file = "results.json"
    existing_data = []
    
    if os.path.exists(output_file):
        with open(output_file, 'r', encoding='utf-8') as f:
            existing_data = json.load(f)
    
    existing_data.append(data)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(existing_data, f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        query = sys.argv[1]
        results = search_and_scrape(query)
        save_results(results)
        print(f"تعداد نتایج ذخیره شده: {results['result_count']}")
    else:
        print("لطفاً عبارت جستجو را وارد کنید.")
        sys.exit(1)
