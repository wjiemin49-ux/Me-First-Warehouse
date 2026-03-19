---
name: self-growth-daily-briefing
description: Generate or send a daily self-growth briefing article from this local repository. Use when the user wants to preview today's self-growth article, send it by email, install the daily 09:00 task, or inspect the configured source list.
---

# Self Growth Daily Briefing

Use the local PowerShell wrapper in `scripts/invoke.ps1` so the skill stays thin and all business logic lives in the Python repo.

## Commands

- Preview today's article:
  - `powershell -ExecutionPolicy Bypass -File skill/scripts/invoke.ps1 preview`
- Generate and send:
  - `powershell -ExecutionPolicy Bypass -File skill/scripts/invoke.ps1 run`
- Install the daily task:
  - `powershell -ExecutionPolicy Bypass -File skill/scripts/invoke.ps1 install-task`
- List sources:
  - `powershell -ExecutionPolicy Bypass -File skill/scripts/invoke.ps1 list-sources`

## Notes

- Run from the repository root.
- Read `.env`, `config/settings.yaml`, and `config/feeds.yaml` before using the live flow.
- If SMTP or OpenAI-compatible credentials are missing, explain the missing keys instead of guessing.
