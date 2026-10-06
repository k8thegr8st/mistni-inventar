"""
Místní inventář pro Google Merchant Center – HranaNetu.cz
Stáhne Heureka feed z Upgates a vytvoří mistni-inventar.tsv
pro prodejnu HRANA01.
"""
import os
import urllib.request
import xml.etree.ElementTree as ET

# URL feedu se bere z GitHub secretu FEED_URL, aby nebyla vidět ve veřejném repozitáři
FEED_URL = os.environ["FEED_URL"]
STORE_CODE = "HRANA01"
OUTPUT = "mistni-inventar.tsv"

# Které pole z feedu odpovídá ID produktu v Merchant Center:
#   "ITEM_ID"   -> např. 1651
#   "PRODUCTNO" -> např. P01551
ID_POLE = "ITEM_ID"


def text(item, name):
    el = item.find(name)
    return el.text.strip() if el is not None and el.text else ""


def main():
    req = urllib.request.Request(FEED_URL, headers={"User-Agent": "local-inventory-bot"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        root = ET.fromstring(resp.read())

    rows = []
    seen = set()
    for item in root.iter("SHOPITEM"):
        pid = text(item, ID_POLE)
        if not pid or pid in seen:
            continue
        seen.add(pid)
        in_stock = text(item, "DELIVERY_DATE") == "0"
        rows.append((STORE_CODE, pid, "in_stock" if in_stock else "out_of_stock"))

    if not rows:
        raise SystemExit("Feed neobsahuje žádné produkty – soubor nepřepisuji.")

    rows.sort(key=lambda r: r[1])
    with open(OUTPUT, "w", encoding="utf-8", newline="\n") as f:
        f.write("store_code\tid\tavailability\n")
        for r in rows:
            f.write("\t".join(r) + "\n")

    skladem = sum(1 for r in rows if r[2] == "in_stock")
    print(f"Hotovo: {len(rows)} produktů, z toho skladem {skladem}.")


if __name__ == "__main__":
    main()
