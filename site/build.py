import json, os, glob
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
idx = json.load(open(f"{ROOT}/data/index.json", encoding="utf-8"))
combos = {os.path.basename(p)[:-5]: json.load(open(p)) for p in glob.glob(f"{ROOT}/data/latest/*.json")}
heroes = {}
for k, v in idx["heroes"].items():
    c = (v.get("color") or "").lstrip("#")[:6]
    heroes[k] = {"ja": v.get("ja"), "en": v.get("en"), "ko": v.get("ko"), "role": v.get("role"), "color": "#" + c if c else None}
def jp(t):
    d, hm = t.split(" "); y, mo, da = d.split("-"); return f"{int(mo)}月{int(da)}日 {hm}"
a = idx.get("asof", {})
asof = f"韓国 {jp(a['Korea'])}／アジア・米州・欧州 {jp(a['Blizzard'])}（日本時間）" if a.get("Korea") != a.get("Blizzard") else f"{jp(a['Korea'])}（日本時間）"
try:
    periods = json.load(open(f"{ROOT}/data/periods/index.json", encoding="utf-8"))
except Exception:
    periods = {"periods": [], "current": None}
D = {"periods": periods, "img": json.load(open(f"{ROOT}/data/img.json")), "asof": asof, "heroes": heroes,
     "maps": idx["maps"], "mapTypes": idx["mapTypes"], "combos": combos}
html = open(f"{ROOT}/site/template.html", encoding="utf-8").read().replace("/*__DATA__*/null", json.dumps(D, ensure_ascii=False, separators=(",", ":")))
open(f"{ROOT}/index.html", "w", encoding="utf-8").write(html)
print(f"built index.html: {len(combos)} combos, {len(heroes)} heroes, {len(html)//1024} KB, asof {asof}")
