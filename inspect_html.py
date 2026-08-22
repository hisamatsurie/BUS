#!/usr/bin/env python3
"""
Test script to inspect Tokyo Bus timetable HTML structure
"""
import re
from html.parser import HTMLParser
from urllib.request import Request, urlopen

STOPS = [
    {
        "id": "kasai-post",
        "url": "https://tobus.jp/sp/blsys/stop/time?ud=1&poleno=2&ln=ja&stopid=2084&routecode=76",
    },
    {
        "id": "edogawa",
        "url": "https://tobus.jp/sp/blsys/stop/time?ud=2&poleno=2&ln=ja&stopid=310&routecode=81",
    },
]


class TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_data(self, data):
        text = data.strip()
        if text:
            self.parts.append(text)

    def get_text(self):
        return "\n".join(self.parts)


def fetch_html(url):
    request = Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept-Language": "ja,en;q=0.8",
            "Cache-Control": "no-cache",
            "Referer": "https://tobus.jp/",
        },
    )

    with urlopen(request, timeout=30) as response:
        raw = response.read()
        charset = response.headers.get_content_charset() or "utf-8"
        return raw.decode(charset, errors="replace")


for stop in STOPS:
    print(f"\n{'='*60}")
    print(f"Inspecting: {stop['id']}")
    print(f"URL: {stop['url']}")
    print('='*60)
    
    try:
        html = fetch_html(stop["url"])
        print(f"✓ HTML fetched successfully ({len(html)} chars)")
        
        parser = TextExtractor()
        parser.feed(html)
        text = parser.get_text()
        
        print(f"✓ Text extracted ({len(text)} chars)")
        print(f"\nFirst 1000 characters of extracted text:")
        print("-" * 60)
        print(text[:1000])
        print("-" * 60)
        
        # Look for patterns
        print(f"\nPattern analysis:")
        
        # 日本語の「ジ」を使った時間パターン
        hour_matches = list(re.finditer(r"(?m)^(\d{1,2})ジ$", text))
        print(f"  Hour pattern (ジ): {len(hour_matches)} matches")
        if hour_matches:
            print(f"    Examples: {[m.group(1) for m in hour_matches[:5]]}")
        
        # 数字のみのパターン（分）
        minute_matches = list(re.finditer(r"(?<!\d)([0-5]\d)(?!\d)", text))
        print(f"  Minute pattern ([0-5]\\d): {len(minute_matches)} matches")
        if minute_matches:
            print(f"    Examples: {[m.group(1) for m in minute_matches[:10]]}")
        
        # 時間フォーマット HH:MM
        time_pattern_matches = list(re.finditer(r"\d{1,2}:\d{2}", text))
        print(f"  Time pattern (HH:MM): {len(time_pattern_matches)} matches")
        if time_pattern_matches:
            print(f"    Examples: {[m.group(0) for m in time_pattern_matches[:10]]}")
        
        # 改正日を探す
        if "改正日" in text:
            print(f"  ✓ Contains '改正日'")
        else:
            print(f"  ✗ Does NOT contain '改正日'")
        
        # 月日パターンを探す
        date_matches = list(re.finditer(r"\d{1,2}月\d{1,2}日", text))
        print(f"  Date pattern (M月D日): {len(date_matches)} matches")
        if date_matches:
            print(f"    Examples: {[m.group(0) for m in date_matches[:5]]}")
        
        # 曜日パターン
        day_pattern = re.findall(r"(月|火|水|木|金|土|日)曜日", text)
        print(f"  Weekday pattern: {len(day_pattern)} matches - {day_pattern[:5] if day_pattern else 'None'}")
        
        # 重要な時間帯マーカーを探す
        if "平日" in text:
            print(f"  ✓ Contains '平日' (weekday)")
        if "土曜" in text:
            print(f"  ✓ Contains '土曜' (Saturday)")
        if "日祝" in text or "日曜" in text:
            print(f"  ✓ Contains holiday marker")
        
        print(f"\nLast 500 characters:")
        print("-" * 60)
        print(text[-500:])
        print("-" * 60)
        
    except Exception as e:
        print(f"✗ Error: {type(e).__name__}: {e}")

print("\n" + "="*60)
print("Analysis complete")
print("="*60)
