#!/usr/bin/env python3
"""Record the human's pick from a generation run.

Usage:
  python3 select.py --run runs/<timestamp>_<name> --list
  python3 select.py --run runs/<timestamp>_<name> --pick img_003 [--note "..."]

Writes selection.json into the run directory. The pick is always made by a
human; this tool only records it. studio.py --mode variate --from-selection
<run-dir> then expands variations around the recorded pick.
Re-running with a different --pick replaces the current pick and appends the
previous one to "history".
"""
import argparse
import json
import os
from datetime import datetime


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True, help="run directory containing manifest.json")
    ap.add_argument("--pick", default="", help="image id to record as the pick, e.g. img_003")
    ap.add_argument("--note", default="", help="free-text note stored with the pick")
    ap.add_argument("--list", action="store_true", help="list the run's images and exit")
    args = ap.parse_args()

    manifest_path = os.path.join(args.run, "manifest.json")
    with open(manifest_path) as f:
        manifest = json.load(f)
    images = {img["id"]: img for img in manifest["images"]}

    if args.list or not args.pick:
        for img in manifest["images"]:
            print(f"{img['id']}  {img['file']}  seed {img['seed']}  {img['prompt'][:60]}")
        if not args.pick:
            return

    if args.pick not in images:
        raise SystemExit(f"pick '{args.pick}' not in run. Available: {', '.join(images)}")

    picked = images[args.pick]
    entry = {
        "picked_id": picked["id"],
        "picked_file": picked["file"],
        "picked_path": os.path.join(args.run, picked["file"]),
        "prompt": picked["prompt"],
        "seed": picked["seed"],
        "parent": picked.get("parent"),
        "decided_at": datetime.now().isoformat(timespec="seconds"),
        "decided_by": "human",
        "note": args.note,
    }

    sel_path = os.path.join(args.run, "selection.json")
    history = []
    if os.path.exists(sel_path):
        with open(sel_path) as f:
            prev = json.load(f)
        history = prev.get("history", [])
        if prev.get("picked_id"):
            history.append({k: prev[k] for k in ("picked_id", "picked_file", "decided_at", "note") if k in prev})

    selection = {"run_dir": args.run, **entry, "history": history}
    with open(sel_path, "w") as f:
        json.dump(selection, f, ensure_ascii=False, indent=1)
    print(json.dumps({"selection_written": sel_path, "picked": entry["picked_id"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
