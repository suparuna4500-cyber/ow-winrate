# OW 勝率 韓国×アジア

韓国（Nexon 公式 영웅 통계）とアジア・米州・欧州（Blizzard 公式ヒーロー統計）の
全ヒーローの勝率・ピック率・BAN率を、マップ・ランク・モード別に並べて見るページです。

- `index.html` … サイト本体（データ埋め込み済み・GitHub Pages で公開）
- `collector/collect.py` … 公式ページから最新値を取り直して `data/latest/` と `index.html` を作り直す
- `.github/workflows/collect.yml` … 毎日 12:17（日本時間）に自動実行。Actions 画面から手動実行も可

数値は各公式ページの「最新パッチ開始からの集計」をそのまま写したものです。非公式・個人用。
