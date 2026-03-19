# Self-Growth Daily Briefing

`self-growth-daily-briefing` is a local-first Python project that collects English self-growth signals, ranks one core topic, writes a warm Chinese growth article, and emails it to you every morning.

## What It Does

- Pulls content from curated RSS sources, Google News RSS queries, and Reddit trend sources
- Filters and clusters recent items around self-growth themes
- Uses an OpenAI-compatible chat API to choose one theme and write one article
- Renders both HTML and plain-text email output
- Sends via SMTP and records run state in SQLite
- Installs a Windows Task Scheduler job for daily 09:00 delivery in `Asia/Shanghai`

## Quick Start

1. Create a `.env` from `.env.example` and fill in your SMTP and OpenAI-compatible credentials.
2. Review `config/settings.yaml` and `config/feeds.yaml`.
3. Run a preview:

```powershell
python -m self_growth_daily_briefing preview --project-root .
```

4. Send the briefing:

```powershell
python -m self_growth_daily_briefing run --send --project-root .
```

5. Install the daily scheduled task:

```powershell
python -m self_growth_daily_briefing install-task --time 09:00 --project-root .
```

## CLI

- `python -m self_growth_daily_briefing preview`
- `python -m self_growth_daily_briefing run --send`
- `python -m self_growth_daily_briefing send-test`
- `python -m self_growth_daily_briefing install-task --time 09:00`
- `python -m self_growth_daily_briefing list-sources`

Pass `--project-root <path>` if you invoke the package outside the repo root.
