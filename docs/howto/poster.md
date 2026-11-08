# Howto：ポスターを作る

全体の流れ：**背景を生成 → 人間が選ぶ → 文字を合成 → （任意で）馴染ませる → 確認して保存**。
詳しい手順と切り分けは [12 章](../manual/12_poster.md) にあります。ここは最短の道筋です。

## 1. 背景を作って選ぶ

```bash
modal run studio.py --mode generate \
--prompt "A lighthouse under a starry sky, flat poster illustration, no text" \
--count 8 --run-name poster-bg
python3 select.py --run runs/<日時>_poster-bg --pick img_00X # Xは人間が選ぶ
```

## 2. 文字を合成する

```bash
python3 poster.py render --bg runs/<日時>_poster-bg/img_00X.png \
--template orderly \
--title "星空の灯台" --subtitle "満月の夜、港を照らす" \
--band-left "2026年 夏 公開予定" --band-right "入場無料" \
--out poster_out
```

## 3. 文字レイヤーを単体で確認する

`poster_out/textlayer.png` を開き、全文字がそろっているか見る（欠けはブレンドで保存されてしまうため。12 章手順2）。

## 4. 馴染ませる（任意）

```bash
python3 poster.py blend --bg runs/<日時>_poster-bg/img_00X.png \
--template orderly \
--title "星空の灯台" --subtitle "満月の夜、港を照らす" \
--band-left "2026年 夏 公開予定" --band-right "入場無料" \
--out poster_out
```

成果物は `poster_out/final.png`。シャープな印刷物風にしたい場合は、手順2の `composite.png` をそのまま使う。

## テンプレートの選び方

- きちんとした告知 → `orderly`
- 勢いのあるイベント系 → `art-broken`（文字が躍る系の出発点。応用は 12 章手順4）
- 募集など情報量の多い実務系 → `recruit`

作例は [samples/SAMPLES.md](../../samples/SAMPLES.md) の 18〜29 番。
