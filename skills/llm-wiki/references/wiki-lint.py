#!/usr/bin/env python3
"""Wiki lint script — run via execute_code. Requires: wiki path as argument or set WIKI env."""
import os, re, sys
from collections import defaultdict

wiki = os.environ.get("WIKI_PATH", os.path.expanduser("~/wiki"))
if not os.path.isdir(wiki):
    print(f"ERROR: {wiki} not found")
    sys.exit(1)

# --- Collect wiki pages in tracked dirs ---
page_files = {}  # name -> relative path
for d in ["entities", "concepts", "comparisons", "queries"]:
    path = os.path.join(wiki, d)
    if os.path.exists(path):
        for f in os.listdir(path):
            if f.endswith(".md"):
                page_files[f.replace(".md", "")] = os.path.join(d, f)

print(f"Total wiki pages: {len(page_files)}")

# --- Build wikilink graph ---
inbound = defaultdict(set)
broken_links = []

for name, pf in page_files.items():
    content = open(os.path.join(wiki, pf)).read()
    for link in re.findall(r'\[\[(.*?)\]\]', content):
        target = link.split("|")[0].strip()
        inbound[target].add(name)
        if target not in page_files and not target.startswith("raw/") and not target.startswith("_"):
            broken_links.append(f"  {name} -> [[{target}]]")

print(f"\n=== Broken wikilinks: {len(broken_links)} ===")
for b in broken_links:
    print(b)

# --- Orphan pages ---
orphans = [n for n in page_files if n not in inbound]
print(f"\n=== Orphan pages: {len(orphans)} ===")
for o in sorted(orphans):
    print(f"  {o} ({page_files[o]})")

# --- Index completeness ---
index_content = open(os.path.join(wiki, "index.md")).read()
index_links = set(l.split("|")[0].strip() for l in re.findall(r'\[\[(.*?)\]\]', index_content))
missing = set(page_files.keys()) - index_links
extra = index_links - set(page_files.keys())
if missing:
    print(f"\n=== MISSING from index.md: {len(missing)} ===")
    for m in sorted(missing):
        print(f"  {m}")
if extra:
    print(f"\n=== Extra in index.md: {len(extra)} ===")
    for e in sorted(extra):
        print(f"  {e}")
if not missing:
    print(f"\n=== index.md complete ✓ ===")

# --- Frontmatter audit ---
required = ["title", "created", "updated", "type", "tags", "sources"]
missing_fm = {}
for name, pf in page_files.items():
    content = open(os.path.join(wiki, pf)).read()
    if not content.strip().startswith("---"):
        missing_fm[name] = "NO FRONTMATTER"
    else:
        m = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
        if m:
            for field in required:
                if not re.search(rf'^{field}\s*:', m.group(1), re.MULTILINE):
                    missing_fm[name] = missing_fm.get(name, "") + f"missing:{field}; "
if missing_fm:
    print(f"\n=== Frontmatter issues: {len(missing_fm)} ===")
    for k, v in missing_fm.items():
        print(f"  {k}: {v}")
else:
    print(f"\n=== Frontmatter complete ✓ ===")

# --- Tag audit ---
schema = open(os.path.join(wiki, "SCHEMA.md")).read()
tax_m = re.search(r'## Tag Taxonomy\n(.*?)(?:\n## |\Z)', schema, re.DOTALL)
valid_tags = set()
if tax_m:
    for line in tax_m.group(1).strip().split("\n"):
        if ":" in line:
            valid_tags.update(t.strip() for t in line.split(":", 1)[1].split(","))

all_used = set()
for name, pf in page_files.items():
    content = open(os.path.join(wiki, pf)).read()
    m = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
    if m and (tags_m := re.search(r'tags:\s*\[(.*?)\]', m.group(1))):
        all_used.update(t.strip() for t in tags_m.group(1).split(","))

invalid = all_used - valid_tags
print(f"\n=== Tags: {len(all_used)} in use, {len(invalid)} not in SCHEMA ===")
for t in sorted(invalid):
    print(f"  INVALID: {t}")

# --- Page size ---
large = [(n, os.path.join(wiki, pf), sum(1 for _ in open(os.path.join(wiki, pf))))
         for n, pf in page_files.items() if sum(1 for _ in open(os.path.join(wiki, pf))) > 200]
if large:
    print(f"\n=== Pages > 200 lines ===")
    for n, pf, lines in large:
        print(f"  {pf}: {lines}")

# --- Raw/ frontmatter ---
raw_no_fm, raw_no_sha = [], []
for root, _, files in os.walk(os.path.join(wiki, "raw")):
    for f in files:
        if not f.endswith(".md"): continue
        fp = os.path.join(root, f)
        c = open(fp).read()
        if not c.strip().startswith("---"):
            raw_no_fm.append(fp)
        elif "sha256" not in (m.group(1) if (m := re.match(r'^---\n(.*?)\n---', c, re.DOTALL)) else ""):
            raw_no_sha.append(fp)
print(f"\n=== Raw/: no frontmatter={len(raw_no_fm)}, missing sha256={len(raw_no_sha)} ===")
