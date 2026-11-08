# Howto：選んだ画像を展開する

「この絵は良い。ここから広げたい」というときの手順です。

## 前提

09 章の選択が済み、対象 run に selection.json があること。まだなら先に：

```bash
python3 select.py --run runs/<日時>_<名前> --list
python3 select.py --run runs/<日時>_<名前> --pick img_00X   # 選ぶのは人間
```

## 展開のしかたで選ぶ

| 狙い | プロンプトの型 | 例 |
|---|---|---|
| 一部だけ変える（Preserve） | "Change X, keep everything else" | 季節を冬に、空を夕焼けに |
| 作風を変える（Restyle） | "Restyle as 〜" または `--style` | 水彩化、浮世絵化（`--style ukiyo-e`） |
| 場面を広げる（Explore） | "Transform the scene into 〜" | 湖畔の小屋 → 冬の夜＋オーロラ |

```bash
modal run studio.py --mode variate --from-selection runs/<日時>_<名前> \
  --prompt "Change the scene to a winter night with aurora borealis, keep the cabin and composition" \
  --count 4 --run-name expand1
```

## 繰り返し方

- 展開結果も通常の run です。気に入ったものを人間が選び直し（09 章）、そこからさらに展開できます
- 系譜は manifest.json の `parent` に自動で残るので、「どれから生えた絵か」が後から追えます
- 苦手な指示（移動・視点変更）に当たったら [10 章の言い換え表](../manual/10_variate.md)
