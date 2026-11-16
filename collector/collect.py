#!/usr/bin/env python3
"""
Overwatch hero win/pick/ban rate collector.

- Americas / Asia / Europe : Blizzard official  https://overwatch.blizzard.com/en-us/rates/
- Korea                    : Nexon official     https://overwatch.nexon.com/hero/rate

Overwrites one compact file per (region, mode, input, tier):
  data/latest/<Region>_<rq>_<Input>_<Tier>.json
  {"h": [hero ids...], "m": {"<map>": [w,p,b, w,p,b, ...]}}   (values x10, int; null = no data)
refreshes data/index.json (hero/map metadata, fetch times), adds icons for new heroes,
and rebuilds index.html (the site) with the data embedded.

Run:  python collector/collect.py
      python collector/collect.py --only Korea
"""
import argparse
import concurrent.futures as cf
import datetime as dt
import json
import os
import re
import sys
import time

import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from meta import HERO_JA, MAPS as MAP_META, MAP_TYPE_JA  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
JST = dt.timezone(dt.timedelta(hours=9))

MAPS = ["all-maps", "antarctic-peninsula", "busan", "ilios", "lijiang-tower", "nepal", "oasis", "samoa",
        "circuit-royal", "dorado", "grimsvotn", "havana", "junkertown", "rialto", "route-66",
        "shambali-monastery", "watchpoint-gibraltar", "aatlis", "new-junk-city", "suravasa",
        "blizzard-world", "eichenwalde", "hollywood", "kings-row", "midtown", "neon-junction", "numbani",
        "paraiso", "colosseo", "esperanca", "new-queen-street", "runasapi"]
TIERS = ["All", "Bronze", "Silver", "Gold", "Platinum", "Emerald", "Diamond", "Master", "Grandmaster"]
BLIZZ_REGIONS = ["Asia", "Americas", "Europe"]
INPUTS = ["PC", "Console"]

UA = {"User-Agent": "Mozilla/5.0 (ow-winrate collector; personal, once-daily)",
      "Accept-Language": "ko-KR,ko;q=0.9,ja;q=0.8,en;q=0.7"}
S = requests.Session()
S.headers.update(UA)


def norm(hid):
    """Normalize hero ids across sources (soldier-76 / soldier76, d-va / dva...)."""
    return re.sub(r"[^a-z0-9]", "", hid.lower())


def get(url, kind):
    last = None
    for attempt in range(4):
        try:
            r = S.get(url, timeout=30)
            if r.status_code == 200:
                return r.json() if kind == "json" else r.text
            last = f"HTTP {r.status_code}"
        except Exception as e:  # noqa
            last = repr(e)
        time.sleep(2 + attempt * 3)
    raise RuntimeError(f"{url}: {last}")


# ---------- Blizzard ----------
def blizz_job(region, rq, inp, tier, mp):
    url = (f"https://overwatch.blizzard.com/en-us/rates/data/?input={inp}&map={mp}"
           f"&region={region}&role=All&rq={rq}&tier={tier}")
    d = get(url, "json")
    out, meta = {}, {}
    for x in d["rates"]["rates"]:
        hid = norm(x["id"])
        c = x["cells"]
        out[hid] = [c.get("winrate"), c.get("pickrate"), c.get("banrate")]
        h = x.get("hero", {})
        meta[hid] = {"en": h.get("name") or c.get("name"), "role": (h.get("role") or "").lower(),
                     "sub": h.get("subrole"), "color": h.get("color"), "img": h.get("portrait")}
    return out, meta


# ---------- Nexon (Korea) ----------
NUXT_RE = re.compile(r'<script[^>]*id="__NUXT_DATA__"[^>]*>(.*?)</script>', re.S)
WRAP = {"ShallowReactive", "Reactive", "Ref", "ShallowRef", "EmptyRef"}


def devalue(arr):
    memo = {}

    def v(i):
        if not isinstance(i, int) or isinstance(i, bool):
            return i
        if i in memo:
            return memo[i]
        x = arr[i]
        if isinstance(x, list):
            if x and isinstance(x[0], str) and x[0] in WRAP:
                r = v(x[1]); memo[i] = r; return r
            r = []; memo[i] = r
            r.extend(v(e) for e in x)
            return r
        if isinstance(x, dict):
            r = {}; memo[i] = r
            for k, e in x.items():
                r[k] = v(e)
            return r
        return x
    return v(0)


def nexon_job(rq, tier, mp):
    nmap = "all" if mp == "all-maps" else mp
    url = (f"https://overwatch.nexon.com/hero/rate?role=all&rq={rq}&rank={tier.lower()}"
           f"&map={nmap}&input=pc&region=korea")
    html = get(url, "text")
    m = NUXT_RE.search(html)
    if not m:
        raise RuntimeError(f"{url}: __NUXT_DATA__ not found")
    root = devalue(json.loads(m.group(1)))
    lst = root["data"]["hero-rate-list"]["data"]["list"]
    out, meta = {}, {}
    for x in lst:
        hid = norm(x["heroId"])
        out[hid] = [x.get("winRate"), x.get("pickRate"), x.get("banRate")]
        meta[hid] = {"ko": x.get("name"), "role": (x.get("role") or "").lower(), "sub": x.get("subrole"),
                     "color": x.get("colorCode"), "img_ko": x.get("thumbnailUrl")}
    return out, meta


def pack(per_map):
    heroes = sorted({h for m in per_map.values() for h in m})
    def i10(v):
        return None if v is None else int(round(float(v) * 10))
    out = {"h": heroes, "m": {}}
    for mp in MAPS:
        if mp not in per_map:
            continue
        flat = []
        for h in heroes:
            flat.extend(i10(v) for v in per_map[mp].get(h, [None, None, None]))
        out["m"][mp] = flat
    return out


def write_combo(key, per_map):
    d = os.path.join(DATA, "latest")
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, key + ".json"), "w", encoding="utf-8") as f:
        json.dump(pack(per_map), f, separators=(",", ":"))


def update_index(meta, asof):
    p = os.path.join(DATA, "index.json")
    idx = json.load(open(p, encoding="utf-8")) if os.path.exists(p) else {}
    heroes = idx.get("heroes", {})
    for hid, m in meta.items():
        h = heroes.setdefault(hid, {})
        for k, v in m.items():
            if v:
                h[k] = v
    for hid, h in heroes.items():
        h["ja"] = HERO_JA.get(hid) or h.get("ja") or h.get("en") or h.get("ko") or hid
    idx["heroes"] = heroes
    idx["maps"] = [{"id": m, "ja": ja, "type": t} for m, ja, t in MAP_META]
    idx["mapTypes"] = MAP_TYPE_JA
    idx.setdefault("asof", {}).update(asof)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(idx, f, ensure_ascii=False, indent=1)
    return idx


def update_icons(idx):
    """Add a small round-croppable icon (data URI) for any hero that does not have one yet."""
    p = os.path.join(DATA, "img.json")
    imgs = json.load(open(p)) if os.path.exists(p) else {}
    missing = [h for h in idx["heroes"] if h not in imgs]
    if not missing:
        return
    try:
        import base64, io
        from PIL import Image
    except ImportError:
        print("Pillow not installed; skipping icons"); return
    for hid in missing:
        h = idx["heroes"][hid]
        url = h.get("img_ko") or h.get("img")
        if not url:
            continue
        try:
            r = S.get(url, timeout=30); r.raise_for_status()
            im = Image.open(io.BytesIO(r.content)).convert("RGBA")
            s = min(im.size)
            im = im.crop(((im.width - s) // 2, (im.height - s) // 2, (im.width + s) // 2, (im.height + s) // 2)).resize((64, 64), Image.LANCZOS)
            buf = io.BytesIO(); im.save(buf, "WEBP", quality=82)
            imgs[hid] = "data:image/webp;base64," + base64.b64encode(buf.getvalue()).decode()
            print("icon added:", hid)
        except Exception as e:  # noqa
            print("icon failed:", hid, e)
    with open(p, "w") as f:
        json.dump(imgs, f)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", choices=["Korea", "Blizzard"], default=None)
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args()

    jobs = []
    if a.only != "Korea":
        for region in BLIZZ_REGIONS:
            for inp in INPUTS:
                for tier in TIERS:
                    for mp in MAPS:
                        jobs.append(("B", region, "2", inp, tier, mp))
                for mp in MAPS:
                    jobs.append(("B", region, "0", inp, "All", mp))
    if a.only != "Blizzard":
        for tier in TIERS:
            for mp in MAPS:
                jobs.append(("N", "Korea", "2", "PC", tier, mp))
        for mp in MAPS:
            jobs.append(("N", "Korea", "0", "PC", "All", mp))

    results, meta, errors = {}, {}, []

    def run(j):
        src, region, rq, inp, tier, mp = j
        if src == "B":
            return j, blizz_job(region, rq, inp, tier, mp)
        return j, nexon_job(rq, tier, mp)

    t0 = time.time()
    with cf.ThreadPoolExecutor(a.workers) as ex:
        futs = [ex.submit(run, j) for j in jobs]
        for n, f in enumerate(cf.as_completed(futs), 1):
            try:
                j, (out, m) = f.result()
            except Exception as e:  # noqa
                errors.append(str(e)); continue
            _, region, rq, inp, tier, mp = j
            results.setdefault(f"{region}_{rq}_{inp}_{tier}", {})[mp] = out
            for hid, mm in m.items():
                meta.setdefault(hid, {}).update({k: v for k, v in mm.items() if v})
            if n % 200 == 0:
                print(f"{n}/{len(jobs)}  {time.time()-t0:.0f}s", flush=True)

    now = dt.datetime.now(JST).strftime("%Y-%m-%d %H:%M")
    for key, per_map in results.items():
        if per_map.get("all-maps"):
            write_combo(key, per_map)
    asof = {}
    if any(k.startswith("Korea_") for k in results):
        asof["Korea"] = now
    if any(not k.startswith("Korea_") for k in results):
        asof["Blizzard"] = now
    idx = update_index(meta, asof)
    update_icons(idx)
    import subprocess
    subprocess.run([sys.executable, os.path.join(ROOT, "site", "build.py")], check=True)
    print(f"done: {len(results)} files, {len(errors)} errors, {time.time()-t0:.0f}s")
    for e in errors[:20]:
        print("ERR", e)
    # fail the run only if (almost) nothing came back
    if len(errors) > len(jobs) * 0.5:
        sys.exit(1)


if __name__ == "__main__":
    main()
