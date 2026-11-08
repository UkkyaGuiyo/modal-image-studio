# 開発ログ P4-001：選定フローと製品版CLI

- 日時：2026-11-08 17:07–17:10 JST
- 内容：製品版 `repo/studio.py`（作風プリセット11種を内蔵：画風8＋デザイン言語3）と `repo/select.py`（選定記録）を新設し、全工程を実走
- 手順と結果：
  1. generate --style retro-tv-pop ×4 → 成功（load 8.2s、4枚14.4s、$0.007）。作風サフィックスがプロンプトと manifest に記録される
  2. select.py --list → 一覧表示OK。--pick img_002 → selection.json 生成（picked_path/prompt/seed/decided_by=human/history 配列）
  3. variate --from-selection ×4（冬の夜＋オーロラ）→ 成功（$0.011）。新 manifest の parent に「<元run>/img_002.png」が記録され、系譜が追える
- 判定：P4完了。「生成→提示→人間が選ぶ→記録→選定から展開」の循環が、製品版コードで再現可能になった
- 残：ポスター合成ツール（poster系）の製品化は P5 の手順書と一緒に repo へ入れる
