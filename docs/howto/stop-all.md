# Howto：全部止める

「もう止めたい」度合い別に、上から順に実施します。下に行くほど恒久的です。

## 1. 今の実行だけ止める

実行中のターミナルで `Ctrl-C`。これでローカル側の実行は止まります。

## 2. アプリを止める（実行中コンテナも止まる）

```bash
modal app list
modal app stop image-studio
```

`image-studio` がこの道具のアプリ名です。止めても重みのキャッシュ（Volume）は残るので、再開時は高速なままです。

## 3. ローカルの生成結果を消す

```bash
rm -rf runs/<日時>_<名前>
```

消す前に、人間に確認を取ること。再現条件（プロンプト・seed）も manifest ごと消えます。

## 4. クラウド側のキャッシュまで消す（完全初期化）

```bash
modal volume ls flux2-klein-weights   # 中身の最終確認
modal volume delete flux2-klein-weights
```

**人間の承認後**に実行します。次回は初回と同じ約62秒のダウンロードから始まります。

## 5. アカウントの解約

人間が Modal のダッシュボードで行います（Muse の担当外）。支払い方法の削除も同じく人間側の操作です。

詳しくは [13 章](../manual/13_cost_and_stop.md)。
