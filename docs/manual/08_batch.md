# 08 一括生成

## 手順1：候補を一括生成する

- 目的：選んでもらうための候補を、seed を変えて複数枚そろえる
- 前提条件：07 章が成功している
- 実行主体：Muse
- コマンド：
  ```bash
  modal run studio.py --mode generate \
    --prompt "A retro travel poster of a mountain lake at dawn, flat colors, no text" \
    --count 8 --base-seed 1000 --run-name lake
  ```
- 成功条件：`runs/<日時>_lake/` に img_001〜img_008.png、manifest.json、contact_sheet.png がそろう。標準出力の est_cost_usd が想定範囲（8枚で約 $0.011）
- 失敗時の切り分け：プロンプトに作風の指定がないと地味な絵になりがち。作風は手順3の `--style` か、プロンプト内の作風語で指定する
- 次のステップ：09 章（選択）

## オプションの使い方（すべて実在を確認済み）

| オプション | 意味 | 備考 |
|---|---|---|
| `--count N` | 枚数 | 標準8。推奨最大16（候補として扱える量の目安） |
| `--base-seed S` | seed の起点 | img_00i の seed は S+i-1。再現したいときは同じ値を使う |
| `--prompts-json '[...]'` | 枚ごとに別プロンプト | 配列の長さがそのまま枚数になる（作風比較などに。STYLES-001 で使用） |
| `--style NAME` | 作風プリセット | 11種。カタログは [docs/style-catalog.md](../style-catalog.md) |
| `--size PRESET` | 縦横比 | 1:1 / 3:4 / 4:3 / 2:3 / 3:2 / 16:9 / 9:16、または `WxH` 直指定。全プリセット寸法どおり出ることを実測済み（BENCH-001） |
| `--run-name NAME` | 出力フォルダの名前部分 | 後から探しやすい名前を付ける |

## 手順2（コツ）：絵の中に文字を入れない

- 目的：読めない疑似文字が絵に入り込むのを防ぐ
- 前提条件：看板・ポスターなどが画面に入る題材のとき
- 実行主体：Muse
- コマンド：プロンプトに `no text` を含める（上の例のように）
- 成功条件：生成物に文字らしい模様が無い
- 失敗時の切り分け：それでも疑似文字が出る場合は seed を変える。文字が本当に必要な場合は生成で描かせず、12 章の合成で入れる（TEXT-001）
- 次のステップ：09 章

## 手順3（コツ）：作風を指定する

- 目的：地味なデフォルト絵柄から、狙った作風に寄せる
- 前提条件：なし
- 実行主体：Muse
- コマンド例：
  ```bash
  modal run studio.py --mode generate --prompt "A lighthouse on rocky coast at dusk, no text" \
    --style ukiyo-e --count 8 --run-name lighthouse-ukiyoe
  ```
- 成功条件：manifest.json の各画像に style が記録され、絵柄がプリセットどおりに変わる
- 失敗時の切り分け：未知のスタイル名を指定するとエラーで止まる（利用可能一覧が表示される）
- 次のステップ：09 章

次のステップ：[09 コンタクトシートと選択](09_select.md)
