#!/usr/bin/env python3
"""Send scheduled update results to Feishu and/or email.

All credentials are read from environment variables so that GitHub Actions can
inject them through repository secrets without storing secrets in the project.
"""

from __future__ import annotations

import argparse
import json
import os
import smtplib
import ssl
import urllib.request
from email.message import EmailMessage
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[1]
STATUS_FILE = PROJECT_DIR / "metadata" / "update_status.json"


def load_status() -> dict:
    if not STATUS_FILE.exists():
        return {"status": "failed", "message": "update_status.json was not generated"}
    return json.loads(STATUS_FILE.read_text(encoding="utf-8"))


def render_message(status: dict, repository: str = "", run_url: str = "") -> tuple[str, str]:
    state = status.get("status", "unknown")
    summary = status.get("data_summary") or {}
    title = f"EconAtlas 云端数据更新：{state.upper()}"
    lines = [
        title,
        f"开始时间：{status.get('started_at') or '-'}",
        f"结束时间：{status.get('finished_at') or '-'}",
        f"运行耗时：{status.get('duration_seconds') if status.get('duration_seconds') is not None else '-'} 秒",
        f"数据规模：{summary.get('row_count', '-')} 条 / {summary.get('indicator_count', '-')} 项指标 / {summary.get('country_count', '-')} 个国家（地区）",
        f"运行结果：{status.get('message') or '-'}",
    ]
    if repository:
        lines.append(f"代码仓库：{repository}")
    if run_url:
        lines.append(f"运行详情：{run_url}")
    return title, "\n".join(lines)


def send_feishu(webhook_url: str, title: str, body: str) -> None:
    payload = json.dumps(
        {"msg_type": "text", "content": {"text": body}}, ensure_ascii=False
    ).encode("utf-8")
    request = urllib.request.Request(
        webhook_url,
        data=payload,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        response_body = json.loads(response.read().decode("utf-8"))
    if response_body.get("code", response_body.get("StatusCode", 0)) != 0:
        raise RuntimeError(f"Feishu webhook rejected the notification: {response_body}")


def send_email(title: str, body: str) -> None:
    host = os.environ.get("SMTP_HOST", "").strip()
    sender = os.environ.get("SMTP_FROM", "").strip()
    recipients = [item.strip() for item in os.environ.get("SMTP_TO", "").split(",") if item.strip()]
    if not host or not sender or not recipients:
        raise ValueError("SMTP_HOST, SMTP_FROM and SMTP_TO are required for email notifications")

    port = int(os.environ.get("SMTP_PORT", "").strip() or "465")
    username = os.environ.get("SMTP_USERNAME", "").strip()
    password = os.environ.get("SMTP_PASSWORD", "")
    use_ssl = os.environ.get("SMTP_USE_SSL", "true").lower() not in {"0", "false", "no"}

    message = EmailMessage()
    message["Subject"] = title
    message["From"] = sender
    message["To"] = ", ".join(recipients)
    message.set_content(body)

    if use_ssl:
        with smtplib.SMTP_SSL(host, port, context=ssl.create_default_context(), timeout=30) as server:
            if username:
                server.login(username, password)
            server.send_message(message)
    else:
        with smtplib.SMTP(host, port, timeout=30) as server:
            server.starttls(context=ssl.create_default_context())
            if username:
                server.login(username, password)
            server.send_message(message)


def main() -> int:
    parser = argparse.ArgumentParser(description="Notify update result through configured channels")
    parser.add_argument("--dry-run", action="store_true", help="Print the notification without sending it")
    args = parser.parse_args()

    status = load_status()
    repository = os.environ.get("GITHUB_REPOSITORY", "")
    server_url = os.environ.get("GITHUB_SERVER_URL", "https://github.com")
    run_id = os.environ.get("GITHUB_RUN_ID", "")
    run_url = f"{server_url}/{repository}/actions/runs/{run_id}" if repository and run_id else ""
    title, body = render_message(status, repository, run_url)

    if args.dry_run:
        print(body)
        return 0

    configured = 0
    failures = []
    webhook = os.environ.get("FEISHU_WEBHOOK_URL", "").strip()
    if webhook:
        configured += 1
        try:
            send_feishu(webhook, title, body)
            print("[Notify] Feishu notification sent")
        except Exception as exc:  # notification failure must not hide pipeline result
            failures.append(f"Feishu: {exc}")

    if os.environ.get("SMTP_HOST", "").strip():
        configured += 1
        try:
            send_email(title, body)
            print("[Notify] Email notification sent")
        except Exception as exc:
            failures.append(f"Email: {exc}")

    if configured == 0:
        print("[Notify] No notification channel configured; skipped")
    if failures:
        print("[Notify] " + " | ".join(failures))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
