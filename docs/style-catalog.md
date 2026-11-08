# 作風カタログ

`studio.py --style <名前>` で指定できるプリセットの一覧です。
同じ被写体でも作風でここまで変わる、という実測は samples の 03〜06 番と 20〜26 番にあります。

## 画風（8種）

同一被写体（灯台）で8作風すべて判別可能に描き分けられることを確認済み（STYLES-001）。

| 名前 | 追加される指示（英語・実装の原文） | 雰囲気 |
|---|---|---|
| watercolor | soft watercolor painting, gentle color bleeding, visible paper texture | 水彩。色のにじみと紙の質感 |
| ukiyo-e | Japanese ukiyo-e woodblock print, flat color areas, bold black outlines | 浮世絵。平坦な色面と太い輪郭 |
| pixel-art | detailed pixel art, limited color palette, crisp pixels | ピクセルアート |
| oil-painting | classical oil painting, visible brushstrokes, rich layered color | 油絵。筆致と重ね塗り |
| photorealistic | photorealistic, natural lighting, fine detail, shot on a 35mm lens | 写真風 |
| ink-manga | black and white ink manga illustration, screentones, strong line work | 白黒の線画漫画 |
| pastel | soft pastel illustration, gentle light colors, dreamy atmosphere | パステル。淡く夢のある空気 |
| cyberpunk | cyberpunk style, neon lights, rain-slick streets, high-tech mood | サイバーパンク。ネオンと雨 |

注意：ukiyo-e などでは絵の中に漢字風の落款（疑似文字）が付くことがあります。不要なら元のプロンプトに `no text` を入れてください（P3-001）。

## デザイン言語（3種）

「色を塗り替える」のではなく、図形・モチーフ・人物の置き方・タイポグラフィまで様式ごとに切り替わる、強いグラフィックデザインの型です。
専門家のデザイン分析をキーフレーズ化してプリセットにしたもので、同一題材の比較テストで 94 / 92 / 97 点（100点満点の様式再現評価）を記録しました（BENCH-002 第3波）。

### quiet-blue（静かな青）

- 追加される指示：cool teal-blue monochromatic palette with subtle yellow accents, translucent glass panels, soft water ripples and floating bubbles, moon-phase symbols and circular geometry, elegant negative space, atmospheric underwater lighting and soft reflections
- 型：ティール〜深青の単色基調。黄色は月などの**小さなアクセントだけ**。水・泡・ガラスの透明感、円と月相のモチーフ、余白の多さ、静かな単独人物
- 空気感の目安： "Melancholic Urban Futurism"（憂いのある近未来の静けさ）
- やってはいけない：色数を増やす／黄色を大きく使う／人物を賑やかに並べる

### retro-tv-pop（レトロTVポップ）

- 追加される指示：warm saturated yellow and amber palette with bold black contrast, retro television broadcast graphics, multicolor horizontal television signal stripes, CRT scanlines and subtle analog static, thick black rectangular frames, atmospheric yellow fog, playful ensemble composition
- 型：黄色は主役だが**一色にしない**。多色のテレビ信号ストライプと黒がサブカラー。テレビの画面枠・太い黒フチ・アナログなノイズ、足元の黄色い霧、にぎやかな群像
- 空気感の目安： "Nostalgic Pop Mystery"（懐かしいポップな謎解き感）
- やってはいけない：黄色一色で塗る（第1波の失敗。ストライプ＋黒を入れて解消した）

### pop-punk-red（ポップパンク赤）

- 追加される指示：high-contrast scarlet red, black and white palette, aggressive pop-punk editorial graphic design, sharp diagonal cuts and jagged geometric shapes, kinetic asymmetrical collage composition, bold black ink shading, subtle halftone dots and photocopy grain
- 型：赤・黒・白のみ。斜線とギザギザの図形、巨大な凝縮書体を図形として扱う、動きのある非対称コラージュ。**レイアウトそのものが勝負**（3種の中で最も再現が難しいと予想され、実測では最高点を取った）
- 空気感の目安： "Aggressive Pop-Punk Rebellion"（攻撃的なポップパンクの反逆）
- やってはいけない：色を足す／左右対称に整える／文字を小さく行儀よく置く

## プリセット以外の作風

プリセットは「プロンプトの末尾に作風の指示文を足す」仕組みです。カタログに無い作風は、プロンプト内に直接書けば同じことができます（例：`in the style of a vintage screen print`）。枚ごとに違う指示を出す場合は `--prompts-json` を使います（08 章）。
