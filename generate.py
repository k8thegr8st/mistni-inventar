"""
HranaNetu.cz – automatické soubory pro Google Merchant Center

1) mistni-inventar.tsv  – místní inventář pro prodejnu HRANA01 (z Heureka feedu)
2) oprava-nazvu.tsv     – doplňkový zdroj s opravenými názvy produktů,
                          kde je výrobce v názvu dvakrát (z Google feedu)
"""
import os
import re
import urllib.request
import xml.etree.ElementTree as ET

# URL feedů se berou z GitHub secretů, aby nebyly vidět ve veřejném repozitáři
FEED_URL = os.environ["FEED_URL"]                    # Heureka feed
GOOGLE_FEED_URL = os.environ.get("GOOGLE_FEED_URL")  # Google Merchant feed

STORE_CODE = "HRANA01"
OUTPUT_INVENTAR = "mistni-inventar.tsv"
OUTPUT_NAZVY = "oprava-nazvu.tsv"

# Které pole z Heureka feedu odpovídá ID produktu v Merchant Center:
#   "ITEM_ID"   -> např. 1651
#   "PRODUCTNO" -> např. P01551
ID_POLE = "ITEM_ID"

G = "{http://base.google.com/ns/1.0}"


def stahnout(url):
    req = urllib.request.Request(url, headers={"User-Agent": "hrana-merchant-bot"})
    with urllib.request.urlopen(req, timeout=180) as resp:
        return ET.fromstring(resp.read())


def text(item, name):
    el = item.find(name)
    return el.text.strip() if el is not None and el.text else ""


def zapsat_tsv(cesta, hlavicka, radky):
    with open(cesta, "w", encoding="utf-8", newline="\n") as f:
        f.write("\t".join(hlavicka) + "\n")
        for r in radky:
            f.write("\t".join(c.replace("\t", " ").replace("\n", " ") for c in r) + "\n")


# ---------- 1) Místní inventář ----------

def mistni_inventar():
    root = stahnout(FEED_URL)
    rows, seen = [], set()
    for item in root.iter("SHOPITEM"):
        pid = text(item, ID_POLE)
        if not pid or pid in seen:
            continue
        seen.add(pid)
        in_stock = text(item, "DELIVERY_DATE") == "0"
        rows.append((STORE_CODE, pid, "in_stock" if in_stock else "out_of_stock"))

    if not rows:
        raise SystemExit("Heureka feed neobsahuje žádné produkty – soubor nepřepisuji.")

    # Produkty z Google feedu, které v Heureka feedu nejsou (vyprodané,
    # předprodej), doplníme jako out_of_stock, aby jim nechyběla místní data.
    if GOOGLE_FEED_URL:
        groot = stahnout(GOOGLE_FEED_URL)
        for item in groot.iter("item"):
            pid = text(item, G + "id")
            if pid and pid not in seen:
                seen.add(pid)
                rows.append((STORE_CODE, pid, "out_of_stock"))

    rows.sort(key=lambda r: r[1])
    zapsat_tsv(OUTPUT_INVENTAR, ["store_code", "id", "availability"], rows)
    skladem = sum(1 for r in rows if r[2] == "in_stock")
    print(f"Inventář: {len(rows)} produktů, z toho skladem {skladem}.")


# ---------- 2) Oprava zdvojených názvů ----------

def opravit_nazev(title, brand):
    """
    Pokud název začíná výrobcem a ten se v názvu objevuje znovu,
    první (přidaný) výskyt odstraní:
      'Ultra PRO Ultra PRO Eclipse…'          -> 'Ultra PRO Eclipse…'
      'Curator Orange Nebula Curator Palette…' -> 'Orange Nebula Curator Palette…'
    Názvy, kde výrobce je jen jednou, nechá beze změny.
    """
    t = re.sub(r"\s+", " ", title).strip()
    b = re.sub(r"\s+", " ", brand).strip()
    if not b:
        return t
    prefix = b + " "
    if t.lower().startswith(prefix.lower()):
        zbytek = t[len(prefix):].strip()
        if b.lower() in zbytek.lower():
            return zbytek
    return t


def oprava_nazvu():
    if not GOOGLE_FEED_URL:
        print("GOOGLE_FEED_URL není nastavený – opravu názvů přeskakuji.")
        return

    root = stahnout(GOOGLE_FEED_URL)
    rows, seen = [], set()
    for item in root.iter("item"):
        pid = text(item, G + "id")
        title = text(item, G + "title") or text(item, "title")
        brand = text(item, G + "brand")
        if not pid or pid in seen or not title:
            continue
        seen.add(pid)
        novy = opravit_nazev(title, brand)
        if novy != re.sub(r"\s+", " ", title).strip():
            rows.append((pid, novy))

    rows.sort(key=lambda r: r[0])
    # soubor zapisujeme vždy (i prázdný), aby opravené produkty ze zdroje vypadly
    zapsat_tsv(OUTPUT_NAZVY, ["id", "title"], rows)
    print(f"Oprava názvů: {len(seen)} produktů prověřeno, {len(rows)} názvů opraveno.")


if __name__ == "__main__":
    mistni_inventar()
    oprava_nazvu()
