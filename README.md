# BUS
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
        "url": "https://tobus.jp/sp/blsys/stop/time?routecode=81&poleno=2&stopid=310&ln=ja",
    },
]


class TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_data(self, data):
        self.parts.append(data)

    def text(self):
        return " ".join(self.parts)


def fetch_text(url):
    req = Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; BUS-timetable/1.0)",
            "Accept-Language": "ja,en;q=0.8",
            "Cache-Control": "no-cache",
        },
    )

    with urlopen(req, timeout=30) as response:
        raw = response.read()
        charset = response.headers.get_content_charset() or "utf-8"

        return raw.decode(
            charset,
            errors="replace"
        )


def parse_timetable(html):
    parser = TextExtractor()
    parser.feed(html)

    text = re.sub(
        r"\s+",
        " ",
        parser.text()
    ).strip()

    note_match = re.search(
        r"(\d{1,2}月\d{1,2}日.*?ダイヤで運行しております。)",
        text
    )

    service_note = (
        note_match.group(1)
        if note_match
        else "当日の公式ダイヤ"
    )

    start = text.find(
        "すべての時間帯を表示する"
    )

    if start == -1:
        start = text.find(
            "改正日："
        )

    section = (
        text[start:]
        if start != -1
        else text
    )

    end = section.find(
        "このバス停の他の系統を見る"
    )

    if end != -1:
        section = section[:end]

    times = []

    hour_pattern = re.compile(
        r"(?<!\d)(\d{1,2})\s*ジ(.*?)(?=(?<!\d)\d{1,2}\s*ジ|$)"
    )

    for match in hour_pattern.finditer(
        section
    ):

        hour = int(
            match.group(1)
        )

        if not 0 <= hour <= 23:
            continue

        minutes = [
            int(x)
            for x in re.findall(
                r"(?<!\d)([0-5]\d)(?!\d)",
                match.group(2)
            )
        ]

        for minute in minutes:

            times.append(
                f"{hour:02d}:{minute:02d}"
            )

    times = sorted(
        set(times),
        key=lambda x:
            tuple(
                map(
                    int,
                    x.split(":")
                )
            )
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
            now.isoformat(
                timespec="seconds"
            ),

        "date":
            now.strftime(
                "%Y-%m-%d"
            ),

        "stops": []
    }

    for stop in STOPS:

        try:

            html = fetch_text(
                stop["url"]
            )

            service_note, times = (
                parse_timetable(
                    html
                )
            )

            item = {
                **stop,
                "service_note":
                    service_note,
                "times":
                    times,
                "ok":
                    True
            }

        except Exception as exc:

            item = {
                **stop,
                "service_note": "",
                "times": [],
                "ok": False,
                "error": str(exc)
            }

        result[
            "stops"
        ].append(
            item
        )

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
        encoding="utf-8"
    ) as f:

        json.dump(
            result,
            f,
            ensure_ascii=False,
            indent=2
        )

        f.write("\n")


if __name__ == "__main__":
    main()
