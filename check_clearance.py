import requests
from bs4 import BeautifulSoup
import json
import os
from datetime import datetime

URL = "https://totalbodyshop.co.nz/collections/garage-sale"
STATE_FILE = "state.json"
NTFY_TOPIC = "totalbodyshop-clearance-92hd"  

HEADERS = {"User-Agent": "Mozilla/5.0"}

def send_notification(title: str, message: str) -> None:
    # Title must be latin-1 safe (no emojis)
    requests.post(
        f"https://ntfy.sh/{NTFY_TOPIC}",
        data=message.encode("utf-8"),
        headers={"Title": title}
    )

def load_state() -> dict:
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {"seen": {}}
    return {"seen": {}}

def save_state(state: dict) -> None:
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)

def clean_text(s: str) -> str:
    return " ".join((s or "").split()).strip()

def money_text(node) -> str:
    # Pull any reasonable-looking price text from a node
    if not node:
        return ""
    txt = clean_text(node.get_text(" ", strip=True))
    # common Shopify patterns include "$xx.xx" / "NZ$xx.xx"
    return txt

# Fetch page
r = requests.get(URL, timeout=30, headers=HEADERS)
r.raise_for_status()
soup = BeautifulSoup(r.text, "html.parser")

# --- Extract products (best-effort for Shopify themes) ---
products = {}

# Shopify collections usually link products via /products/...
for a in soup.select("a[href*='/products/']"):
    href = a.get("href")
    if not href or "/products/" not in href:
        continue

    link = href.split("?")[0].strip()

    # Try to find the "card" container around this link to get title + price
    card = a
    for _ in range(6):
        if card is None:
            break
        # many themes have product-card / card / grid item wrappers
        classes = " ".join(card.get("class", [])) if hasattr(card, "get") else ""
        if any(k in classes.lower() for k in ["product", "card", "grid", "collection"]):
            break
        card = card.parent

    # Title: prefer the anchor text; fallback to nearby headings
    title = clean_text(a.get_text(" ", strip=True))
    if not title and card:
        h = card.select_one("h3, h2, .product-card__title, .card__heading, .product-title")
        if h:
            title = clean_text(h.get_text(" ", strip=True))

    # Price: look for common price selectors, fallback to any $ text in card
    price = ""
    if card:
        pnode = card.select_one(
            ".price, .price__regular, .price-item, .product-price, .money, [class*='price']"
        )
        price = money_text(pnode)

        if not price:
            # brute fallback: find first text containing '$' within the card
            card_text = clean_text(card.get_text(" ", strip=True))
            # simple extraction: keep a slice around first '$'
            if "$" in card_text:
                idx = card_text.find("$")
                price = card_text[idx: idx + 20].split(" ")[0:2]
                price = " ".join(price).strip()

    # If still no title, skip (reduces junk)
    if not title:
        continue

    products[link] = {
        "title": title,
        "price": price or "Price not found"
    }

# --- Compare to previous state ---
state = load_state()
seen = state.get("seen", {})  # dict of link -> {title, price}

current_links = set(products.keys())
seen_links = set(seen.keys())

new_links = sorted(current_links - seen_links)

# Notify only if new items exist
if new_links:
    lines = []
    lines.append(f" {len(new_links)} new Garage Sale item(s) added:")
    lines.append("")

    for link in new_links[:15]:
        item = products[link]
        title = item["title"]
        price = item["price"]
        lines.append(f"- {title} — {price}")
        lines.append(f"  https://totalbodyshop.co.nz{link}")
        lines.append("")

    if len(new_links) > 15:
        lines.append(f"(+ {len(new_links) - 15} more not shown)")

    lines.append(f"Checked: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    send_notification("New Garage Sale Items", "\n".join(lines))

# Always update state (so we never re-alert the same items)
state["seen"] = products
save_state(state)
