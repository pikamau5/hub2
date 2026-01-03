#!/usr/bin/env python3
import json
import os
import re
import subprocess
from datetime import datetime
from pathlib import Path

# --- settings ---
REPO_SSH = "git@github-pikamau5:pikamau5/hub2.git"  # uses SSH alias in ~/.ssh/config
LOCAL_DIR = Path.home() / "hub2"                    # where to clone / work
ITEMS_DIR = LOCAL_DIR / "items"
MANIFEST = ITEMS_DIR / "manifest.json"
DEFAULT_TYPE = "book"

def run(cmd, cwd=None):
    p = subprocess.run(cmd, cwd=cwd, text=True)
    if p.returncode != 0:
        raise SystemExit(p.returncode)

def slugify(s: str) -> str:
    s = s.strip().lower()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_-]+", "-", s)
    s = re.sub(r"^-+|-+$", "", s)
    return s or "item"

def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))

def save_json(path: Path, data):
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

def prompt_multiline(prompt: str) -> str:
    print(prompt)
    print("(finish with an empty line)")
    lines = []
    while True:
        line = input()
        if line == "":
            break
        lines.append(line)
    return "\n".join(lines)

def ensure_repo():
    if (LOCAL_DIR / ".git").exists():
        return
    print(f"Cloning into {LOCAL_DIR} …")
    run(["git", "clone", REPO_SSH, str(LOCAL_DIR)])

def ensure_dirs():
    ITEMS_DIR.mkdir(parents=True, exist_ok=True)
    if not MANIFEST.exists():
        save_json(MANIFEST, [])

def parse_date_for_sort(d: str) -> str:
    # ISO strings sort lexicographically if consistent: YYYY-MM-DDTHH:MM
    # fallback to very old date
    return d if isinstance(d, str) and d else "0000-01-01T00:00"

def main():
    ensure_repo()
    ensure_dirs()

    print("➜ Add reading list item (GitHub)\n")

    url = input("URL: ").strip()
    if not url:
        print("URL is required.")
        return

    title = input("Title: ").strip()
    if not title:
        print("Title is required.")
        return

    notes = prompt_multiline("Notes:")

    filename = slugify(title) + ".json"
    timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M")

    item = {
        "name": title,
        "url": url,
        "date": timestamp,
        "type": DEFAULT_TYPE,
        "notes": notes
    }

    item_path = ITEMS_DIR / filename
    save_json(item_path, item)

    # Update manifest
    manifest = load_json(MANIFEST)
    if not isinstance(manifest, list):
        manifest = []

    if filename not in manifest:
        manifest.append(filename)

    # Sort newest-first by each item's date
    dated = []
    for fn in manifest:
        p = ITEMS_DIR / fn
        if p.exists():
            try:
                obj = load_json(p)
                d = parse_date_for_sort(obj.get("date", ""))
            except Exception:
                d = "0000-01-01T00:00"
        else:
            d = "0000-01-01T00:00"
        dated.append((d, fn))

    dated.sort(key=lambda x: x[0], reverse=True)
    save_json(MANIFEST, [fn for _, fn in dated])

    # Git commit + push
    run(["git", "add", "items"], cwd=LOCAL_DIR)

    # If nothing changed, don't fail
    status = subprocess.check_output(["git", "status", "--porcelain"], cwd=LOCAL_DIR, text=True).strip()
    if not status:
        print("\nNothing to commit.")
        return

    msg = f"Add item: {title}"
    run(["git", "commit", "-m", msg], cwd=LOCAL_DIR)
    run(["git", "push"], cwd=LOCAL_DIR)

    print(f"\n✅ Added + pushed: {title}")
    print(f"   File: items/{filename}")
    print(f"   Date: {timestamp}")

if __name__ == "__main__":
    main()
