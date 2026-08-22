---
name: wiki-creation
trigger: User asks to create wiki pages from raw markdown sources, or to build/initialize a wiki from existing files
description: Create entity and concept wiki pages synthesised from raw source files, following SCHEMA.md conventions — frontmatter, wikilinks, provenance, tag taxonomy, bilingual language.
---

# Wiki Creation from Raw Sources

Systematically create wiki entity and concept pages from raw markdown source files, following a SCHEMA.md convention file.

## Workflow

1. **Read SCHEMA.md first** - Understand file naming, frontmatter format, tag taxonomy, page thresholds, and language conventions before creating anything. If the user says "wiki" but the root is not explicit, locate the wiki by finding a nearby `SCHEMA.md` (commonly `~/wiki/SCHEMA.md`) before creating pages.

2. **Identify entities vs concepts** from sources:
   - **Entity**: agents, projects, personas, products (one per notable thing)
   - **Concept**: patterns, pipelines, techniques, architectures (reusable ideas)

3. **Choose the source mode before reading.**
   - **Source-ingest mode:** when the user gives raw files or asks to build from existing materials, read ALL source files BEFORE creating pages. Don't create pages piecemeal. Read all source files in parallel batches so you understand the full context before synthesizing. Use `search_files` to find files, `read_file` to read them.
   - **User-idea note mode:** when the user asks to create a new wiki note from the current message/idea, treat the user's message as the source (`sources: [user:<channel>:<date>]`). Search for related existing pages, then create the note directly; do not invent raw-file provenance or block on non-existent source files.
   - **External-source research mode:** when the user asks to research an external topic (web project, crypto token, API, product) and write the findings to wiki, treat the web URLs you fetch as the sources. List them in `sources:` frontmatter (mix of `user:<channel>:<date>` and full URLs). Use `^[https://url]` provenance markers on paragraphs synthesized from specific pages. Fetch all sources in parallel batches (via `execute_code` + `curl`) before writing the page — same "read everything first" rule as source-ingest mode. For Mintlify-hosted docs, fetch `/llms.txt` first to get a structured index of all doc pages (see [[crypto-project-research]] skill for the full pattern).

4. **For new wiki subdomains, update the schema before/alongside pages.** If the user asks for a new top-level folder/category (e.g. a money-ideas/temki database), add a compact convention section to `SCHEMA.md`, extend the tag taxonomy only with needed class-level tags, and create a folder `index.md` that explains the packaging pattern. Keep the main note as executive context and split deep context into related child files instead of stuffing everything into one page.

   **Temki external-research packs:** when researching an external model/tool/product for `wiki/temki/`, use `references/temki-research-packaging.md`: preserve the user's hypothesis from chat/voice as first-party source context, research authoritative external sources, then split into main + roadmap + money + risks + agent-workflow notes. For high-stakes domains like trading, explicitly distinguish model capability claims from validated money-making edge and add validation gates.

5. **Create entity pages first, then concept pages** - Entities are the anchors; concepts reference them. In user-idea note mode this may be a single concept page; still link it to 2+ existing pages. For themed packs, create the main page first, then child concept pages, then the folder index.

6. **Every page MUST have:**
   - YAML frontmatter with: `title`, `created`, `updated`, `type`, `tags` (from taxonomy), `sources`, `confidence`, `contested`, `contradictions`
   - At least 2 outbound `[[wikilinks]]` to other wiki pages
   - Content synthesized from raw sources (not copied verbatim)
   - Provenance markers `^[path/to/source.md]` at end of paragraphs synthesized from specific sources
   - Language: primary language as specified in SCHEMA.md (often bilingual), English for technical terms

6. **Create index.md** listing all entities and concepts with one-line descriptions.

7. **Append to log.md** with a summary of what was created.

## Pitfalls

- **Over-applying ingest workflow to a single idea** - If the user only asked for a new note from their current thought, don't perform a heavy raw-source ingestion pass. Read SCHEMA, search related pages, create a concise concept/entity page, update `index.md`, and append `log.md`.
- **Missing provenance markers** - SCHEMA.md requires `^[source]` on synthesized paragraphs from 3+ sources. Always add them for multi-source synthesis. For a single user-message idea, use `sources: [user:<channel>:<date>]` and provenance markers are usually unnecessary unless SCHEMA says otherwise. After writing, verify that every `^[path]` marker also appears in the page frontmatter `sources:` list.
- **Invalid pre-existing empty files in new folders** - When creating a new subfolder, scan for existing/accidental `.md` files. Do not leave zero-byte or no-frontmatter notes behind; either remove them safely or convert them into valid index/overview notes and add them to `index.md`/`log.md`.
- **Stale page counts after folder packs** - If `index.md` tracks a total page count, recompute it with the same inclusion rule used by the wiki (usually curated `.md` pages excluding `raw/`, `SCHEMA.md`, root `index.md`, and `log.md`) after all files are written, including any folder index/overview pages.
- **Insufficient wikilinks** - Every page needs minimum 2 outbound links. Cross-reference entities and concepts.
- **Wrong language mix** - Follow SCHEMA.md: typically Russian primary, English for technical terms. Don't translate established technical terms.
- **Creating pages piecemeal** - Read all sources first, then create. Creating pages one-by-one without full context leads to inconsistent wikilinks and missed cross-references.
- **Forgetting index.md** - Every new page must be added to index.md under the correct section (Entity vs Concept).
- **Forgetting log.md** - Every action must be appended to log.md per SCHEMA.md conventions.
- **Tag taxonomy drift** - Only use tags from the SCHEMA.md taxonomy. Don't invent new tags.
- **Over-splitting** - SCHEMA.md says split when exceeding ~200 lines. Keep pages concise. Don't create a page for passing mentions.
- **Over-architecting product concept pages** - If the user explicitly says this is only a software/product concept and not the backend/architecture workspace, create a compact entity that captures product purpose, MVP scope, and key business concepts only. Do not expand into architecture, implementation plans, or backend assumptions.

## Wiki Refactoring and Maintenance

When renaming files or restructuring an existing wiki, follow this sequence to keep everything consistent:

1. **Plan the rename map first.** List every old name → new name before touching files. Verify the naming convention applies to ALL files in scope, not just the ones the user explicitly mentioned.
2. **Rename files on disk.** Use `mv` or bulk rename tools.
3. **Bulk-update wikilinks across the entire wiki.** Use `find` + `perl -pi -e` (or `sed`) to replace `[[old-name]]` with `[[new-name]]` and plain file references (`old-name.md`) in every `.md` file. Example:
   ```bash
   cd ~/wiki && find . -name '*.md' -exec perl -pi -e 's/\[\[old-name\]\]/[[new-name]]/g; s/old-name\.md/new-name.md/g' {} +
   ```
4. **Update frontmatter `updated` dates** on every renamed page.
5. **Refresh tags** for consistency — add role-specific or domain-specific tags if the refactor reveals gaps.
6. **Update index.md** — swap old names for new names in the catalog, bump the "Last updated" date.
7. **Append to log.md** with a clear record of what was renamed and why.
8. **Update agent memory** so future sessions know the new canonical names.

### Refactoring pitfalls

- **Partial rename** — renaming only the files the user explicitly listed while leaving others with the old convention. Always scan the full directory and apply the convention uniformly.
- **Orphaned wikilinks** — renaming files but missing some `[[wikilink]]` or plain-text `.md` references. Use `grep` to verify zero occurrences of the old name remain.
- **Stale index/log** — forgetting to bump `updated` dates in index.md or omitting the refactor entry from log.md.
- **Memory drift** — agent memory still holding old filenames after a rename, causing broken references in future sessions. Always update memory after a bulk rename.

## Portfolio Packaging

When the user asks to package a portfolio (LinkedIn, CV, project showcase), use this sub-pattern on top of the standard wiki workflow.

### File structure

```
wiki/porfolio/   (or wiki/portfolio/ — use whatever the user created)
├── linkedin.md       — optimized LinkedIn profile
├── cv.md             — professional CV
└── project-<name>.md — one file per project
```

### Per-project file template

Every project file follows this structure (see `templates/portfolio-project.md` for a copy-paste starter — use it as the starting point, not a rigid cage):

1. **Frontmatter** — standard YAML (type: entity, tags from taxonomy, sources from raw/)
2. **TL;DR** — 2-3 sentence summary with links (live URL, GitHub, period)
3. **Контекст и мотивация** — what problem, what pains were being solved
4. **Инженерные решения** — numbered list of specific technical decisions, innovations, workarounds (this is the meat — differentiate from marketing fluff)
5. **Результаты** — concrete outcomes, metrics, artifacts
6. **Tech Stack** — table of layers and technologies
7. **Roadmap** — what's done vs planned (checkboxes)

### linkedin.md specifics

- **Headline variants** — provide 2-3 headline options tuned for different job targets
- **About** — expanded professional summary, not a copy of the CV
- **Experience** — restructured entries with project cross-links
- **SEO keywords** — list of searchable terms for LinkedIn algorithm
- **Gap analysis** — what's wrong with the current profile + what to add (Featured, Skills, Recommendations)
- **Post ideas** — 4-6 LinkedIn post concepts, one per major project/case

### cv.md specifics

- Summary (2-3 lines)
- Core competencies table (domain → technologies)
- Experience entries with embedded project descriptions
- Key projects table with links to portfolio files
- Education, languages

### Workflow differences from standard wiki creation

1. **Read ALL raw sources first** — portfolio materials are often scattered (raw/, project READMEs, CV docs, LinkedIn exports). Search broadly with `find` before reading.
2. **Synthesize, don't copy** — raw portfolio materials are often informal (notes, Obsidian dumps, READMEs). Rewrite into professional, presentable language while preserving technical accuracy.
3. **Cross-link aggressively** — each project file should link to existing wiki entity/concept pages (e.g., `[[project-kinodel]]`, `[[agent-producer-kinodel]]`).
4. **Fill gaps from context** — if raw materials mention a project briefly but the wiki already has a rich entity page for it, pull technical details from the entity page to enrich the portfolio entry.
5. **Update index.md and log.md** — add a "Portfolio" section to index.md with all created files.

### Pitfalls

- **Copying raw notes verbatim** — portfolio files must be presentable to employers/clients. Raw notes often contain slang, incomplete sentences, or internal jokes. Rewrite professionally.
- **Missing the "engineered solutions" angle** — employers want to see HOW you solved problems, not just WHAT you built. Always include the "Инженерные решения" section with specific decisions.
- **Forgetting linkedin.md post ideas** — the user often wants to create LinkedIn posts for each case. Include 4-6 post concepts in linkedin.md.
- **Not cross-linking to wiki entities** — portfolio files are richer when they link to the deep technical wiki pages. Always check existing entities/ and concepts/ directories.

## Verification

After creating pages, spot-check:
- All pages have valid YAML frontmatter (closed `---` delimiters)
- All pages have 2+ wikilinks
- No orphaned pages (every concept links to at least one entity, every entity links to at least one concept or entity)
- index.md lists all created pages
- log.md has an entry for the creation

After renaming/refactoring, additionally spot-check:
- Zero grep hits for old filenames or old wikilink names across the wiki
- All renamed pages have bumped `updated` dates
- log.md contains a refactor entry with the full rename map
- Agent memory reflects the new canonical names
