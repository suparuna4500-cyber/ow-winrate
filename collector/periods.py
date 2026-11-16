"""過去シーズン（パッチ期間）の勝率アーカイブ。

公式の勝率はシーズン開始・中間パッチのたびにリセットされるため、
終わった期間の最終値を owherostats.com のシーズン統計ページから取り込み、
data/periods/<slug>.json に保存する。取得できなくても本体の収集は止めない。

  python collector/periods.py            # 新しく終わった期間だけ追加
  python collector/periods.py --import X # ブラウザで集めたJSONを取り込む
"""
import json, os, re, sys, datetime
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PDIR = f"{ROOT}/data/periods"
BASE = "https://owherostats.com"
RANKS = ["all", "Bronze", "Silver", "Gold", "Platinum", "Emerald", "Diamond", "Master", "Grandmaster"]
TIER = {"all": "All"}  # owherostats のランク名 → このサイトのランク名
INPUT = {"mnk": "PC", "controller": "Console"}
MODE = {"competitive": "2", "qp": "0"}
UA = {"User-Agent": "Mozilla/5.0 (ow-winrate archive; +https://github.com/suparuna4500-cyber/ow-winrate)",
      "Accept-Language": "ja"}


def norm(s):
    return re.sub(r"[^a-z0-9]", "", s.lower())


def ja_name(title):
    """英語のシーズン名から日本語ラベルを作る（例: Season 5 Midseason → シーズン5 後半）"""
    t = title.lower()
    m = re.search(r"season\s*(\d+)", t) or re.search(r"\bs(\d+)\b", t)
    mid = "mid" in t or "anniversary" in t
    if not m:
        return title
    return f"シーズン{m.group(1)} {'後半' if mid else '前半'}"


def jobs_for(korea=True):
    out = []
    for reg in (["Asia", "Korea"] if korea else ["Asia"]):
        for inp in (["mnk"] if reg == "Korea" else ["mnk", "controller"]):
            out += [(reg, inp, "competitive", rk) for rk in RANKS]
            out.append((reg, inp, "qp", "all"))
    return out


def combo_key(reg, inp, mode, rk):
    return f"{reg}_{MODE[mode]}_{INPUT[inp]}_{TIER.get(rk, rk)}"


def pack(res):
    """{'w':{slug:v},'p':{},'b':{}} → {'h':[ids],'m':{'all-maps':[w,p,b ×10 int]}}"""
    ids = sorted(set(res.get("w", {})) | set(res.get("p", {})))
    if not ids:
        return None
    flat = []
    for s in ids:
        for k in "wpb":
            v = res.get(k, {}).get(s)
            flat.append(None if v is None else round(v * 10))
    return {"h": [norm(s) for s in ids], "m": {"all-maps": flat}}


# ---- owherostats のHTML解析（bs4）
def parse_page(html):
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    out = {"w": {}, "p": {}, "b": {}}
    heads = {"ヒーロー勝率": "w", "ヒーローピック率": "p", "ヒーローバン率": "b"}
    for a in soup.select('a[href^="/ja/heroes/"]'):
        val = next((s.get_text(strip=True) for s in a.find_all("span")
                    if re.fullmatch(r"\d+(\.\d+)?%", s.get_text(strip=True))), None)
        if not val:
            continue
        p, key = a.parent, None
        for _ in range(8):
            if p is None:
                break
            h = p.find(["h2", "h3"])
            if h:
                key = heads.get(h.get_text(strip=True))
                break
            p = p.parent
        if key:
            out[key][a["href"].rsplit("/", 1)[-1]] = float(val[:-1])
    lab = {}
    for b in soup.find_all("button"):
        m = re.fullmatch(r"(ランク|地域|モード|入力デバイス)·(.+)", b.get_text(strip=True))
        if m:
            lab[m.group(1)] = m.group(2)
    text = soup.get_text(" ", strip=True)
    per = re.search(r"期間：\s*([0-9-]+)\s*→\s*([0-9-]+)", text)
    title = soup.find("h1").get_text(strip=True) if soup.find("h1") else ""
    nav = {}
    for a in soup.find_all("a"):
        t = a.get_text(strip=True)
        if ("前へ" in t or "次へ" in t) and "/seasons/" in (a.get("href") or ""):
            nav["prev" if "前へ" in t else "next"] = a["href"].rsplit("/", 1)[-1]
    return out, {"title": title, "start": per and per.group(1), "end": per and per.group(2), **nav}, lab


def fetch(slug, reg="Asia", inp="mnk", mode="competitive", rk="all"):
    import requests
    ck = {"ow_region": reg, "ow_input": inp, "ow_mode": mode, "ow_rank": rk}
    url = f"{BASE}/ja/seasons/{slug}" if slug else f"{BASE}/ja/seasons"
    for _ in range(3):
        try:
            r = requests.get(url, cookies=ck, headers=UA, timeout=60)
            if r.status_code == 200:
                return parse_page(r.text)
            print(f"  owherostats {r.status_code} {url}")
            if r.status_code in (403, 429, 503):
                return None
        except Exception as e:
            print("  owherostats error", e)
    return None


def load_index():
    try:
        return json.load(open(f"{PDIR}/index.json", encoding="utf-8"))
    except Exception:
        return {"periods": [], "current": None}


def save_period(slug, info, combos, idx):
    os.makedirs(PDIR, exist_ok=True)
    json.dump(combos, open(f"{PDIR}/{slug}.json", "w"), separators=(",", ":"))
    idx["periods"] = [p for p in idx["periods"] if p["id"] != slug]
    idx["periods"].append({"id": slug, "title": info["title"], "ja": info.get("ja") or ja_name(info["title"]),
                           "start": info["start"], "end": info["end"],
                           "regions": sorted({k.split("_")[0] for k in combos})})
    idx["periods"].sort(key=lambda p: p["start"] or "", reverse=True)


def write_index(idx):
    os.makedirs(PDIR, exist_ok=True)
    json.dump(idx, open(f"{PDIR}/index.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def scrape_period(slug, info):
    combos = {}

    def run(j):
        r = fetch(slug, *j)
        return j, r

    korea_ok = True
    first = fetch(slug, "Korea", "mnk", "competitive", "all")
    if not first or not first[0]["w"]:
        korea_ok = False
    with ThreadPoolExecutor(4) as ex:
        for j, r in ex.map(run, jobs_for(korea_ok)):
            if r and r[0]["w"]:
                pk = pack(r[0])
                if pk:
                    combos[combo_key(*j)] = pk
    return combos


def update():
    idx = load_index()
    known = {p["id"] for p in idx["periods"]}
    got = fetch(None)
    if not got:
        print("periods: owherostats に接続できないためスキップ")
        return
    _, info, _ = got
    # 最新の期間までたどる
    seen = 0
    while info.get("next") and seen < 5:
        nxt = fetch(info["next"])
        if not nxt:
            return
        slug = info["next"]
        info = nxt[1]
        info["slug"] = slug
        seen += 1
    cur_slug = info.get("slug")
    if not cur_slug and info.get("prev"):
        # /ja/seasons が最新ページそのものだった場合は前のページの「次へ」で名前を知る
        p = fetch(info["prev"])
        cur_slug = p and p[1].get("next")
    today = datetime.date.today().isoformat()
    idx["current"] = {**(idx.get("current") or {}), "id": cur_slug, "title": info["title"],
                      "ja": ja_name(info["title"]), "start": info["start"]}
    # 新しく終わった期間を遡って追加
    slug, guard = info.get("prev"), 0
    while slug and slug not in known and guard < 3:
        got = fetch(slug)
        if not got:
            break
        pinfo = got[1]
        if pinfo["end"] and pinfo["end"] < today:
            print(f"periods: {slug} を取り込み中")
            combos = scrape_period(slug, pinfo)
            if combos:
                save_period(slug, pinfo, combos, idx)
                print(f"periods: {slug} {len(combos)}件")
        slug, guard = pinfo.get("prev"), guard + 1
    write_index(idx)


def ko_name(title):
    """ネクソンのお知らせ題名（例: 탈론의 지배 - 5시즌 중간 패치…）→ シーズン5 後半"""
    m = re.search(r"(\d+)\s*시즌", title or "")
    if not m:
        return title
    return f"シーズン{m.group(1)} {'後半' if '중간' in title else '前半'}"


def rollover(news):
    """ネクソンの最新シーズンのお知らせが変わったら、いま data/latest にある数字
    （＝終わった期間の最後の値）を全マップ合計だけ過去シーズンとして保存する。"""
    if not news or not news.get("newsNo") or "시즌" not in (news.get("title") or ""):
        return
    idx = load_index()
    cur = idx.get("current") or {}
    if not cur.get("newsNo"):
        cur["newsNo"] = str(news["newsNo"])
        idx["current"] = cur
        write_index(idx)
        return
    if str(news["newsNo"]) == str(cur["newsNo"]):
        return
    d = datetime.datetime.strptime(news["createdAt"].strip(), "%Y.%m.%d").date()
    start_new = (d - datetime.timedelta(days=1)).isoformat()   # パッチは米国の日付（韓国の告知日の前日）
    end_old = (d - datetime.timedelta(days=2)).isoformat()
    old_id = cur.get("id") or f"p-{cur.get('start') or end_old}"
    if old_id not in {p["id"] for p in idx["periods"]}:
        import glob
        combos = {}
        for f in glob.glob(f"{ROOT}/data/latest/*.json"):
            key = os.path.basename(f)[:-5]
            if not key.startswith(("Asia_", "Korea_")):
                continue
            c = json.load(open(f))
            if c.get("m", {}).get("all-maps"):
                combos[key] = {"h": c["h"], "m": {"all-maps": c["m"]["all-maps"]}}
        if combos:
            save_period(old_id, {"title": cur.get("title") or old_id, "ja": cur.get("ja"),
                                 "start": cur.get("start"), "end": end_old}, combos, idx)
            print(f"periods: {old_id} を過去シーズンとして保存（{len(combos)}件）")
    idx["current"] = {"id": f"p-{start_new}", "title": news["title"], "ja": ko_name(news["title"]),
                      "start": start_new, "newsNo": str(news["newsNo"])}
    write_index(idx)


def import_browser(path):
    """ブラウザで集めた {"slug|reg|inp|mode|rk": {w,p,b,lab}, "_info": {slug: {...}}} を取り込む"""
    raw = json.load(open(path, encoding="utf-8"))
    infos = raw.pop("_info")
    cur = raw.pop("_current", None)
    idx = load_index()
    by = {}
    for key, res in raw.items():
        slug, reg, inp, mode, rk = key.split("|")
        pk = pack(res)
        if pk:
            by.setdefault(slug, {})[combo_key(reg, inp, mode, rk)] = pk
    for slug, combos in by.items():
        save_period(slug, infos[slug], combos, idx)
        print(slug, len(combos))
    if cur:
        idx["current"] = cur
    write_index(idx)


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "--import":
        import_browser(sys.argv[2])
    else:
        try:
            update()
        except Exception as e:
            print("periods: エラーのためスキップ", e)
