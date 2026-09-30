#!/usr/bin/env python3
"""아침 브리핑 페이지 생성기.

사용법: python3 build.py data/today.json
- today.json 을 검증하고 data/days/YYYY-MM-DD.json 으로 저장
- index.html(오늘) / prev.html(전날) 생성
- data/meta.json 회차 갱신, data/dedup.json 에 오늘 기사 추가 및 7일 초과분 삭제
같은 날짜로 다시 실행하면 회차를 올리지 않고 덮어쓴다.
"""
import datetime as dt
import html
import json
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
P = lambda *a: os.path.join(ROOT, *a)
e = html.escape
WD = "월화수목금토일"

SUN = '<svg viewBox="0 0 32 32" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" aria-hidden="true"><circle cx="16" cy="16" r="5.5"/><path d="M16 3.5v3M16 25.5v3M3.5 16h3M25.5 16h3M7.2 7.2l2.1 2.1M22.7 22.7l2.1 2.1M7.2 24.8l2.1-2.1M22.7 9.3l2.1-2.1"/></svg>'
CLOUD_PATH = '<path d="M9 20h14a5 5 0 0 0 .4-10 7 7 0 0 0-13.3 1.6A4.2 4.2 0 0 0 9 20z"/>'
ICONS = {
    "sun": SUN,
    "sun_cloud": '<svg viewBox="0 0 32 32" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" aria-hidden="true"><circle cx="11" cy="11" r="4"/><path d="M11 3.5v1.5M3.5 11h1.5M5.7 5.7l1 1M16.3 5.7l-1 1"/><path d="M11 25h13a4.5 4.5 0 0 0 0-9 6 6 0 0 0-11.5 1.5A3.8 3.8 0 0 0 11 25z" fill="var(--surface)"/></svg>',
    "cloud": '<svg viewBox="0 0 32 32" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" aria-hidden="true"><path d="M9 23h14a5 5 0 0 0 .4-10 7 7 0 0 0-13.3 1.6A4.2 4.2 0 0 0 9 23z"/></svg>',
    "rain": '<svg viewBox="0 0 32 32" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" aria-hidden="true">' + CLOUD_PATH + '<path d="M11 23.5l-1.2 3.5M16 23.5l-1.2 3.5M21 23.5l-1.2 3.5"/></svg>',
    "heavy_rain": '<svg viewBox="0 0 32 32" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" aria-hidden="true">' + CLOUD_PATH + '<path d="M9 23l-2 5M13.5 23l-2 5M18 23l-2 5M22.5 23l-2 5"/></svg>',
    "snow": '<svg viewBox="0 0 32 32" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" aria-hidden="true">' + CLOUD_PATH + '<path d="M11 24v4M9 26h4M18 24v4M16 26h4"/></svg>',
    "thunder": '<svg viewBox="0 0 32 32" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' + CLOUD_PATH + '<path d="M17 21l-3 5h4l-3 5"/></svg>',
}
AQ = {"좋음": "g1", "보통": "g2", "나쁨": "g3", "매우나쁨": "g4"}
SECTORS = [("econ", "시사경제"), ("world", "국제"), ("politics", "정치"), ("it", "IT/AI"), ("culture", "문화")]


def fail(msg):
    sys.exit("BUILD ERROR: " + msg)


def load(path, default=None):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return default


def save(path, obj):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)


def validate(d):
    try:
        dt.date.fromisoformat(d["date"])
    except Exception:
        fail("date 는 YYYY-MM-DD 형식이어야 함")
    w = d.get("weather") or fail("weather 없음")
    for k in ("min", "max", "am_text", "am_icon", "pm_text", "pm_icon", "humidity", "rain", "pm10", "pm25"):
        if k not in w:
            fail(f"weather.{k} 없음")
    for k in ("am_icon", "pm_icon"):
        if w[k] not in ICONS:
            fail(f"weather.{k} 는 {list(ICONS)} 중 하나")
    for k in ("pm10", "pm25"):
        if w[k] not in AQ:
            fail(f"weather.{k} 는 {list(AQ)} 중 하나")
    mk = d.get("markets")
    if mk is not None:
        if len(mk) != 3:
            fail("markets 는 3개 또는 null(일요일)")
        for m in mk:
            for k in ("name", "value", "pct", "closes"):
                if k not in m:
                    fail(f"markets.{k} 없음")
            if len(m["closes"]) < 2:
                fail("markets.closes 는 2개 이상")
    secs = d.get("sectors") or fail("sectors 없음")
    ids = [s["id"] for s in secs]
    if ids != [i for i, _ in SECTORS]:
        fail(f"sectors 순서는 {[i for i, _ in SECTORS]}")
    urls = set()
    for s in secs:
        if len(s["articles"]) != 3:
            fail(f"{s['id']} 기사는 3건이어야 함")
        for a in s["articles"]:
            for k in ("fixed", "tag1", "tag2", "source", "time", "title", "url", "summary"):
                if k not in a:
                    fail(f"{s['id']} 기사에 {k} 없음")
            if len(a["summary"]) > 210:
                fail(f"요약 200자 초과: {a['title']}")
            if a["url"] in urls:
                fail(f"같은 기사 중복: {a['url']}")
            urls.add(a["url"])
    return urls


def spark(vals, cls):
    lo, hi = min(vals), max(vals)
    r = (hi - lo) or 1
    n = len(vals)
    pts = [(i * 100 / (n - 1), 3 + 24 * (1 - (v - lo) / r)) for i, v in enumerate(vals)]
    d = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    ex, ey = pts[-1]
    return (f'<svg class="spark {cls}" viewBox="0 0 100 30" preserveAspectRatio="none" aria-hidden="true">'
            f'<polyline points="{d}" fill="none" stroke="currentColor" stroke-width="1.6" vector-effect="non-scaling-stroke" stroke-linejoin="round"/>'
            f'<circle cx="{ex:.1f}" cy="{ey:.1f}" r="2.2" fill="currentColor"/></svg>')


def pct_cls(p):
    return "flat" if abs(p) < 0.001 else ("up" if p > 0 else "down")


def pct_fmt(p):
    if abs(p) < 0.001:
        return "0.00%"
    s = "+" if p > 0 else ""
    return s + (f"{p:.3f}%" if abs(p) < 0.01 else f"{p:.2f}%")


def render(d, meta_line, prev_href, next_href):
    day = dt.date.fromisoformat(d["date"])
    title = f"{day:%y%m%d}({WD[day.weekday()]}) 아침 브리핑"
    head = open(P("template", "head.html"), encoding="utf-8").read().replace("{{TITLE}}", e(title))
    w = d["weather"]

    def nav(href, label, sym):
        if href:
            return f'<a class="nav" href="{href}" aria-label="{label}">{sym}</a>'
        return f'<span class="nav off" aria-hidden="true">{sym}</span>'

    wx = f'''<div class="wxbox" aria-label="서울 날씨">
      <div class="wxhead"><span class="city">서울</span><span class="hl">{e(str(w["min"]))}℃~{e(str(w["max"]))}℃</span></div>
      <div class="wxlines">
        <div class="wxline">{ICONS[w["am_icon"]]}<span class="when">오전</span><span>{e(w["am_text"])}</span></div>
        <div class="wxline">{ICONS[w["pm_icon"]]}<span class="when">오후</span><span>{e(w["pm_text"])}</span></div>
      </div>
      <div class="wxgrid">
        <div><span class="k">습도</span><b>{(e(str(w["humidity"])) + "%") if w.get("humidity") is not None else "—"}</b></div>
        <div><span class="k">미세먼지</span><span class="aq {AQ[w["pm10"]]}">{e(w["pm10"])}</span></div>
        <div><span class="k">강수량</span><b>{e(str(w["rain"]))}</b></div>
        <div><span class="k">초미세먼지</span><span class="aq {AQ[w["pm25"]]}">{e(w["pm25"])}</span></div>
      </div>
    </div>'''
    mk = ""
    if d.get("markets"):
        boxes = ""
        for m in d["markets"]:
            c = pct_cls(m["pct"])
            boxes += (f'<div class="box"><div class="lbl"><span>{e(m["name"])}</span><span class="val {c}">{pct_fmt(m["pct"])}</span></div>'
                      f'<div class="num">{e(str(m["value"]))}</div>{spark(m["closes"], c)}</div>')
        mk = f'<div class="strip" aria-label="시장 지표">{boxes}</div>'

    secs = ""
    names = dict(SECTORS)
    for s in d["sectors"]:
        cards = ""
        for a in s["articles"]:
            extra = ""
            if a.get("deadline"):
                extra += f'<span class="due">마감 {e(a["deadline"])}</span>'
            if a.get("age"):
                extra += f'<span class="old">{e(a["age"])}</span>'
            orig = f'<p class="orig">{e(a["orig"])}</p>' if a.get("orig") else ""
            cards += (f'<article class="card"><div class="meta"><span class="tag{" fill" if a["fixed"] else ""}">{e(a["tag1"])}</span>'
                      f'<span class="tag">{e(a["tag2"])}</span><span>{e(a["source"])}</span><span class="tm">{e(a["time"])}</span>{extra}</div>'
                      f'{orig}<a href="{e(a["url"])}" target="_blank" rel="noopener">{e(a["title"])}</a>'
                      f'<p class="sum">{e(a["summary"])}</p></article>')
        secs += f'<section class="sector" id="{s["id"]}"><h2>{names[s["id"]]}</h2><div class="list">{cards}</div></section>'
    navbar = "".join(f'<a href="#{i}">{n}</a>' for i, n in SECTORS)
    body = f'''<div class="wrap">
  <header class="top">
    <div class="datebar">
      {nav(prev_href, "전날 브리핑", "‹")}
      <div class="date"><strong>{e(title)}</strong><span class="round">{e(meta_line)}</span></div>
      {nav(next_href, "오늘 브리핑", "›")}
    </div>
    {wx}
    {mk}
  </header>
  <nav class="sectors" aria-label="섹터 바로가기"><div class="row">{navbar}</div></nav>
  <main>{secs}</main>
</div>
</body>
</html>
'''
    return head + body


def main():
    if len(sys.argv) != 2:
        fail("사용법: python3 build.py data/today.json")
    d = load(sys.argv[1]) or fail("입력 파일을 읽을 수 없음")
    urls = validate(d)
    today = dt.date.fromisoformat(d["date"])

    meta = load(P("data", "meta.json"), {"last_round": 0, "last_date": None})
    dedup = load(P("data", "dedup.json"), {"retention_days": 7, "days": {}})

    same_day = meta.get("last_date") == d["date"]
    rnd = meta["last_round"] if same_day else meta["last_round"] + 1

    # 중복 검사: 오늘 이전 기록과 겹치면 중단
    for day, items in dedup["days"].items():
        if day == d["date"]:
            continue
        seen = {x["url"] for x in items}
        dup = urls & seen
        if dup:
            fail(f"{day} 브리핑과 중복된 기사: {sorted(dup)}")

    iso = today.isocalendar()
    d["_meta_line"] = f"{iso[1]:02d}주차 · {rnd}회차 브리핑"
    os.makedirs(P("data", "days"), exist_ok=True)
    save(P("data", "days", f"{d['date']}.json"), d)

    # 전날 데이터
    prev_date = None if same_day else meta.get("last_date")
    if same_day:
        prev_date = meta.get("prev_date")
    prev_json = load(P("data", "days", f"{prev_date}.json")) if prev_date else None

    if prev_json:
        with open(P("prev.html"), "w", encoding="utf-8") as f:
            f.write(render(prev_json, prev_json.get("_meta_line", ""), None, "./"))
    elif not same_day and os.path.exists(P("index.html")):
        # 데이터 파일이 없는 이전 페이지(수동 제작)는 그대로 옮기고 화살표만 고친다
        old = open(P("index.html"), encoding="utf-8").read()
        old = old.replace('<button type="button" aria-label="다음 날짜" disabled>›</button>',
                          '<a href="./" aria-label="오늘 브리핑" style="display:inline-flex;align-items:center;justify-content:center;width:32px;height:32px;border:1px solid var(--line);border-radius:6px;color:var(--fg);text-decoration:none">›</a>')
        with open(P("prev.html"), "w", encoding="utf-8") as f:
            f.write(old)
    has_prev = os.path.exists(P("prev.html")) and (prev_date is not None)

    with open(P("index.html"), "w", encoding="utf-8") as f:
        f.write(render(d, d["_meta_line"], "prev.html" if has_prev else None, None))

    # 오래된 일자 데이터 정리: 오늘·전날만 남김
    keep = {d["date"], prev_date}
    for fn in os.listdir(P("data", "days")):
        if fn.endswith(".json") and fn[:-5] not in keep:
            os.remove(P("data", "days", fn))

    # 중복 기록: 오늘 추가, 7일 초과분 삭제
    dedup["days"][d["date"]] = [{"url": a["url"], "title": a["title"]} for s in d["sectors"] for a in s["articles"]]
    cutoff = today - dt.timedelta(days=dedup.get("retention_days", 7))
    dedup["days"] = {k: v for k, v in sorted(dedup["days"].items()) if dt.date.fromisoformat(k) > cutoff}
    save(P("data", "dedup.json"), dedup)

    meta.update({"last_round": rnd, "last_date": d["date"], "prev_date": prev_date})
    save(P("data", "meta.json"), meta)
    print(f"OK {d['date']} {d['_meta_line']} prev={prev_date}")


if __name__ == "__main__":
    main()
