#!/usr/bin/env python3
"""GitHub 定时任务：检查臻海艺术新公告，有新公告就推送到手机（ntfy）。
每次运行只查一次；查过的公告编号保存在 seen_notices.json。
"""
import html, json, os, re, sys, urllib.request
from datetime import datetime, timedelta, timezone

API = ("https://api.shengtai.cyou/basic/notice?appid=__UNI__22FD095"
       "&version=1.4.2&platform=web&pageNo=1&cid=")
SEEN_FILE = "seen_notices.json"
TOPIC = os.environ.get("NTFY_TOPIC", "").strip()
CN = timezone(timedelta(hours=8))  # 北京时间
BOILER = re.compile(r"^(尊敬的.*用户[：:]?|您好[！!]?|敬请各位用户知悉.*|臻海艺术|\d{4}年\d{1,2}月\d{1,2}日)$")


def get(url, data=None, headers=None):
    req = urllib.request.Request(url, data=data, headers={"User-Agent": "Mozilla/5.0", **(headers or {})})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def core(content):
    text = re.sub(r"<br\s*/?>|</p>", "\n", content or "")
    text = html.unescape(re.sub(r"<[^>]+>", "", text))
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    return " ".join(l for l in lines if not BOILER.match(l))


def push(title, body):
    if not TOPIC:
        print("没有设置 NTFY_TOPIC，跳过推送")
        return
    payload = json.dumps({"topic": TOPIC, "title": title, "message": body, "priority": 4}).encode()
    get("https://ntfy.sh", payload, {"Content-Type": "application/json"})


def main():
    if "--test-push" in sys.argv:
        push("臻海艺术公告监控（GitHub）", "测试推送：GitHub 定时任务已连通，能收到这条说明设置成功。")
        print("测试推送已发送")
        return

    items = json.loads(get(API)).get("data") or []
    print(f"读取到 {len(items)} 条公告")

    if not os.path.exists(SEEN_FILE):  # 第一次运行：只记录，不推送
        json.dump(sorted(n["id"] for n in items), open(SEEN_FILE, "w"))
        print("首次运行，已记录现有公告")
        return

    seen = set(json.load(open(SEEN_FILE)))
    new = [n for n in items if n["id"] not in seen]
    for n in reversed(new):
        t = datetime.fromtimestamp(int(n["createTime"]) / 1000, CN)
        cat = (n.get("category") or {}).get("name", "")
        push(f"臻海艺术·{cat} {t:%H:%M}  {n['title']}", core(n.get("content")))
        print("已推送：", n["title"])
        seen.add(n["id"])
    if new:
        json.dump(sorted(seen), open(SEEN_FILE, "w"))
    else:
        print("没有新公告")


if __name__ == "__main__":
    main()
