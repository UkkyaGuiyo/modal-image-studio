# 17 完了検査チェックリスト

セットアップ完了の判定に使います。全てにチェックが付いたら「導入完了」です。

## 環境・アカウント

- [ ] Modal アカウントでダッシュボードにログインできる（03 章）
- [ ] 支払い方法が登録されている（人間が実施。Muse は見た目だけ確認）
- [ ] 予算（Spend limit）が設定されている
- [ ] `modal --version` が表示される（04 章）
- [ ] `modal setup` の認証が完了している（05 章）
- [ ] `modal run studio.py --help` / `python3 select.py --help` / `python3 poster.py --help` が全て表示される

## 生成の循環

- [ ] 最初の1枚が生成でき、runs/ に manifest.json と contact_sheet.png ができた（07 章）
- [ ] 8枚の一括生成ができ、費用（est_cost_usd）が確認できた（08 章）
- [ ] 人間が選び、`select.py` で selection.json に記録できた（09 章）
- [ ] 選択画像から variate ができ、新しい manifest に parent が記録された（10 章）
- [ ] 2回目以降の生成で、読み込みが約9秒台になっている（Volume キャッシュの効果）

## ポスター

- [ ] `poster.py render` で composite.png と textlayer.png ができた（12 章）
- [ ] textlayer.png 単体で全文字の存在を確認した
- [ ] （任意）`poster.py blend` で final.png ができ、文字が composite と一字一句同じだった

## 安全・費用

- [ ] `modal run` を同時に2本以上出していない（運用ルールとして理解した）
- [ ] `modal billing summary` で当月の使用額を確認した（13 章）
- [ ] runs/ や認証情報が Git に入っていない（.gitignore の確認）

## 判定

- 全項目チェック済み → 導入完了。人間に報告する
- 残っている項目がある → その章に戻って潰す。原因が分からなければ [トラブルシューティング](../troubleshooting.md) を引く
