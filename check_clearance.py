import requests
from bs4 import BeautifulSoup
import json
import os

URL = "https://totalbodyshop.co.nz/collections/garage-sale"
STATE_FILE = "state.json"
NTFY_TOPIC = "totalbodyshop-clearance-92hd"

def send_notification(title, message):
    requests.post(
        f"https://ntfy.sh/{NTFY_TOPIC}",
        data=message.encode("utf-8"),
        headers={"Title": title}
    )

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return []

def save_state(products):
    with open(STATE_FILE, "w") as f:
        json.dump(products, f)

html = requests.get(URL, timeout=30).text
soup = BeautifulSoup(html, "html.parser")

products = sorted(
    a["href"]
    for a in soup.select("a[href*='/products/']")
)

previous = load_state()

if not products and previous:
    send_notification(
        "⚠️ Garage Sale Empty",
        "Total Body Shop garage sale is now SOLD OUT."
    )

new_items = [p for p in products if p not in previous]

if new_items:
    send_notification(
        "🔥 New Garage Sale Items!",
        f"{len(new_items)} new item(s) added:\n" +
        "\n".join(f"https://totalbodyshop.co.nz{p}" for p in new_items)
    )

save_state(products)
