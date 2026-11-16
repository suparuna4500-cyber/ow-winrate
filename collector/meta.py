"""Static metadata: Japanese names for heroes / maps, map types, patch markers."""

HERO_JA = {
    "winston": "ウィンストン", "junkerqueen": "ジャンカー・クイーン", "domina": "ドミナ", "doomfist": "ドゥームフィスト",
    "hazard": "ハザード", "sigma": "シグマ", "zarya": "ザリア", "reinhardt": "ラインハルト", "orisa": "オリーサ",
    "dmon": "D.Mon", "dva": "D.Va", "mauga": "マウガ", "ramattra": "ラマットラ", "roadhog": "ロードホッグ",
    "wreckingball": "レッキング・ボール", "pharah": "ファラ", "genji": "ゲンジ", "tracer": "トレーサー",
    "symmetra": "シンメトラ", "reaper": "リーパー", "venture": "ベンチャー", "anran": "アンラン",
    "vendetta": "ヴェンデッタ", "ashe": "アッシュ", "mei": "メイ", "echo": "エコー", "junkrat": "ジャンクラット",
    "shion": "シオン", "sierra": "シエラ", "widowmaker": "ウィドウメイカー", "hanzo": "ハンゾー", "freja": "フレイヤ",
    "torbjorn": "トールビョーン", "cassidy": "キャスディ", "emre": "エムレ", "soldier76": "ソルジャー76",
    "sojourn": "ソジョーン", "bastion": "バスティオン", "illari": "イラリー", "zenyatta": "ゼニヤッタ",
    "brigitte": "ブリギッテ", "wuyang": "ウーヤン", "doctrine": "ドクトリン", "ana": "アナ", "moira": "モイラ",
    "juno": "ジュノ", "sombra": "ソンブラ", "kiriko": "キリコ", "mizuki": "ミズキ",
    "jetpackcat": "ジェットパック・キャット", "lucio": "ルシオ", "baptiste": "バティスト", "mercy": "マーシー",
    "lifeweaver": "ライフウィーバー",
}

# value, ja name, type  (order = Blizzard's list)
MAPS = [
    ("all-maps", "全マップ", ""),
    ("antarctic-peninsula", "南極半島", "control"), ("busan", "釜山", "control"), ("ilios", "イリオス", "control"),
    ("lijiang-tower", "麗江タワー", "control"), ("nepal", "ネパール", "control"), ("oasis", "オアシス", "control"),
    ("samoa", "サモア", "control"),
    ("circuit-royal", "サーキット・ロイヤル", "escort"), ("dorado", "ドラド", "escort"),
    ("grimsvotn", "ウォッチポイント：グリムスヴォトン", "escort"), ("havana", "ハバナ", "escort"), ("junkertown", "ジャンカータウン", "escort"),
    ("rialto", "リアルト", "escort"), ("route-66", "ルート66", "escort"),
    ("shambali-monastery", "シャンバリ寺院", "escort"), ("watchpoint-gibraltar", "ウォッチポイント：ジブラルタル", "escort"),
    ("aatlis", "アートリス", "flashpoint"), ("new-junk-city", "ニュー・ジャンク・シティ", "flashpoint"),
    ("suravasa", "スラヴァーサ", "flashpoint"),
    ("blizzard-world", "ブリザードワールド", "hybrid"), ("eichenwalde", "アイヒェンヴァルデ", "hybrid"),
    ("hollywood", "ハリウッド", "hybrid"), ("kings-row", "キングスロウ", "hybrid"), ("midtown", "ミッドタウン", "hybrid"),
    ("neon-junction", "ネオン・ジャンクション", "hybrid"), ("numbani", "ナンバーニ", "hybrid"), ("paraiso", "パライーゾ", "hybrid"),
    ("colosseo", "コロッセオ", "push"), ("esperanca", "エスペランサ", "push"),
    ("new-queen-street", "ニュー・クイーン・ストリート", "push"), ("runasapi", "ルナサピ", "push"),
]
MAP_TYPE_JA = {"control": "コントロール", "escort": "エスコート", "flashpoint": "フラッシュポイント",
               "hybrid": "ハイブリッド", "push": "プッシュ"}
