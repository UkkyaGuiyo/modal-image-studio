# Howto：背景だけ変える

被写体と構図を保ったまま、背景（空・季節・時刻など）だけを変えるのは、この道具が最も得意な編集です（品質ゲートで満点通過。P3-001）。

## 手順

```bash
modal run studio.py --mode variate --from-selection runs/<日時>_<名前> \
  --prompt "Change only the sky to a starry night, keep everything else exactly the same" \
  --count 4 --run-name night-sky
```

- 参照画像を直接指定する場合は `--ref path/to/image.png`
- ポイントは「変える場所」と「保つもの」を両方書くこと：`Change only X, keep Y`
- 効きやすい変更：空、季節、時刻、天候、背景の景色
- 効きにくい変更：被写体の移動、視点の変更（[10 章](../manual/10_variate.md) 手順3の言い換え表を参照）

結果は新しい run に出ます。元の画像はそのまま残るので、気に入らなければプロンプトを直してもう一度どうぞ。
