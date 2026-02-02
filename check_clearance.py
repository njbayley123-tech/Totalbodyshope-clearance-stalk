import requests
from bs4 import BeautifulSoup
import json
import os

URL = "https://totalbodyshop.co.nz/collections/garage-sale"
STATE_FILE = "state.json"
NTFY_TOPIC = "totalbodyshop-clearance-92hd"  

def send_notification(title: str, message: str) -> None:
    requests.post(
        f"https://ntfy.sh/{NTFY_TOPIC}",
        data=message.encode("utf-8"),
        headers={"Title": title}
    )

def load_seen() -> list[str]:
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_seen(items: list[str]) -> None:
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(items, f, indent=2)

# Fetch page
r = requests.get(URL, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
r.raise_for_status()

soup = BeautifulSoup(r.text, "html.parser")

# Collect product links
products = sorted({
    a["href"].strip()
    for a in soup.select("a[href*='/products/']")
    if a.get("href")
})

seen = set(load_seen())
current = set(products)

new_items = sorted(current - seen)

# Notify ONLY if new items exist
if new_items:
    msg_lines = [f"{len(new_items)} new item(s) added:"]
    msg_lines += [f"https://totalbodyshop.co.nz{p}" for p in new_items[:15]]
    if len(new_items) > 15:
        msg_lines.append(f"(+ {len(new_items) - 15} more)")

    send_notification("🔥 New Garage Sale Items!", "\n".join(msg_lines))

# Always update state so we don’t re-alert the same items
save_seen(sorted(current))
