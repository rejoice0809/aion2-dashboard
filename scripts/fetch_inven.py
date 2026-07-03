"""
아이온2 인벤 게시판에서 최신 글 '제목 + 링크 + 날짜'만 수집합니다.
본문 내용은 저작권 문제로 가져오지 않고, 사용자가 클릭해서 원문을 보도록 링크만 제공합니다.
GitHub Actions에서 매시간 실행되어 data/latest.json 을 갱신합니다.
"""
import json
import re
import time
from datetime import datetime, timezone, timedelta
import urllib.request

BOARDS = {
    "assassin": {"label": "살성 게시판", "url": "https://www.inven.co.kr/board/aion2/6449"},
    "gladiator": {"label": "검성 게시판", "url": "https://www.inven.co.kr/board/aion2/6448"},
    "general": {"label": "자유 게시판(패치노트 등)", "url": "https://www.inven.co.kr/board/aion2/6388"},
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
}

# 인벤 게시판 리스트에서 흔히 쓰이는 글 링크 패턴: /board/aion2/{board_id}/{article_no}
LINK_PATTERN = re.compile(r'href="(/board/aion2/\d+/\d+[^"]*)"[^>]*(?:title="([^"]*)")?')
TITLE_TAG_PATTERN = re.compile(
    r'<a[^>]+href="(/board/aion2/\d+/\d+[^"]*)"[^>]*class="[^"]*(?:subject|tit)[^"]*"[^>]*>(.*?)</a>',
    re.IGNORECASE | re.DOTALL,
)
TAG_STRIP = re.compile(r"<[^>]+>")


def clean(text: str) -> str:
    text = TAG_STRIP.sub("", text)
    return re.sub(r"\s+", " ", text).strip()


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=15) as resp:
        return resp.read().decode("utf-8", errors="replace")


def extract_posts(html: str, base_url: str, limit: int = 8):
    posts = []
    seen = set()

    matches = TITLE_TAG_PATTERN.findall(html)
    if not matches:
        # 폴백: class 매칭이 실패하면 일반 링크 패턴으로 재시도
        matches = [(m.group(1), m.group(2) or "") for m in LINK_PATTERN.finditer(html)]

    for href, raw_title in matches:
        title = clean(raw_title)
        if not title or len(title) < 2:
            continue
        if href in seen:
            continue
        seen.add(href)
        full_url = href if href.startswith("http") else f"https://www.inven.co.kr{href}"
        posts.append({"title": title, "url": full_url})
        if len(posts) >= limit:
            break
    return posts


def main():
    result = {
        "updated_at": datetime.now(timezone(timedelta(hours=9))).strftime("%Y-%m-%d %H:%M KST"),
        "boards": {},
    }

    for key, board in BOARDS.items():
        try:
            html = fetch(board["url"])
            posts = extract_posts(html, board["url"])
        except Exception as e:  # noqa: BLE001
            posts = []
            result.setdefault("errors", {})[key] = str(e)
        result["boards"][key] = {"label": board["label"], "source": board["url"], "posts": posts}
        time.sleep(1)  # 과도한 요청 방지

    with open("data/latest.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print("saved data/latest.json")


if __name__ == "__main__":
    main()
