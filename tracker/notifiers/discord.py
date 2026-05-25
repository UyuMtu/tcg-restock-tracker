"""
Discord notifier via webhooks.
No bot account or permissions needed — just a webhook URL from your server.

How to get a webhook URL:
1. Open your Discord server
2. Right-click a channel → Edit Channel → Integrations → Webhooks
3. Create a new webhook and copy the URL
4. Add it as DISCORD_WEBHOOK_URL in GitHub Secrets
"""

import requests


def send_discord_alert(webhook_url: str, message: str, embed: dict | None = None):
    """
    Send a notification to a Discord channel.
    If embed is provided, sends a rich embed card (looks much nicer).
    """
    payload: dict = {"username": "TCG Restock Bot"}

    if embed:
        # Rich embed format — shows as a coloured card in Discord
        payload["embeds"] = [
            {
                "title": embed.get("title", ""),
                "description": embed.get("description", ""),
                "color": embed.get("color", 0x7289DA),
                "fields": embed.get("fields", []),
                "url": embed.get("url", ""),
                "footer": {"text": "TCG Tracker • Check every 30 min"},
            }
        ]
    else:
        payload["content"] = message

    try:
        resp = requests.post(webhook_url, json=payload, timeout=10)
        resp.raise_for_status()
    except requests.exceptions.HTTPError as e:
        print(f"  ⚠️  Discord alert failed (HTTP {e.response.status_code}): {e.response.text[:200]}")
    except Exception as e:
        print(f"  ⚠️  Discord alert failed: {e}")
