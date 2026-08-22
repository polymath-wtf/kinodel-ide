# Bulk Ingest from Local Directory Tree

Pattern for importing 20+ local markdown/text files from an existing project directory
into an llm-wiki knowledge base.

## Workflow

### 1. Analyze source tree first

```bash
# Find all text files, exclude .git and node_modules
find ~/source_dir -type f \( -name "*.md" -o -name "*.txt" \) -not -path '*/.git/*' | sort
```

Read a sample of files to understand content quality. Many project directories contain
empty files, configs, and docs of varying relevance.

### 2. Copy raw sources preserving structure

```bash
mkdir -p ~/wiki/raw && cp -r ~/source_dir/* ~/wiki/raw/
```

Copy everything to `raw/` preserving directory structure. These are Layer 1 immutable sources.
No frontmatter needed on bulk copy — the wiki pages cite the paths.

### 3. Delegate page creation to subagent

For 20+ sources, use `delegate_task` with a long-running goal. The subagent has its own
session, can read files independently, and create pages without burning your token budget.

Key prompt elements for the delegate:
- Read SCHEMA.md first for conventions and tag taxonomy
- Read ALL source files (check for empty content — skip those)
- Create entity pages for agents/projects/personas
- Create concept pages for patterns/technologies/architectures
- Every page needs: frontmatter, 2+ wikilinks, Russian primary/English technical terms (adapt to schema)
- Update index.md and log.md when done

### 4. Verify and fill gaps

After the subagent completes:
- `ls wiki/entities/*.md wiki/concepts/*.md wiki/comparisons/*.md wiki/queries/*.md` — count pages
- `cat wiki/log.md` — check if log was created (subagent often misses this)
- `cat wiki/index.md` — verify all sections are populated
- Create missing comparison/queries pages yourself
- Add a bulk-ingest entry to log.md

### Pitfalls

- `read_file()` on empty files returns empty content — check before processing
- Subagents often forget to create log.md — always verify after completion
- If the source tree has many empty files, filter them: `find ... -size +0`
- The Bulk Ingest section in the main skill mentions batching updates to index.md/log.md —
  ensure the subagent does this (write index once, not after every page).
