# agent-skills

A curated collection of **skills** for AI agents and agentic workflows. Skills are packaged, reusable instruction sets (with scripts, references, and assets) that give agents specialized capabilities for day-to-day productivity.

## What is a skill?

A `.skill` file is a **ZIP archive** containing everything an agent needs to perform a specific task:

- `SKILL.md` — Instructions and metadata (name, description, usage)
- `scripts/` — Executable code (Python, Bash, etc.)
- `references/` — Supporting documentation and specs
- `assets/` — Fonts, templates, and other resources
- `examples/` — Sample inputs and usage patterns

Skills are designed to be loaded by AI coding agents (Claude, Cursor, OpenCode, etc.) to extend their capabilities with domain-specific workflows.

## Available skills

| Skill | Description |
|-------|-------------|
| [md2pdf-creator](skills/md2pdf-creator.skill) | Turn Markdown into polished, branded PDFs and EPUBs with dark cover pages, part dividers, running footers, and refined typography (Bricolage Grotesque + IBM Plex). |

## Examples

See what these skills can produce:

| Example | Produced by |
|---------|-------------|
| [Flat to Mountain — Third Edition.pdf](examples/Flat%20to%20Mountain%20%E2%80%94%20Third%20Edition.pdf) | md2pdf-creator |

## How to use

1. Download a `.skill` file from the `skills/` directory
2. Place it in your agent's skills directory (e.g., `~/.claude/skills/` for Claude Code, or your project's `.opencode/skills/`)
3. The agent will automatically detect and use it when relevant

## Contributing

Want to add a skill? Open a PR with your `.skill` file in the `skills/` directory and update the table above.

## License

MIT
