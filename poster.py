#!/usr/bin/env python3
"""poster.py - poster compositing tool for image-studio.

Pipeline (measured standard, see docs/development-log TEXT-001..TEXT-004):
  1. render : HTML/CSS template -> headless Chromium screenshot.
              Two renders are produced:
                composite.png - background + foreground design (the poster
                                as designed, no AI pass)
                textlayer.png - foreground only, transparent background
                                (used for the protection mask and for the
                                final pixel-exact re-overlay)
  2. mask   : build_protection/repaint masks from the text layer's alpha.
              Protection = foreground dilated by 6 px (never repainted).
              halo mode repaints only a 44 px ring around the foreground;
              full mode repaints everything except the protection zone.
  3. blend  : (optional, needs Modal) Flux2KleinInpaintPipeline repaints the
              mask area so the composited foreground melts into the artwork.
              The blend prompt must NOT mention text in any way - prompts
              that talk about lettering provoke redraw/garbling. This tool
              refuses text-mentioning prompts unless --force is given.
  4. final  : the original text layer is re-overlaid on the blended image,
              so glyphs are guaranteed pixel-exact even though the inpaint
              itself only preserves shapes approximately.

Usage:
  python3 poster.py render --bg bg.png --template orderly \\
      --title "星空の灯台" --subtitle "満月の夜、港を照らす" \\
      --band-left "2026年 夏 公開予定" --band-right "入場無料" --out poster_out
  python3 poster.py blend  --bg bg.png --template orderly ... --out poster_out
  python3 poster.py render --template recruit --bg photo.png \\
      --title-main "未経験" ... --out recruit_out

Requirements: Python 3.10+, Pillow. A Chromium/Chrome binary for rendering
(auto-detected; override with --chrome or the CHROME_BIN env var).
The blend stage additionally needs the Modal CLI setup used by studio.py
(it shares the "image-studio" app and the "flux2-klein-weights" volume).
Japanese fonts: templates assume "Noto Sans CJK JP" / "Noto Serif CJK JP".
"""
import argparse
import html
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime

TOOL_VERSION = "1.0.0"
A10_USD_PER_SEC = 0.000306  # Modal A10 list price basis used across the project

# ---------------------------------------------------------------- templates
# Tokens look like %%TITLE%% and are substituted with HTML-escaped slot text
# (newlines become <br>). %%BG_URL%% is replaced with a file:// URL (or a CSS
# gradient when no background image is given).
# %%TEXTLAYER_CSS%% receives extra CSS that strips the page background for
# the transparent text-layer render.

CSS_RESET = "* { margin:0; padding:0; box-sizing:border-box; }"

TEMPLATE_ORDERLY = """<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="utf-8">
<style>
  %%RESET%%
  html, body { width: %%W%%px; height: %%H%%px; overflow: hidden; }
  body {
    font-family: "Noto Sans CJK JP", sans-serif;
    background: %%BG%% center / cover no-repeat;
    position: relative; color: #fff;
  }
  .vtitle {
    position: absolute; top: 64px; right: 56px;
    writing-mode: vertical-rl;
    font-family: "Noto Serif CJK JP", serif;
    font-size: 96px; font-weight: 700;
    letter-spacing: 0.18em;
    text-shadow: 0 2px 18px rgba(4, 10, 40, .85), 0 0 2px rgba(4, 10, 40, .9);
  }
  .subtitle {
    position: absolute; top: 84px; left: 64px;
    font-size: 34px; font-weight: 500;
    letter-spacing: 0.42em; color: #dbe7ff;
    text-shadow: 0 1px 10px rgba(4, 10, 40, .9);
  }
  .band {
    position: absolute; left: 0; right: 0; bottom: 0; height: 104px;
    background: linear-gradient(180deg, rgba(6, 10, 34, 0), rgba(6, 10, 34, .88) 38%);
    display: flex; align-items: flex-end; justify-content: space-between;
    padding: 0 56px 30px;
  }
  .band .date { font-size: 36px; font-weight: 700; letter-spacing: 0.22em; }
  .band .note { font-size: 24px; letter-spacing: 0.3em; color: #b9c9ee; }
  %%TEXTLAYER_CSS%%
</style>
</head>
<body>
  <div class="vtitle">%%TITLE%%</div>
  <div class="subtitle">%%SUBTITLE%%</div>
  <div class="band">
    <div class="date">%%BAND_LEFT%%</div>
    <div class="note">%%BAND_RIGHT%%</div>
  </div>
</body>
</html>
"""

# Text-layer overrides: drop the page background and the gradient band so
# only the foreground (glyphs + their shadows) remains.
TEXTLAYER_ORDERLY = """
  body { background: none !important; }
  .band { background: none !important; }
"""

TEMPLATE_ART = """<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="utf-8">
<style>
  %%RESET%%
  html, body { width: %%W%%px; height: %%H%%px; overflow: hidden; }
  body {
    font-family: "Noto Sans CJK JP", sans-serif;
    background: %%BG%% center / cover no-repeat;
    position: relative; color: #fff;
  }
  .char { position: absolute; font-weight: 900; line-height: 1; text-shadow: 0 3px 22px rgba(3, 8, 36, .8); }
  .c1 { top: 40px;  left: 60px;  font-size: 190px; transform: rotate(-9deg); font-family: "Noto Serif CJK JP", serif; }
  .c2 { top: 150px; left: 250px; font-size: 120px; transform: rotate(7deg); color: #ffd94d; }
  .c3 { top: 66px;  left: 420px; font-size: 84px;  transform: rotate(-16deg); color: transparent; -webkit-text-stroke: 3px #fff; text-shadow: none; }
  .c4 { top: 120px; left: 520px; font-size: 220px; transform: rotate(5deg); font-family: "Noto Serif CJK JP", serif; }
  .c5 { top: 300px; left: 700px; font-size: 150px; transform: rotate(-12deg); color: #ff5d7a; }
  .big {
    position: absolute; top: 430px; left: -30px;
    font-family: "Noto Serif CJK JP", serif; font-weight: 700;
    font-size: 300px; letter-spacing: .05em;
    color: rgba(255,255,255,.16); transform: rotate(-90deg);
    transform-origin: left top;
  }
  .tape {
    position: absolute; top: 392px; left: -40px; width: 640px;
    background: #e63946; color: #fff;
    font-size: 34px; font-weight: 700; letter-spacing: .34em;
    padding: 12px 30px; transform: rotate(-6deg);
    box-shadow: 0 6px 24px rgba(0,0,0,.45);
  }
  .frag1 { position: absolute; bottom: 210px; right: 70px; font-size: 40px; transform: rotate(11deg); letter-spacing: .2em; color: #dbe7ff; text-shadow: 0 2px 12px rgba(3,8,36,.9); }
  .frag2 { position: absolute; bottom: 150px; right: 190px; font-size: 28px; transform: rotate(-4deg); letter-spacing: .5em; color: #ffd94d; text-shadow: 0 2px 12px rgba(3,8,36,.9); }
  .badge {
    position: absolute; bottom: 96px; left: 64px; width: 168px; height: 168px;
    border: 4px solid #fff; border-radius: 50%;
    display: flex; align-items: center; justify-content: center; text-align: center;
    font-size: 34px; font-weight: 900; letter-spacing: .14em; line-height: 1.35;
    transform: rotate(-13deg); background: rgba(6, 12, 44, .42);
    text-shadow: 0 2px 10px rgba(3,8,36,.9);
  }
  .date {
    position: absolute; bottom: 44px; right: 56px;
    font-size: 30px; font-weight: 700; letter-spacing: .3em;
    transform: rotate(2deg); text-shadow: 0 2px 12px rgba(3,8,36,.95);
  }
  %%TEXTLAYER_CSS%%
</style>
</head>
<body>
  <div class="big">%%WATERMARK%%</div>
  %%CHARS%%
  <div class="tape">%%SUBTITLE%%</div>
  <div class="frag1">%%FRAG1%%</div>
  <div class="frag2">%%FRAG2%%</div>
  <div class="badge">%%BADGE%%</div>
  <div class="date">%%BAND_LEFT%%</div>
</body>
</html>
"""

# The tape and badge carry their own background as part of the design, so
# only the page background is stripped for the text layer.
TEXTLAYER_ART = """
  body { background: none !important; }
"""

TEMPLATE_RECRUIT = """<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="utf-8">
<style>
  %%RESET%%
  html, body { width: %%W%%px; height: %%H%%px; overflow: hidden; }
  body { font-family: "Noto Sans CJK JP", sans-serif;
    background: linear-gradient(180deg, #fdfefe 0%, #eef7f4 55%, #e8f3ee 100%);
    position: relative; color: #223; }
  .photo { position:absolute; top:0; left:0; right:0; height:600px;
    background: %%BG%% 62% 18% / cover no-repeat; }
  .fade { position:absolute; top:470px; left:0; right:0; height:190px;
    background: linear-gradient(180deg, rgba(253,254,254,0), rgba(247,251,249,.96) 78%); }
  .tag { position:absolute; top:26px; left:26px; background:rgba(255,255,255,.82); border-radius:999px; padding:8px 20px;
    font-size:25px; font-weight:700; color:#33608c; letter-spacing:0.14em; }
  .ribbon { position:absolute; top:352px; left:0; background:rgba(168,205,230,.92); color:#17395c;
    font-size:29px; font-weight:700; letter-spacing:0.08em; padding:10px 26px 10px 30px; }
  .title { position:absolute; top:520px; left:0; right:0; text-align:center; }
  .t1 { font-family:"Noto Serif CJK JP", serif; font-size:104px; font-weight:900; color:#27348b; letter-spacing:0.02em; }
  .t1s { font-size:43px; font-weight:700; color:#222; margin-left:10px; }
  .t2 { font-size:82px; font-weight:900; color:#2f9257; letter-spacing:0.06em; margin-top:2px;
    text-shadow: 0 0 14px rgba(255,255,255,.9); }
  .circles { position:absolute; top:838px; left:0; right:0; display:flex; justify-content:center; gap:26px; }
  .circle { width:236px; height:236px; border-radius:50%; background:rgba(230,245,234,.95); border:2px solid #bfe0cc;
    display:flex; align-items:center; justify-content:center; text-align:center;
    font-size:27px; font-weight:700; line-height:1.5; color:#24402e; padding:14px; }
  .visit { position:absolute; top:1104px; left:0; right:0; text-align:center; font-size:30px; font-weight:700; color:#333; }
  .visit u { text-decoration-thickness:2px; text-underline-offset:6px; }
  .footer { position:absolute; bottom:0; left:0; right:0; height:104px; padding:14px 30px; display:flex; justify-content:space-between; align-items:center; }
  .fname { font-size:31px; font-weight:900; color:#2b5797; letter-spacing:0.1em; }
  .finfo { font-size:19px; color:#444; line-height:1.45; }
  .qrs { display:flex; gap:12px; }
  .qr { width:64px; height:64px; border:2px dashed #9db8cc; border-radius:8px; display:flex; align-items:center; justify-content:center;
    font-size:14px; color:#7a97ab; text-align:center; line-height:1.3; background:rgba(255,255,255,.7); }
  %%TEXTLAYER_CSS%%
</style>
</head>
<body>
<div class="photo"></div><div class="fade"></div>
<div class="tag">%%TAG%%</div>
<div class="ribbon">%%RIBBON%%</div>
<div class="title">
  <div><span class="t1">%%TITLE_MAIN%%</span><span class="t1s">%%TITLE_SUB%%</span></div>
  <div class="t2">%%TITLE_LINE2%%</div>
</div>
<div class="circles">
  <div class="circle">%%CIRCLE1%%</div>
  <div class="circle">%%CIRCLE2%%</div>
  <div class="circle">%%CIRCLE3%%</div>
</div>
<div class="visit"><u>%%VISIT%%</u></div>
<div class="footer">
  <div>
    <div class="fname">%%ORG_NAME%%</div>
    <div class="finfo">%%ORG_INFO%%</div>
  </div>
  <div class="qrs"><div class="qr">QR<br>LINE</div><div class="qr">QR<br>SNS</div></div>
</div>
</body>
</html>
"""

# Photo band and page gradient belong to the background, not the text layer.
TEXTLAYER_RECRUIT = """
  body { background: none !important; }
  .photo, .fade { display: none !important; }
"""

TEMPLATES = {
    "orderly": {
        "html": TEMPLATE_ORDERLY,
        "textlayer_css": TEXTLAYER_ORDERLY,
        "default_size": (1024, 1024),
        "slots": ["TITLE", "SUBTITLE", "BAND_LEFT", "BAND_RIGHT"],
    },
    "art-broken": {
        "html": TEMPLATE_ART,
        "textlayer_css": TEXTLAYER_ART,
        "default_size": (1024, 1024),
        "slots": ["TITLE", "SUBTITLE", "FRAG1", "FRAG2", "BADGE", "BAND_LEFT", "WATERMARK"],
    },
    "recruit": {
        "html": TEMPLATE_RECRUIT,
        "textlayer_css": TEXTLAYER_RECRUIT,
        "default_size": (832, 1248),
        "slots": [
            "TAG", "RIBBON", "TITLE_MAIN", "TITLE_SUB", "TITLE_LINE2",
            "CIRCLE1", "CIRCLE2", "CIRCLE3", "VISIT", "ORG_NAME", "ORG_INFO",
        ],
    },
}

DEFAULT_SLOTS = {
    "TITLE": "星空の灯台",
    "SUBTITLE": "満月の夜、港を照らす",
    "BAND_LEFT": "2026年 夏 公開予定",
    "BAND_RIGHT": "入場無料",
    "FRAG1": "",
    "FRAG2": "",
    "BADGE": "入場\n無料",
    "WATERMARK": "",  # empty -> last two characters of TITLE
    "TAG": "スタッフ募集",
    "RIBBON": "病院でのお仕事 募集",
    "TITLE_MAIN": "未経験",
    "TITLE_SUB": "から始められる",
    "TITLE_LINE2": "医療のお仕事",
    "CIRCLE1": "未経験OK\n無資格OK",
    "CIRCLE2": "勤務時間\n相談OK",
    "CIRCLE3": "福利厚生\n充実",
    "VISIT": "毎週木曜日、見学会実施中！！",
    "ORG_NAME": "さくら総合病院",
    "ORG_INFO": "〒000-0000　大阪府○○市○○町1-1-1\nTEL：000-000-0000",
}

# ------------------------------------------------------- Modal (blend only)
# Modal requires @app.function targets in global scope, so the app, image
# and remote function live at module level. The import is optional: the
# render stage and --help work on machines without Modal installed.
try:
    import modal as _modal
except ImportError:  # pragma: no cover - depends on environment
    _modal = None

if _modal is not None:
    _weights = _modal.Volume.from_name("flux2-klein-weights", create_if_missing=True)
    _image_def = (
        _modal.Image.from_registry(
            "nvidia/cuda:12.8.0-cudnn-devel-ubuntu22.04", add_python="3.12"
        )
        .env({"TORCH_CUDA_ARCH_LIST": "8.0;8.6;8.9;9.0"})
        .apt_install("git")
        .pip_install(
            "torch==2.8.0",
            "torchvision==0.23.0",
            index_url="https://download.pytorch.org/whl/cu128",
        )
        .pip_install(
            "git+https://github.com/huggingface/diffusers.git",
            "transformers",
            "accelerate",
            "safetensors",
            "huggingface_hub",
            "pillow",
            "sentencepiece",
            "protobuf",
            "numpy",
        )
        .env({"HF_HOME": "/weights/hf"})
    )
    _app = _modal.App("image-studio")

    @_app.function(image=_image_def, gpu="A10", volumes={"/weights": _weights}, timeout=1800)
    def _blend_remote(image_bytes: bytes, mask_bytes: bytes, steps: int, seed: int,
                      blend_prompt: str) -> dict:
        import io
        import time

        import torch
        from diffusers import Flux2KleinInpaintPipeline
        from PIL import Image

        t0 = time.time()
        pipe = Flux2KleinInpaintPipeline.from_pretrained(
            "black-forest-labs/FLUX.2-klein-4B", torch_dtype=torch.bfloat16
        )
        pipe.to("cuda")
        load_s = time.time() - t0

        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        mask = Image.open(io.BytesIO(mask_bytes)).convert("L")
        gen = torch.Generator("cuda").manual_seed(seed)
        t1 = time.time()
        res = pipe(
            image=img,
            mask_image=mask,
            prompt=blend_prompt,
            num_inference_steps=steps,
            guidance_scale=1.0,
            strength=1.0,
            generator=gen,
        ).images[0]
        seconds = time.time() - t1
        buf = io.BytesIO()
        res.save(buf, format="PNG")
        return {"png": buf.getvalue(), "load_s": round(load_s, 2),
                "seconds": round(seconds, 2)}


BLEND_PROMPT_DEFAULT = (
    "Blend this poster into a cohesive flat illustration with a unified "
    "color palette and a subtle printed-paper grain texture"
)
# Words that make the inpaint model try to redraw lettering (measured rule,
# dev log TEXT-003). The blend prompt must stay abstract: style words only.
# Latin words are matched on word boundaries so that e.g. "texture" (paper
# grain - part of the standard prompt) does not false-positive on "text"
# (dev log P5-001).
TEXT_MENTION_WORDS_EN = ["text", "letter", "title", "typograph", "word", "caption", "font"]
TEXT_MENTION_WORDS_JA = ["文字", "タイトル", "字", "書体"]


def text_mentions(prompt: str) -> list:
    import re

    hits = [
        w for w in TEXT_MENTION_WORDS_EN
        if re.search(rf"\b{re.escape(w)}\b", prompt, flags=re.IGNORECASE)
    ]
    hits += [w for w in TEXT_MENTION_WORDS_JA if w in prompt]
    return hits


# ------------------------------------------------------------------ helpers

def esc(text: str) -> str:
    return html.escape(text, quote=False).replace("\n", "<br>")


def find_chrome(explicit: str = "") -> str:
    candidates = []
    if explicit:
        candidates.append(explicit)
    if os.environ.get("CHROME_BIN"):
        candidates.append(os.environ["CHROME_BIN"])
    home = os.path.expanduser("~")
    import glob

    candidates += sorted(
        glob.glob(os.path.join(home, ".cache/ms-playwright/chromium-*/chrome-linux64/chrome"))
    )
    for name in ("chromium", "chromium-browser", "google-chrome", "google-chrome-stable"):
        found = shutil.which(name)
        if found:
            candidates.append(found)
    for cand in candidates:
        if cand and os.path.isfile(cand) and os.access(cand, os.X_OK):
            return cand
    raise SystemExit(
        "No Chromium/Chrome binary found. Pass --chrome <path>, set CHROME_BIN, "
        "or install Chromium (e.g. `npx playwright install chromium`)."
    )


def render_png(chrome: str, html_path: str, out_png: str, width: int, height: int,
               transparent: bool) -> None:
    cmd = [
        chrome,
        "--headless=new",
        "--no-sandbox",
        "--disable-gpu",
        "--hide-scrollbars",
        "--force-device-scale-factor=1",
        f"--window-size={width},{height}",
        f"--screenshot={out_png}",
    ]
    if transparent:
        cmd.append("--default-background-color=00000000")
    cmd.append("file://" + os.path.abspath(html_path))
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if proc.returncode != 0 or not os.path.isfile(out_png):
        raise SystemExit(
            f"Chromium render failed (exit {proc.returncode}):\n{proc.stderr[-2000:]}"
        )


def build_html(template_key: str, slots: dict, bg_url: str, width: int, height: int,
               textlayer: bool) -> str:
    spec = TEMPLATES[template_key]
    doc = spec["html"]
    doc = doc.replace("%%RESET%%", CSS_RESET)
    doc = doc.replace("%%W%%", str(width)).replace("%%H%%", str(height))
    if bg_url:
        doc = doc.replace("%%BG%%", f'url("{bg_url}")')
    else:
        doc = doc.replace(
            "%%BG%%", "linear-gradient(160deg, #16265e 0%, #274b8f 55%, #0d1838 100%)"
        )
    doc = doc.replace("%%TEXTLAYER_CSS%%", spec["textlayer_css"] if textlayer else "")
    if template_key == "art-broken":
        chars = slots.get("TITLE", "")
        spans = "".join(
            f'<span class="char c{i + 1}">{html.escape(ch)}</span>'
            for i, ch in enumerate(chars[:5])
        )
        doc = doc.replace("%%CHARS%%", spans)
        watermark = slots.get("WATERMARK") or (chars[-2:] if len(chars) >= 2 else chars)
        doc = doc.replace("%%WATERMARK%%", html.escape(watermark))
    for key in set(DEFAULT_SLOTS) | set(slots):
        doc = doc.replace(f"%%{key}%%", esc(slots.get(key, DEFAULT_SLOTS.get(key, ""))))
    return doc


def dilate(mask_img, radius_px: int):
    from PIL import ImageFilter

    size = radius_px * 2 + 1
    return mask_img.filter(ImageFilter.MaxFilter(size))


def build_masks(textlayer_png: str, out_dir: str, mode: str) -> dict:
    """Derive protection + repaint masks from the text layer alpha channel.

    Returns dict with foreground coverage ratio and file names.
    Mask convention (diffusers inpaint): white = repaint, black = keep.
    """
    from PIL import Image

    layer = Image.open(textlayer_png).convert("RGBA")
    alpha = layer.split()[3]
    glyph = alpha.point(lambda a: 255 if a >= 128 else 0)
    total = glyph.size[0] * glyph.size[1]
    coverage = round(glyph.histogram()[255] / total, 4)

    protection = dilate(glyph, 6)  # foreground + 6 px: never repainted
    if mode == "halo":
        outer = dilate(glyph, 44)
        repaint = Image.composite(
            Image.new("L", glyph.size, 255), Image.new("L", glyph.size, 0), outer
        )
        repaint = Image.composite(
            Image.new("L", glyph.size, 0), repaint, protection
        )
    elif mode == "full":
        repaint = Image.composite(
            Image.new("L", glyph.size, 0),
            Image.new("L", glyph.size, 255),
            protection,
        )
    else:
        raise SystemExit(f"unknown blend mode '{mode}'")

    protect_path = os.path.join(out_dir, "mask_protection.png")
    repaint_path = os.path.join(out_dir, "mask_repaint.png")
    protection.save(protect_path)
    repaint.save(repaint_path)
    return {"coverage": coverage, "protection": protect_path, "repaint": repaint_path}


def overlay_text(base_png: str, textlayer_png: str, out_png: str) -> None:
    from PIL import Image

    base = Image.open(base_png).convert("RGBA")
    layer = Image.open(textlayer_png).convert("RGBA")
    if layer.size != base.size:
        layer = layer.resize(base.size)
    base.alpha_composite(layer)
    base.convert("RGB").save(out_png)


# ------------------------------------------------------------------- stages

def stage_render(args) -> dict:
    os.makedirs(args.out, exist_ok=True)
    spec = TEMPLATES[args.template]
    if args.size:
        width, height = (int(v) for v in args.size.lower().split("x"))
    else:
        width, height = spec["default_size"]

    slots = dict(DEFAULT_SLOTS)
    for key, value in args.slot_values.items():
        if value is not None:
            slots[key] = value
    if args.slots_json:
        slots.update(json.loads(args.slots_json))

    bg_url = ""
    if args.bg:
        if not os.path.isfile(args.bg):
            raise SystemExit(f"background image not found: {args.bg}")
        bg_url = "file://" + os.path.abspath(args.bg)

    chrome = find_chrome(args.chrome)
    info = {"chrome": chrome, "size": f"{width}x{height}", "template": args.template}

    full_html = os.path.join(args.out, "poster.html")
    with open(full_html, "w", encoding="utf-8") as f:
        f.write(build_html(args.template, slots, bg_url, width, height, textlayer=False))
    composite = os.path.join(args.out, "composite.png")
    render_png(chrome, full_html, composite, width, height, transparent=False)
    info["composite"] = composite

    layer_html = os.path.join(args.out, "textlayer.html")
    with open(layer_html, "w", encoding="utf-8") as f:
        f.write(build_html(args.template, slots, bg_url, width, height, textlayer=True))
    textlayer = os.path.join(args.out, "textlayer.png")
    render_png(chrome, layer_html, textlayer, width, height, transparent=True)
    info["textlayer"] = textlayer
    info["slots"] = {k: slots[k] for k in spec["slots"] if k in slots}
    return info


def stage_blend(args, info: dict) -> dict:
    prompt = args.blend_prompt
    hits = text_mentions(prompt)
    if hits and not args.force:
        raise SystemExit(
            "Blend prompt mentions text "
            f"({', '.join(hits)}). Measured rule (TEXT-003): prompts that "
            "talk about lettering make the model redraw and garble it. Use "
            "abstract style words only, or pass --force to override."
        )

    masks = build_masks(info["textlayer"], args.out, args.blend_mode)
    info["masks"] = masks

    if _modal is None:
        raise SystemExit(
            "The blend stage needs the Modal client. Install it and finish "
            "the Modal setup first (manual chapters 03-05): pip install modal"
        )

    with open(info["composite"], "rb") as f:
        composite_bytes = f.read()
    with open(masks["repaint"], "rb") as f:
        mask_bytes = f.read()

    with _app.run():
        result = _blend_remote.remote(
            composite_bytes, mask_bytes, args.blend_steps, args.seed, prompt
        )

    blended = os.path.join(args.out, "blended.png")
    with open(blended, "wb") as f:
        f.write(result["png"])
    final = os.path.join(args.out, "final.png")
    overlay_text(blended, info["textlayer"], final)

    gpu_seconds = result["load_s"] + result["seconds"]
    info["blend"] = {
        "mode": args.blend_mode,
        "steps": args.blend_steps,
        "seed": args.seed,
        "prompt": prompt,
        "load_seconds": result["load_s"],
        "blend_seconds": result["seconds"],
        "gpu_seconds_total": round(gpu_seconds, 1),
        "est_cost_usd": round(gpu_seconds * A10_USD_PER_SEC, 3),
        "blended": blended,
        "final": final,
    }
    return info


def write_manifest(args, info: dict) -> str:
    manifest = {
        "tool": f"poster.py {TOOL_VERSION}",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "command": args.command,
        **info,
    }
    path = os.path.join(args.out, "poster_manifest.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=1)
    return path


# ---------------------------------------------------------------------- CLI

def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        description="Poster compositing: HTML/CSS text over a generated "
                    "background, optional masked blend pass, pixel-exact "
                    "text re-overlay. See the module docstring for the pipeline."
    )
    sub = ap.add_subparsers(dest="command", required=True)

    def add_common(p):
        p.add_argument("--bg", default="", help="background image PNG (e.g. a studio.py output). "
                                                 "Omit for a plain gradient background.")
        p.add_argument("--template", default="orderly",
                       choices=sorted(TEMPLATES),
                       help="poster layout template (default: orderly)")
        p.add_argument("--out", required=True, help="output directory")
        p.add_argument("--size", default="", help="canvas size WxH (default: template size)")
        p.add_argument("--chrome", default="", help="Chromium/Chrome binary path "
                                                    "(default: auto-detect, CHROME_BIN env)")
        p.add_argument("--slots-json", default="", help="JSON object overriding any text slot")
        # common text slots
        p.add_argument("--title", help="main title (orderly: vertical; art-broken: per-character)")
        p.add_argument("--subtitle", help="subtitle (art-broken: the diagonal tape text)")
        p.add_argument("--band-left", dest="band_left", help="bottom band, left text")
        p.add_argument("--band-right", dest="band_right", help="bottom band, right text (orderly)")
        p.add_argument("--frag1", help="art-broken: scattered fragment 1")
        p.add_argument("--frag2", help="art-broken: scattered fragment 2")
        p.add_argument("--badge", help="art-broken: round badge text (newline = line break)")
        p.add_argument("--watermark", help="art-broken: big rotated watermark "
                                           "(default: last 2 characters of --title)")
        # recruit slots
        p.add_argument("--tag", help="recruit: top-left tag")
        p.add_argument("--ribbon", help="recruit: ribbon text over the photo")
        p.add_argument("--title-main", dest="title_main", help="recruit: big title, main part")
        p.add_argument("--title-sub", dest="title_sub", help="recruit: big title, smaller suffix")
        p.add_argument("--title-line2", dest="title_line2", help="recruit: second title line")
        p.add_argument("--circle1", help="recruit: circle 1 text (newline = line break)")
        p.add_argument("--circle2", help="recruit: circle 2 text")
        p.add_argument("--circle3", help="recruit: circle 3 text")
        p.add_argument("--visit", help="recruit: underlined announcement line")
        p.add_argument("--org-name", dest="org_name", help="recruit: organisation name (footer)")
        p.add_argument("--org-info", dest="org_info", help="recruit: address / phone (footer)")

    p_render = sub.add_parser("render", help="render composite + text layer (no Modal, no cost)")
    add_common(p_render)

    p_blend = sub.add_parser("blend", help="render + masked blend pass on Modal + final re-overlay")
    add_common(p_blend)
    p_blend.add_argument("--blend-mode", dest="blend_mode", default="halo",
                         choices=["halo", "full"],
                         help="halo: repaint only a 44px ring around the text (standard). "
                              "full: repaint everything except the protected text zone "
                              "(restyles the artwork while the text stays fixed).")
    p_blend.add_argument("--blend-steps", dest="blend_steps", type=int, default=6,
                         help="inpaint steps (default: 6; 12 showed no visible gain)")
    p_blend.add_argument("--seed", type=int, default=9100, help="blend seed (default: 9100)")
    p_blend.add_argument("--blend-prompt", dest="blend_prompt", default=BLEND_PROMPT_DEFAULT,
                         help="abstract style prompt for the blend pass. Must NOT mention "
                              "text/lettering (measured rule).")
    p_blend.add_argument("--force", action="store_true",
                         help="allow a text-mentioning blend prompt (not recommended)")
    return ap


SLOT_ARG_MAP = {
    "title": "TITLE", "subtitle": "SUBTITLE", "band_left": "BAND_LEFT",
    "band_right": "BAND_RIGHT", "frag1": "FRAG1", "frag2": "FRAG2",
    "badge": "BADGE", "watermark": "WATERMARK", "tag": "TAG",
    "ribbon": "RIBBON", "title_main": "TITLE_MAIN", "title_sub": "TITLE_SUB",
    "title_line2": "TITLE_LINE2", "circle1": "CIRCLE1", "circle2": "CIRCLE2",
    "circle3": "CIRCLE3", "visit": "VISIT", "org_name": "ORG_NAME",
    "org_info": "ORG_INFO",
}


def main() -> None:
    args = build_parser().parse_args()
    args.slot_values = {
        slot: getattr(args, attr) for attr, slot in SLOT_ARG_MAP.items()
    }
    info = stage_render(args)
    if args.command == "blend":
        info = stage_blend(args, info)
    manifest_path = write_manifest(args, info)
    summary = {
        "out": args.out,
        "composite": info["composite"],
        "manifest": manifest_path,
    }
    if "blend" in info:
        summary["final"] = info["blend"]["final"]
        summary["est_cost_usd"] = info["blend"]["est_cost_usd"]
    print(json.dumps(summary, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
