# 開発ログ P5-001：ポスターツール製品化（poster.py）と文字言及ガードの誤検知

- 日時：2026-11-08（P5作業中）
- 目的：開発用ブレンド工程（dev/blend_dev.py 系）を製品版 `repo/poster.py` に移植し、スモークテストを通す
- 操作：
  1. poster.py を新規作成（render / blend の2サブコマンド。テンプレート orderly / art-broken / recruit。文字レイヤー単独描画→マスク生成→ブレンド→文字再重ねまで1本化）
  2. render スモーク：orderly は開発時デモと同一条件で再現。**文字レイヤーの字形被覆率 2.14% が TEXT-003 の実測と完全一致**。art-broken / recruit も描画成功（被覆率 9.37% / 20.92%。recruit は円・リボン等の前景要素を含むため高い）
  3. blend スモーク：初回実行で自作の「文字言及ガード」がデフォルトプロンプトを弾いて停止（下記）

## 失敗の記録（blend初回）
- 失敗内容：ブレンド段の開始直後、`Blend prompt mentions text (text)` で SystemExit。Modal は起動していない（費用ゼロ）
- 原因：ガードが部分一致で判定していたため、デフォルトプロンプト中の "texture"（紙の質感の指定）に "text" が一致した。デフォルトプロンプト自体は TEXT-003 で実証済みの正規の文面
- 修正：英語の単語は単語境界（\b）で照合し、"texture" のような複合語に当たらないようにする。日本語キーワードは従来どおり部分一致
- 再試験：修正後に blend スモークを再実行 → 失敗2に進んだ（ガード自体は通過）

## 失敗の記録2（blend再実行）
- 失敗内容：ガード修正後の再実行で `modal.exception.InvalidError: The @app.function decorator must apply to functions in global scope`。Modal アプリと関数を stage_blend() の内側で定義したことが原因（studio.py / blend_dev.py はどちらもモジュールレベル定義だった）
- 修正：Modal の App / Image / Volume / 関数はモジュールレベルに定義する。ただし `import modal` は try/except で囲み、未導入環境でも render サブコマンドと --help が動くようにする（blend 実行時のみ必須にする）
- 再試験：組み替え後に blend スモークを実行 → **成功**。読み込み9.29秒＋ブレンド9.84秒、GPU合計19.1秒、費用 **$0.006**。final.png は全文字列が正確なまま、文字周辺に印刷粒子が乗り馴染んだ（目視確認）。ついでに確認できた副次的事実：Modal未導入のPython環境でも render と --help は動作する（import を任意化した効果）
- 判定：poster.py 製品化完了（render / blend 両段スモーク通過）

## 備考（設計判断）
- 製品版のアプリ名は studio.py と同じ `image-studio` に統一（開発版 blend_dev.py の `image-studio-dev` から変更）。重み Volume `flux2-klein-weights` は共通
- 文字レイヤーには「文字を担う前景デザイン要素」（art-broken のテープとバッジ、recruit のタグ・リボン・円）も含めた。マスクの保護対象が字形のみだった TEXT-003 より保護範囲が広い（安全側）。ブレンドの標準値（halo 44px / 保護6px / steps 6 / guidance 1.0 / strength 1.0）は TEXT-003 の確定値を継承
