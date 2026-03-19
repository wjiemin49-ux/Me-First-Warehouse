# Sleep Time Recorder

Desktop application for tracking sleep sessions, viewing history, and analyzing trends.

## Tech Stack
- Python 3.x
- PySide6
- SQLite
- Matplotlib

## Quick Start
```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python scripts/init_db.py
python main.py
```

## Build EXE
```powershell
.\scripts\build_exe.ps1 -Mode OneFolder
```

See full guide: `docs/STEP10_REVIEW_AND_PACKAGING.md`

## Project Structure
```text
sleep-time-recorder/
  main.py
  pyproject.toml
  requirements.txt
  config/
  scripts/
  src/sleep_tracker/
  tests/
```

## Development Roadmap
This project is developed in 10 steps. Current step: Step 10 (final review + packaging guide + roadmap).
