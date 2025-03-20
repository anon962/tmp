# pip install bs4 tqdm niquests

import re
from dataclasses import dataclass
from pathlib import Path

import bs4
import niquests
from tqdm import tqdm

TEXT_FILE = Path("./page_text")
HTML_FILE = Path("./page.html")
DEFAULT_USER = "HVEquipRental"


@dataclass
class EquipLine:
    eid: int
    key: str
    name: str
    level: int
    holder: str


def main():
    # Read each rental line
    lines: list[EquipLine] = []
    for ln in TEXT_FILE.read_text().splitlines():
        after_parse = parse_line(ln)
        if after_parse is None:
            continue

        lines.append(after_parse)

    # Extract equip key
    soup = bs4.BeautifulSoup(HTML_FILE.read_text())
    assign_equip_keys(lines, soup)

    # Check that level, holder, etc is correct
    for ln in tqdm(lines):
        res, err = validate(ln)
        if err:
            print(f"=== {err} ===")
            print(ln)
            print(res)
            print()


def parse_line(line: str) -> EquipLine | None:
    """
    Convert
        [294881719]Exquisite Power Armor of Protection、Level:290、Status:Free、Expiry Date:None、Deposit:5000、Holder:

    to
        EquipLine(
            eid=294881719,
            key="",
            name="Exquisite Power Armor of Protection",
            level=290,
            holder="",
        )

    Any lines that don't match are returned as None (eg "Power - 2/2")
    """

    is_equip_line = "Holder:" in line
    if not is_equip_line:
        return None

    m = re.search(r"\[(\d+)\](.+)、Level:(\d+)、.+Holder:(.*)", line)
    if not m:
        raise Exception(f"Failed to extract {line}")

    eid, name, level, holder = m.groups()

    eid = int(eid)
    level = int(level)
    holder = holder.strip() or DEFAULT_USER

    return EquipLine(eid=eid, name=name, level=level, holder=holder, key="")


def assign_equip_keys(lines: list[EquipLine], soup: bs4.BeautifulSoup):
    eid_to_key_map: dict[int, str] = dict()
    for linkEl in soup.select("a"):
        # https://hentaiverse.org/equip/295031184/301fae368b

        if "href" not in linkEl.attrs:
            continue
        href = linkEl.attrs["href"]

        m = re.search(
            r"hentaiverse.org/equip/(\d+)/([a-z0-9]+)",
            href,
            re.IGNORECASE,
        )
        if not m:
            continue

        eid, key = m.groups()
        eid = int(eid)

        eid_to_key_map[eid] = key

    for ln in lines:
        ln.key = eid_to_key_map[ln.eid]


def validate(line: EquipLine) -> tuple[dict, str | None]:
    url = f"https://hvdata.gisadan.dev/equip?eid={line.eid}&key={line.key}&is_isekai=false"
    resp = niquests.get(url)
    data = resp.json()
    # {
    #     "name": "Legendary Zircon Leather Breastplate Of Deflection",
    #     "alt_name": None,
    #     "category": "Light Armor",
    #     "level": 286,
    #     "is_tradeable": True,
    #     "weapon_damage": None,
    #     "stats": { ... },
    #     "upgrades": {"Holy Mitigation": 20},
    #     "enchants": {},
    #     "owner": {"name": "HVEquipRental", "uid": 7912010},
    #     "condition": {"current": 994, "max": 999},
    #     "potency": {"tier": 0, "current_xp": 297, "max_xp": 373}
    # }

    if line.name != data["name"]:
        return data, f"Invalid name"

    if line.holder != data["owner"]["name"]:
        return data, f"Invalid holder"

    if line.level != data["level"]:
        return data, f"Invalid level"

    return data, None


main()

EquipLine(
    eid=289480297,
    key="75d0a6c588",
    name="Legendary Zircon Leather Breastplate of Deflection",
    level=286,
    holder="HVEquipRental",
)
