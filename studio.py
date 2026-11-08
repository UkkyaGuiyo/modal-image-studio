# image-studio: batch image generation / variation on Modal (FLUX.2-klein-4B).
# One Modal container session runs a whole batch sequentially (cost control).
# The local entrypoint writes PNGs, manifest.json and a labelled contact sheet
# into runs/<timestamp>_<run-name>/.
#
# Modes:
#   generate : text -> images
#   variate  : reference image + instruction -> edited images
#              (--ref <png> or --from-selection <run-dir> to use that run's pick)
#
# Styles: --style appends a tested design-language suffix to every prompt.
# Selection: after presenting a run's contact sheet, record the human's pick
# with select.py (writes selection.json into the run dir).
import base64
import io
import json
import time

import modal

app = modal.App("image-studio")

weights = modal.Volume.from_name("flux2-klein-weights", create_if_missing=True)
WEIGHTS_DIR = "/weights"
MODEL_ID = "black-forest-labs/FLUX.2-klein-4B"

image = (
    modal.Image.from_registry(
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
    .env({"HF_HOME": WEIGHTS_DIR + "/hf"})
)

# Design languages verified by benchmark (see docs). Appended to the prompt.
STYLES = {
    # --- classic art styles ---
    "watercolor": "soft watercolor painting, gentle color bleeding, visible paper texture",
    "ukiyo-e": "Japanese ukiyo-e woodblock print, flat color areas, bold black outlines",
    "pixel-art": "detailed pixel art, limited color palette, crisp pixels",
    "oil-painting": "classical oil painting, visible brushstrokes, rich layered color",
    "photorealistic": "photorealistic, natural lighting, fine detail, shot on a 35mm lens",
    "ink-manga": "black and white ink manga illustration, screentones, strong line work",
    "pastel": "soft pastel illustration, gentle light colors, dreamy atmosphere",
    "cyberpunk": "cyberpunk style, neon lights, rain-slick streets, high-tech mood",
    # --- strong graphic design languages ---
    "quiet-blue": (
        "cool teal-blue monochromatic palette with subtle yellow accents, "
        "translucent glass panels, soft water ripples and floating bubbles, "
        "moon-phase symbols and circular geometry, elegant negative space, "
        "atmospheric underwater lighting and soft reflections"
    ),
    "retro-tv-pop": (
        "warm saturated yellow and amber palette with bold black contrast, "
        "retro television broadcast graphics, multicolor horizontal television "
        "signal stripes, CRT scanlines and subtle analog static, thick black "
        "rectangular frames, atmospheric yellow fog, playful ensemble composition"
    ),
    "pop-punk-red": (
        "high-contrast scarlet red, black and white palette, aggressive pop-punk "
        "editorial graphic design, sharp diagonal cuts and jagged geometric shapes, "
        "kinetic asymmetrical collage composition, bold black ink shading, "
        "subtle halftone dots and photocopy grain"
    ),
}


@app.function(
    image=image,
    gpu="A10",
    volumes={WEIGHTS_DIR: weights},
    timeout=1800,
)
def run_batch(jobs: list[dict], model_id: str = MODEL_ID) -> dict:
    import torch
    from diffusers import Flux2KleinPipeline
    from PIL import Image

    t0 = time.perf_counter()
    pipe = Flux2KleinPipeline.from_pretrained(model_id, torch_dtype=torch.bfloat16)
    pipe.to("cuda")
    torch.cuda.synchronize()
    load_seconds = round(time.perf_counter() - t0, 2)
    weights.commit()

    out = []
    for job in jobs:
        gen = torch.Generator(device="cuda").manual_seed(job["seed"])
        t0 = time.perf_counter()
        if job["kind"] == "edit":
            ref = Image.open(io.BytesIO(base64.b64decode(job["image_b64"])))
            img = pipe(
                image=[ref],
                prompt=job["prompt"],
                height=job.get("height", 1024),
                width=job.get("width", 1024),
                guidance_scale=job.get("guidance", 1.0),
                num_inference_steps=job.get("steps", 4),
                generator=gen,
            ).images[0]
        else:
            img = pipe(
                prompt=job["prompt"],
                height=job.get("height", 1024),
                width=job.get("width", 1024),
                guidance_scale=job.get("guidance", 1.0),
                num_inference_steps=job.get("steps", 4),
                generator=gen,
            ).images[0]
        torch.cuda.synchronize()
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        out.append(
            {
                "png_b64": base64.b64encode(buf.getvalue()).decode(),
                "seconds": round(time.perf_counter() - t0, 2),
            }
        )
    return {"load_seconds": load_seconds, "results": out}


def make_contact_sheet(paths: list[str], labels: list[str], out_path: str) -> None:
    from PIL import Image, ImageDraw, ImageFont

    thumb = 384
    label_h = 36
    cols = 4
    rows = (len(paths) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * thumb, rows * (thumb + label_h)), "white")
    draw = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.load_default(size=24)
    except TypeError:
        font = ImageFont.load_default()
    for i, (p, label) in enumerate(zip(paths, labels)):
        im = Image.open(p).convert("RGB")
        im.thumbnail((thumb, thumb))
        x = (i % cols) * thumb
        y = (i // cols) * (thumb + label_h)
        sheet.paste(im, (x, y))
        draw.text((x + 8, y + thumb + 6), label, fill="black", font=font)
    sheet.save(out_path)


@app.local_entrypoint()
def main(
    mode: str = "generate",
    prompt: str = "A retro travel poster of a mountain lake at dawn, flat colors, no text",
    count: int = 8,
    base_seed: int = 1000,
    ref: str = "",
    from_selection: str = "",
    run_name: str = "run",
    prompts_json: str = "",
    size: str = "1:1",
    model: str = "distilled",
    steps: int = 4,
    guidance: float = 1.0,
    style: str = "",
):
    import os
    from datetime import datetime

    SIZE_PRESETS = {
        "1:1": (1024, 1024),
        "3:4": (896, 1184),
        "4:3": (1184, 896),
        "2:3": (832, 1248),
        "3:2": (1248, 832),
        "16:9": (1376, 768),
        "9:16": (768, 1376),
    }
    if size in SIZE_PRESETS:
        width, height = SIZE_PRESETS[size]
    else:
        width, height = (int(v) for v in size.lower().split("x"))

    if style and style not in STYLES:
        raise SystemExit(f"unknown style '{style}'. Available: {', '.join(STYLES)}")

    # Resolve the reference image for variate mode.
    parent_label = None
    if mode == "variate":
        if from_selection:
            sel_path = os.path.join(from_selection, "selection.json")
            with open(sel_path) as f:
                sel = json.load(f)
            ref = sel["picked_path"]
            parent_label = f"{os.path.basename(from_selection)}/{sel['picked_file']}"
        if not ref:
            raise SystemExit("variate mode needs --ref <png> or --from-selection <run-dir>")

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = os.path.join("runs", f"{stamp}_{run_name}")
    os.makedirs(run_dir, exist_ok=True)

    if prompts_json:
        prompt_list = json.loads(prompts_json)
        count = len(prompt_list)
    else:
        prompt_list = [prompt] * count
    if style:
        prompt_list = [f"{p}. Style: {STYLES[style]}" for p in prompt_list]

    model_id_active = (
        "black-forest-labs/FLUX.2-klein-base-4B"
        if model == "base"
        else MODEL_ID
    )
    jobs = []
    meta = []
    ref_b64 = ""
    if mode == "variate":
        with open(ref, "rb") as f:
            ref_b64 = base64.b64encode(f.read()).decode()
    for i in range(count):
        seed = base_seed + i
        job = {"prompt": prompt_list[i], "seed": seed, "steps": steps, "guidance": guidance, "height": height, "width": width}
        if mode == "variate":
            job["kind"] = "edit"
            job["image_b64"] = ref_b64
        else:
            job["kind"] = "generate"
        jobs.append(job)
        meta.append(
            {
                "id": f"img_{i + 1:03d}",
                "kind": job["kind"],
                "parent": parent_label or (os.path.basename(ref) if mode == "variate" else None),
                "prompt": prompt_list[i],
                "seed": seed,
                "steps": steps,
                "size": f"{width}x{height}",
                "model": model_id_active,
                "style": style or None,
            }
        )

    t0 = time.perf_counter()
    result = run_batch.remote(jobs, model_id_active)
    wall = round(time.perf_counter() - t0, 2)

    paths, labels = [], []
    for m, r in zip(meta, result["results"]):
        p = os.path.join(run_dir, f"{m['id']}.png")
        with open(p, "wb") as f:
            f.write(base64.b64decode(r["png_b64"]))
        m["seconds"] = r["seconds"]
        m["file"] = os.path.basename(p)
        paths.append(p)
        labels.append(f"{m['id']}  seed {m['seed']}")

    manifest = {
        "run_dir": run_dir,
        "mode": mode,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "load_seconds": result["load_seconds"],
        "wall_seconds_incl_queue": wall,
        "images": meta,
    }
    with open(os.path.join(run_dir, "manifest.json"), "w") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=1)
    make_contact_sheet(paths, labels, os.path.join(run_dir, "contact_sheet.png"))
    total_gpu = result["load_seconds"] + sum(m["seconds"] for m in meta)
    print(
        json.dumps(
            {
                "run_dir": run_dir,
                "count": count,
                "load_seconds": result["load_seconds"],
                "per_image_seconds": [m["seconds"] for m in meta],
                "gpu_seconds_total": round(total_gpu, 1),
                "est_cost_usd": round(total_gpu * 0.000306, 3),
                "wall_seconds": wall,
            },
            ensure_ascii=False,
            indent=1,
        )
    )
