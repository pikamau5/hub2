#!/usr/bin/env python3
import json
import re
import subprocess
from datetime import datetime
from pathlib import Path

# Uses the repo you run it from
REPO_DIR = Path.cwd()
ITEMS_DIR = REPO_DIR / "items"
MANIFEST = ITEMS_DIR / "manifest.json"

DEFAULT_TYPE = "book"

def run(cmd, cwd=None, check=True):
    p = subprocess.run(cmd, cwd=cwd, text=True, capture_output=True)
    if check and p.returncode != 0:
        if p.stdout:
            print(p.stdout, end="")
        if p.stderr:
            print(p.stderr, end="")
        raise SystemExit(p.returncode)
    return p

def slugify(s: str) -> str:
    s = s.strip().lower()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_-]+", "-", s)
    s = re.sub(r"^-+|-+$", "", s)
    return s or "item"

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

def load_json(path: Path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))

def save_json(path: Path, data):
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

def ensure_repo():
    if not (REPO_DIR / ".git").exists():
        raise SystemExit(f"Not a git repo: {REPO_DIR} (no .git directory). cd into hub2 and run again.")
    ITEMS_DIR.mkdir(parents=True, exist_ok=True)
    if not MANIFEST.exists():
        save_json(MANIFEST, [])

def sync_repo():
    run(["git", "fetch", "--prune"], cwd=REPO_DIR)
    run(["git", "pull", "--rebase"], cwd=REPO_DIR)

def main():
    ensure_repo()

    # sync before changes
    sync_repo()

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
    print(f"\nWrote: {item_path}")

    # update manifest
    manifest = load_json(MANIFEST, default=[])
    if not isinstance(manifest, list):
        manifest = []

    if filename not in manifest:
        manifest.append(filename)

    # sort manifest newest-first using each item's date
    dated = []
    for fn in manifest:
        p = ITEMS_DIR / fn
        if p.exists():
            try:
                obj = load_json(p, default={})
                d = str(obj.get("date", "0000-01-01T00:00"))
            except Exception:
                d = "0000-01-01T00:00"
        else:
            d = "0000-01-01T00:00"
        dated.append((d, fn))

    dated.sort(key=lambda x: x[0], reverse=True)
    save_json(MANIFEST, [fn for _, fn in dated])

    # commit
    run(["git", "add", "items"], cwd=REPO_DIR)

    status = run(["git", "status", "--porcelain"], cwd=REPO_DIR, check=False).stdout.strip()
    if not status:
        print("\nNothing to commit.")
        return

    run(["git", "commit", "-m", f"Add item: {title}"], cwd=REPO_DIR)

    # sync again (avoid push rejection), then push
    try:
        sync_repo()
    except SystemExit:
        print("\n❌ Rebase failed (conflict).")
        print(f"Go to: cd {REPO_DIR}")
        print("Then run:")
        print("  git status")
        print("  git rebase --continue")
        print("  git push")
        raise

    run(["git", "push"], cwd=REPO_DIR)

    print(f"\n✅ Added + pushed: {title}")
    print(f"   File: items/{filename}")
    print(f"   Date: {timestamp}")

if __name__ == "__main__":
    main()
