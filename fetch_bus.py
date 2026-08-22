import json
import re
from datetime import datetime
from html.parser import HTMLParser
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

STOPS = [
    {
        "id": "kasai-post",
        "name": "葛西郵便局",
        "route": "葛西24",
        "destination": "なぎさニュータウン行",
        "url": "https://tobus.jp/sp/blsys/stop/time?ud=1&poleno=2&ln=ja&stopid=2084&routecode=76",
    },
    {
        "id": "edogawa",
        "name": "江戸川車庫前",
        "route": "秋26",
        "destination": "葛西駅前行",
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


def parse_timetable(html, stop_id=""):
    """
    Parse Tokyo Bus timetable from HTML.
    Supports multiple HTML structures and formats.
    """
    parser = TextExtractor()
    parser.feed(html)
    text = parser.get_text()

    print(f"\n=== Parsing {stop_id} ===")
    print(f"Text length: {len(text)} chars")

    # Extract service note
    note_match = re.search(
        r"(\d{1,2}月\d{1,2}日の[^\n]*ダイヤで運行しております。)",
        text,
    )
    
    service_note = (
        note_match.group(1)
        if note_match
        else "当日の公式ダイヤ"
    )

    times = []
    
    # Strategy 1: Original pattern - look for "NNジ" (hour) followed by minutes
    print("Strategy 1: Looking for 'ジ' hour pattern...")
    hour_matches = list(re.finditer(r"(?m)^(\d{1,2})ジ$", text))
    print(f"  Found {len(hour_matches)} hour markers")
    
    if hour_matches:
        for i, match in enumerate(hour_matches):
            hour = int(match.group(1))

            if not 0 <= hour <= 23:
                continue

            section_start = match.end()
            section_end = (
                hour_matches[i + 1].start()
                if i + 1 < len(hour_matches)
                else len(text)
            )

            section = text[section_start:section_end]

            # Extract minutes from this hour section
            minutes = [
                int(x)
                for x in re.findall(
                    r"(?<!\d)([0-5]\d)(?!\d)",
                    section,
                )
            ]

            for minute in minutes:
                times.append(f"{hour:02d}:{minute:02d}")
    
    # Strategy 2: If no times found, try HH:MM format directly
    if not times:
        print("Strategy 2: Looking for HH:MM pattern...")
        time_pattern = re.findall(r"(\d{1,2}):([0-5]\d)", text)
        print(f"  Found {len(time_pattern)} time entries")
        for hour_str, minute_str in time_pattern:
            hour = int(hour_str)
            minute = int(minute_str)
            if 0 <= hour <= 23:
                times.append(f"{hour:02d}:{minute:02d}")
    
    # Strategy 3: If still no times, try looking for standalone 2-digit numbers
    # that could be minutes after hour indicators
    if not times:
        print("Strategy 3: Looking for alternative patterns...")
        # Look for patterns like "07" followed by "00 05 10" etc
        alt_pattern = re.findall(r"(\d{1,2})\s+([0-9]{2}\s+)+", text)
        print(f"  Found {len(alt_pattern)} alternative patterns")
    
    # Remove duplicates and sort
    times = sorted(
        set(times),
        key=lambda value: tuple(map(int, value.split(":"))),
    )

    print(f"Total unique times: {len(times)}")
    if times:
        print(f"Sample: {times[:5]}")
    
    if not times:
        raise ValueError("No timetable times found")

    return service_note, times


def main():
    now = datetime.now(ZoneInfo("Asia/Tokyo"))

    result = {
        "fetched_at": now.isoformat(timespec="seconds"),
        "date": now.strftime("%Y-%m-%d"),
        "stops": [],
    }

    for stop in STOPS:
        try:
            print(f"\n{'='*60}")
            print(f"Fetching: {stop['id']}")
            html = fetch_html(stop["url"])
            print(f"✓ HTML fetched ({len(html)} chars)")

            service_note, times = parse_timetable(html, stop["id"])

            result["stops"].append({
                **stop,
                "service_note": service_note,
                "times": times,
                "ok": True,
            })
            print(f"✓ {stop['id']} - {len(times)} times found")

        except Exception as exc:
            print(f"✗ {stop['id']} failed: {type(exc).__name__}: {exc}")
            import traceback
            traceback.print_exc()
            result["stops"].append({
                **stop,
                "service_note": "",
                "times": [],
                "ok": False,
                "error": str(exc),
            })

    print(f"\n{'='*60}")
    print(f"Results: {sum(1 for s in result['stops'] if s['ok'])} succeeded")
    
    if not any(stop["ok"] for stop in result["stops"]):
        raise RuntimeError("Failed to fetch all bus timetables")

    with open("bus_data.json", "w", encoding="utf-8") as file:
        json.dump(
            result,
            file,
            ensure_ascii=False,
            indent=2,
        )
        file.write("\n")

    print("✓ Successfully wrote bus_data.json")


if __name__ == "__main__":
    main()
