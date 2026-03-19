from __future__ import annotations

import argparse
import json

from .app import BriefingApp


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Self-growth daily briefing pipeline")
    parser.add_argument("--project-root", default=".", help="Project root containing config/, templates/, and .env")
    subparsers = parser.add_subparsers(dest="command", required=True)

    preview = subparsers.add_parser("preview", help="Generate the daily issue without sending email")
    preview.add_argument("--json", action="store_true", help="Emit the issue as JSON")

    run = subparsers.add_parser("run", help="Generate the daily issue and optionally send it")
    run.add_argument("--send", action="store_true", help="Send the generated issue via SMTP")
    run.add_argument("--json", action="store_true", help="Emit the issue as JSON")

    subparsers.add_parser("send-test", help="Send a simple SMTP connectivity test email")

    install_task = subparsers.add_parser("install-task", help="Install the Windows scheduled task")
    install_task.add_argument("--time", default=None, help="Scheduled time in HH:MM")

    subparsers.add_parser("list-sources", help="List configured sources")
    return parser


def _print_issue(issue, emit_json: bool) -> None:
    if emit_json:
        print(json.dumps(issue.to_dict(), ensure_ascii=False, indent=2))
    else:
        print(issue.article_markdown)


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    app = BriefingApp.from_project_root(args.project_root)

    try:
        if args.command == "preview":
            issue = app.preview()
            _print_issue(issue, emit_json=args.json)
            return 0

        if args.command == "run":
            issue, send_result = app.run(send=args.send)
            _print_issue(issue, emit_json=args.json)
            if send_result:
                status = f"Email status: {send_result.status} ({send_result.attempts} attempt(s))"
                if send_result.error:
                    status = f"{status} - {send_result.error}"
                print(status)
            return 0

        if args.command == "send-test":
            result = app.send_test()
            print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
            return 0

        if args.command == "install-task":
            command = app.install_task(time_text=args.time)
            print("Installed scheduled task with command:")
            print(" ".join(command))
            return 0

        if args.command == "list-sources":
            print(json.dumps(app.list_sources(), ensure_ascii=False, indent=2))
            return 0
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 1

    parser.print_help()
    return 1
