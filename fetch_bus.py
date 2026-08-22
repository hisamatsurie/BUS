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
            "User-Agent": "Mozilla/5.0",
            "Accept-Language": "ja,en;q=0.8",
            "Cache-Control": "no-cache",
        },
    )

    with urlopen(request, timeout=30) as response:
        raw = response.read()
        charset = response.headers.get_content_charset() or "utf-8"
        return raw.decode(charset, errors="replace")


def parse_timetable(html):
    parser = TextExtractor()
    parser.feed(html)
    text = parser.get_text()

    note_match = re.search(
        r"(\d{1,2}月\d{1,2}日の[^\n]*ダイヤで運行しております。)",
        text,
    )

    service_note = (
        note_match.group(1)
        if note_match
        else "当日の公式ダイヤ"
    )

    start = text.find("改正日：")

    if start != -1:
        text = text[start:]

    end = text.find(
        "このバス停の他の系統を見る"
    )

    if end != -1:
        text = text[:end]

    times = []

    hour_matches = list(
        re.finditer(
            r"(?m)^(\d{1,2})ジ$",
            text
        )
    )

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

        section = text[
            section_start:section_end
        ]

        minutes = [
            int(x)
            for x in re.findall(
                r"(?<!\d)([0-5]\d)(?!\d)",
                section,
            )
        ]

        for minute in minutes:
            times.append(
                f"{hour:02d}:{minute:02d}"
            )

    times = sorted(
        set(times),
        key=lambda value:
        tuple(map(int, value.split(":"))),
    )

    if not times:
        raise ValueError(
            "No timetable times found"
        )

    return service_note, times


def main():
    now = datetime.now(
        ZoneInfo("Asia/Tokyo")
    )

    result = {
        "fetched_at":
            now.isoformat(timespec="seconds"),
        "date":
            now.strftime("%Y-%m-%d"),
        "stops": [],
    }

    for stop in STOPS:
        try:
            html = fetch_html(stop["url"])

            service_note, times = (
                parse_timetable(html)
            )

            result["stops"].append({
                **stop,
                "service_note": service_note,
                "times": times,
                "ok": True,
            })

        except Exception as exc:
            result["stops"].append({
                **stop,
                "service_note": "",
                "times": [],
                "ok": False,
                "error": str(exc),
            })

    if not any(
        stop["ok"]
        for stop in result["stops"]
    ):
        raise RuntimeError(
            "Failed to fetch all bus timetables"
        )

    with open(
        "bus_data.json",
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            result,
            file,
            ensure_ascii=False,
            indent=2,
        )
        file.write("\n")


if __name__ == "__main__":
    main()
