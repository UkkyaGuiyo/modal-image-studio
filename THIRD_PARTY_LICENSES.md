# サードパーティのライセンス

このリポジトリのコードが利用する外部コンポーネントと、そのライセンスです。

| コンポーネント | 用途 | ライセンス |
|---|---|---|
| FLUX.2 Klein 4B（black-forest-labs/FLUX.2-klein-4B） | 画像生成・編集モデル（既定） | Apache License 2.0 |
| FLUX.2 Klein Base 4B（black-forest-labs/FLUX.2-klein-base-4B） | `--model base` で使う未蒸留モデル | Apache License 2.0 |
| diffusers（Hugging Face） | モデルの実行ライブラリ | Apache License 2.0 |
| PyTorch | 実行基盤 | BSD-style（PyTorch ライセンス） |
| torchvision | PyTorch の画像処理・モデルユーティリティ | BSD 3-Clause License |
| transformers（Hugging Face） | モデルの読み込み・トークナイザ等 | Apache License 2.0 |
| accelerate（Hugging Face） | 推論実行の補助 | Apache License 2.0 |
| safetensors | モデル重みの読み込み | Apache License 2.0 / MIT License |
| huggingface_hub | モデル重みのダウンロード | Apache License 2.0 |
| Pillow | ローカルでの画像処理（poster.py の合成等） | HPND License |
| sentencepiece | トークナイザの補助ライブラリ | Apache License 2.0 |
| protobuf | データ形式のライブラリ | BSD 3-Clause License |
| NumPy | 数値計算 | BSD 3-Clause License |
| Modal | GPU 実行環境（サービス） | Modal の利用規約に従う |

注意：
- poster.py のポスター描画には、ローカル環境の Chromium / Chrome を使用します（本リポジトリには含まれません。各ブラウザのライセンスに従います）
- ポスターの日本語表示に使う Noto CJK フォントは SIL Open Font License 1.1 で提供されています（フォント自体は本リポジトリに含まれません）
- 本リポジトリでは diffusers を GitHub 本流から導入しています（モデルカードの指示に従った開発時の構成。16 章参照）
- 生成した画像の権利・利用条件は、モデルのライセンスと各サービスの規約を確認してください。本手順書は法的な助言ではありません
