#!/usr/bin/env python3
"""
Wiki Health Check (Linter) for Karpathy-style LLM Wiki.
Run against a wiki directory to find structural issues.

Usage: python wiki_lint.py /path/to/wiki
       # or: python wiki_lint.py  (defaults to ~/wiki)

Checks:
  1. Orphan pages (no inbound [[wikilinks]])
  2. Broken wikilinks (targets that don't exist)
  3. Missing frontmatter on wiki pages
  4. Missing required frontmatter fields
  5. Tags not in SCHEMA.md taxonomy
  6. Pages not listed in index.md
  7. Pages over 200 lines (split candidates)
"""
import os, re, sys
from collections import defaultdict

WIKI_DIRS = ["entities", "concepts", "comparisons", "queries"]
REQUIRED_FM = ["title", "created", "updated", "type", "tags", "sources"]

def collect_pages(wiki):
    pages = {}
    for d in WIKI_DIRS:
        path = os.path.join(wiki, d)
        if os.path.exists(path):
            for f in os.listdir(path):
                if f.endswith(".md"):
                    pages[f.replace(".md", "")] = os.path.join(d, f)
    return pages

def read_page(wiki, pf):
    return open(os.path.join(wiki, pf)).read()

def parse_frontmatter(content):
    m = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
    if m:
        return m.group(1)
    return None

def lint(wiki):
    pages = collect_pages(wiki)
    issues = defaultdict(list)

    # Build wikilink graph
    inbound = defaultdict(set)
    for name, pf in pages.items():
        content = read_page(wiki, pf)
        links = re.findall(r'\[\[(.*?)\]\]', content)
        for link in links:
            target = link.split("|")[0].strip()
            inbound[target].add(name)

    # 1. Orphan pages
    for name in pages:
        if name not in inbound:
            issues["orphans"].append(name)

    # 2. Broken wikilinks
    for name, pf in pages.items():
        content = read_page(wiki, pf)
        links = re.findall(r'\[\[(.*?)\]\]', content)
        for link in links:
            target = link.split("|")[0].strip()
            if target not in pages and not target.startswith("raw/") and not target.startswith("_archive"):
                issues["broken_links"].append(f"{name} -> [[{target}]]")

    # 3-4. Frontmatter audit
    for name, pf in pages.items():
        content = read_page(wiki, pf)
        fm = parse_frontmatter(content)
        if fm is None:
            issues["no_frontmatter"].append(name)
            continue
        for field in REQUIRED_FM:
            if not re.search(rf'^{field}\s*:', fm, re.MULTILINE):
                issues["missing_fm_field"].append(f"{name}: missing '{field}'")

    # 5. Tag taxonomy audit
    schema_path = os.path.join(wiki, "SCHEMA.md")
    valid_tags = set()
    if os.path.exists(schema_path):
        schema = open(schema_path).read()
        tax_m = re.search(r'## Tag Taxonomy\n(.*?)(?:\n## |\Z)', schema, re.DOTALL)
        if tax_m:
            for line in tax_m.group(1).strip().split("\n"):
                if ":" in line:
                    valid_tags.update(t.strip() for t in line.split(":", 1)[1].split(","))

    for name, pf in pages.items():
        content = read_page(wiki, pf)
        fm = parse_frontmatter(content)
        if fm:
            tags_m = re.search(r'tags:\s*\[(.*?)\]', fm)
            if tags_m:
                tags = [t.strip() for t in tags_m.group(1).split(",")]
                for t in tags:
                    if t not in valid_tags:
                        issues["invalid_tags"].append(f"{name}: tag '{t}' not in SCHEMA taxonomy")

    # 6. Index completeness
    index_path = os.path.join(wiki, "index.md")
    if os.path.exists(index_path):
        index_content = open(index_path).read()
        index_links = set(l.split("|")[0].strip() for l in re.findall(r'\[\[(.*?)\]\]', index_content))
        for name in pages:
            if name not in index_links:
                issues["missing_from_index"].append(name)

    # 7. Page size
    for name, pf in pages.items():
        lines = sum(1 for _ in open(os.path.join(wiki, pf)))
        if lines > 200:
            issues["oversized"].append(f"{pf}: {lines} lines")

    return issues, len(pages)

def report(issues, total_pages):
    severity_order = ["broken_links", "no_frontmatter", "missing_fm_field", "invalid_tags", "missing_from_index", "orphans", "oversized"]
    labels = {
        "broken_links": "💥 BROKEN LINKS",
        "no_frontmatter": "📄 NO FRONTMATTER",
        "missing_fm_field": "📋 MISSING FM FIELDS",
        "invalid_tags": "🏷️ INVALID TAGS",
        "missing_from_index": "📑 MISSING FROM INDEX",
        "orphans": "🔗 ORPHAN PAGES",
        "oversized": "📏 OVERSIZED PAGES (>200 lines)",
    }

    total_issues = sum(len(v) for v in issues.values())
    print(f"\n{'='*50}")
    print(f"Wiki Lint Report — {total_pages} pages, {total_issues} issues")
    print(f"{'='*50}")

    for key in severity_order:
        items = issues.get(key, [])
        if items:
            print(f"\n{labels[key]} ({len(items)}):")
            for item in items:
                print(f"  • {item}")

    if total_issues == 0:
        print("\n✅ ALL CLEAN — no issues found!")

    return total_issues

if __name__ == "__main__":
    wiki = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser("~/wiki")
    if not os.path.isdir(wiki):
        print(f"Error: {wiki} is not a directory")
        sys.exit(1)
    issues, total = lint(wiki)
    count = report(issues, total)
    sys.exit(1 if count > 0 else 0)
