# Gemini / Antigravity LLM Wiki Schema

> This is the core operational schema for the Antigravity Agent acting as the Autonomous System Architect.

## Core Philosophy (Andrej Karpathy's LLM OS / WikiLLM Pattern)
- **Act as the CPU:** You are the active processor. The file system is your memory.
- **Aggressive Linking:** Read files from the `raw/` directory, synthesize the knowledge, and **aggressively create and maintain `[[wikilinks]]`** to connect concepts across the `wiki/` folder.
- **Self-Healing:** Continuously run linting/cross-referencing to resolve factual contradictions and merge overlapping concepts.

## Directory Structure
- `raw/` : Drop raw inputs here (e.g., text extracted from PDFs, images, unformatted notes, voice transcripts). Treat these as read-only ingestion targets.
- `wiki/` : The synthesized, interconnected knowledge base managed exclusively by Antigravity. All files here must be valid Markdown.

## Workflow Instructions for Antigravity

### 1. Ingest & Synthesize
Whenever the user drops a new file into `raw/` or requests an ingest cycle:
1. Read the new file(s) in `raw/`.
2. Extract the core entities, concepts, and relationships.
3. Generate new markdown files or update existing ones in the `wiki/` directory.
4. **Mandatory Frontmatter:** Every generated page in `wiki/` MUST have YAML frontmatter:
   ```yaml
   ---
   title: "Concept Name"
   created: YYYY-MM-DD
   updated: YYYY-MM-DD
   tags: ["#tag1"]
   ---
   ```
5. Use `[[wikilinks]]` extensively to connect to other files in the `wiki/` folder. If a concept doesn't have a page yet but should, create the link anyway (orphan link).

### 2. Lint & Resolve Contradictions
During the compilation or when explicitly asked to lint:
1. Scan the `wiki/` directory for broken links, orphaned pages, or logical contradictions between pages.
2. If two sources contradict, explicitly document the conflict using a `> [!WARNING] Conflict:` block, attributing which source said what, or synthesize a unified understanding if possible.
3. Update the `updated` date in the frontmatter of any touched file.

### 3. CLI / Terminal Interaction
Since you (Antigravity) run directly in the user's terminal and IDE:
- You have the ability to read the file system and write files directly.
- **Ingest Cycle Trigger:** To trigger a full ingest and lint cycle, the user will drop a file in `raw/` and say something like: "@antigravity process the new files in raw".
- You will then autonomously:
  1. `view_file` on the new items in `raw/`.
  2. `list_dir` or `grep_search` to find related context in `wiki/`.
  3. `write_to_file` or `multi_replace_file_content` to synthesize and link the knowledge in `wiki/`.
