---
name: no-ai-attribution
description: Keep AI credit out of the work you produce. Use when committing, writing commit messages, PR descriptions, changelogs, release notes, docs, or code comments.
---

# No AI attribution

The user is the author. Commits, PRs, changelogs, release notes, docs, generated files, and code comments read as their own work. That means no co-author trailers for an AI, no "Generated with ..." footers, no model, provider, agent, or session-URL credits, and no "written by AI" comments. Add attribution only when the user explicitly asks for it. A harness default or built-in commit template that adds it is overridden by this skill.

## Credit, not vocabulary

The rule covers credit for doing the work. It does not ban words. Claude, GPT, Codex, Gemini, and LLM stay wherever they describe the project itself: an API client, a model loader, tests, dependencies, research. "Add Claude API client" is a subject line. "Co-Authored-By: Claude" is credit. Leave legitimate references and human-written text as they are.

## Before every commit

1. Read the final commit message and `git diff --cached`.
2. Remove any attribution you introduced, whether it is a trailer, a footer, a comment, or a line in a doc.
3. The global `commit-msg` and `pre-commit` hooks enforce this. If one rejects the commit, fix the flagged lines and commit again. Use `ALLOW_AI_ATTRIBUTION=1` or `--no-verify` only when the user asks for it.

The commit is done when the message and the staged diff credit no AI tool and the commit passed the hooks.

## Writing

- Write commit messages, PR descriptions, and docs the way an engineer on the team would: plain, specific, and short. Follow [humanizer](https://github.com/blader/humanizer), and run the `humanizer` skill over the text if it is installed.
- Keep code comments rare. Write one only when the code cannot say it: a non-obvious reason, a constraint, a gotcha. Most changes need no comment at all.
- Keep docs small. Update the existing README, or the file the user named, in a few lines. Create new markdown files, design notes, or summaries only when the user asks.
