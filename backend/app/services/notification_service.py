"""Email and Slack notifications for expert knowledge submissions."""

from __future__ import annotations

import asyncio
import smtplib
from email.message import EmailMessage
from typing import Any

import httpx
import structlog

from app.config import get_settings

logger = structlog.get_logger()


async def notify_expert_knowledge_submitted(
    repo: dict[str, Any],
    knowledge: dict[str, Any],
) -> None:
    """Fire-and-forget notifications when an expert contributes tribal knowledge."""
    settings = get_settings()
    subject = f"[Code Archaeologist] Expert knowledge: {repo['owner']}/{repo['name']}"
    body = (
        f"Repository: {repo['owner']}/{repo['name']}\n"
        f"Dataset: {repo['dataset_name']}\n"
        f"Author: {knowledge['author_name']}\n"
        f"Topic: {knowledge['topic']}\n"
        f"Related file: {knowledge.get('related_file') or '—'}\n"
        f"Related symbol: {knowledge.get('related_symbol') or '—'}\n"
        f"Cognee stored: {bool(knowledge.get('cognee_stored'))}\n\n"
        f"{knowledge['content'][:2000]}"
    )

    tasks = []
    if settings.slack_webhook_url:
        tasks.append(_send_slack(settings.slack_webhook_url, subject, body, repo, knowledge))
    if settings.notify_email_to and settings.smtp_host:
        tasks.append(
            _send_email(
                settings.smtp_host,
                settings.smtp_port,
                settings.smtp_user,
                settings.smtp_password,
                settings.notify_email_from or settings.smtp_user,
                settings.notify_email_to,
                subject,
                body,
            )
        )

    if not tasks:
        logger.info("expert_notification_skipped", reason="no SLACK_WEBHOOK_URL or SMTP configured")
        return

    results = await asyncio.gather(*tasks, return_exceptions=True)
    for result in results:
        if isinstance(result, Exception):
            logger.warning("expert_notification_failed", error=str(result))


async def _send_slack(
    webhook_url: str,
    subject: str,
    body: str,
    repo: dict[str, Any],
    knowledge: dict[str, Any],
) -> None:
    payload = {
        "text": subject,
        "blocks": [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": "🧠 Expert knowledge submitted"},
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Repo:*\n`{repo['owner']}/{repo['name']}`"},
                    {"type": "mrkdwn", "text": f"*Author:*\n{knowledge['author_name']}"},
                    {"type": "mrkdwn", "text": f"*Topic:*\n{knowledge['topic']}"},
                    {
                        "type": "mrkdwn",
                        "text": f"*Cognee:*\n{'✅ stored' if knowledge.get('cognee_stored') else '⏳ pending'}",
                    },
                ],
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": knowledge["content"][:1500],
                },
            },
        ],
    }
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(webhook_url, json=payload)
        resp.raise_for_status()


async def _send_email(
    host: str,
    port: int,
    user: str,
    password: str,
    from_addr: str,
    to_addr: str,
    subject: str,
    body: str,
) -> None:
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = to_addr
    msg.set_content(body)

    def _send() -> None:
        with smtplib.SMTP(host, port, timeout=20) as smtp:
            if user and password:
                smtp.starttls()
                smtp.login(user, password)
            smtp.send_message(msg)

    await asyncio.to_thread(_send)
