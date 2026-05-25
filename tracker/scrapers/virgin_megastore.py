"""
Virgin Megastore scraper — works for all three regional domains:
  virginmegastore.ae / virginmegastore.om / virginmegastore.qa

Their sites run on a common Magento-based platform, so the
scraping logic is the same across all three regions.
"""

import json
import re
import time
import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
}


def _extract_price(soup: BeautifulSoup) -> float | None:
    """Try multiple CSS patterns to find a price on the page."""
    # Priority order: specific → general
    selectors = [
        {"class": re.compile(r"special.?price", re.I)},
        {"class": re.compile(r"product.?price", re.I)},
        {"class": re.compile(r"price.?final", re.I)},
        {"class": re.compile(r"^price$", re.I)},
    ]
    for attrs in selectors:
        el = soup.find(["span", "p", "div"], attrs)
        if el:
            text = el.get_text(" ", strip=True)
            # Match numbers like 249, 249.00, 1,249.00
            match = re.search(r"[\d,]+\.?\d*", text)
            if match:
                try:
                    return float(match.group().replace(",", ""))
                except ValueError:
                    continue
    return None


def check_virgin_megastore(url: str, name: str) -> dict:
    """
    Returns:
        {
            "name": str,
            "in_stock": bool,
            "price": float | None,
            "url": str,
            "error": str | None
        }
    """
    try:
        time.sleep(1)
        resp = requests.get(url, headers=HEADERS, timeout=20)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        # ── Method 1: JSON-LD structured data ────────────────────
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string or "")
                if isinstance(data, list):
                    data = data[0]
                offers = data.get("offers", {})
                if isinstance(offers, list):
                    offers = offers[0]
                availability = offers.get("availability", "")
                price = offers.get("price")
                if availability:
                    in_stock = "InStock" in availability
                    return {
                        "name": name,
                        "in_stock": in_stock,
                        "price": float(price) if price else None,
                        "url": url,
                    }
            except (json.JSONDecodeError, KeyError, TypeError, ValueError):
                continue

        # ── Method 2: Magento-specific page signals ───────────────
        page_text = soup.get_text(" ", strip=True).lower()

        oos_signals = [
            "out of stock",
            "sold out",
            "currently unavailable",
            "not available",
        ]
        is_oos = any(s in page_text for s in oos_signals)

        # Magento "Add to Cart" button has a specific form action
        add_btn = (
            soup.find("button", {"id": "product-addtocart-button"})
            or soup.find("button", {"class": re.compile(r"tocart", re.I)})
            or soup.find("button", string=re.compile(r"add to (cart|bag)", re.I))
        )

        in_stock = (add_btn is not None) and not is_oos

        price = _extract_price(soup)

        return {"name": name, "in_stock": in_stock, "price": price, "url": url}

    except requests.exceptions.HTTPError as e:
        return {"name": name, "in_stock": False, "price": None, "url": url, "error": f"HTTP {e.response.status_code}"}
    except requests.exceptions.Timeout:
        return {"name": name, "in_stock": False, "price": None, "url": url, "error": "Timeout"}
    except Exception as e:
        return {"name": name, "in_stock": False, "price": None, "url": url, "error": str(e)}
