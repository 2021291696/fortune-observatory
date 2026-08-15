"""Regenerate apps/observatory/src/birthPlaces.ts from the GeoNames CN dump.

Covers PPLC (capital) + PPLA (province capitals) + PPLA2 (prefecture cities)
+ PPLA3 (counties / districts), grouped by province for optgroup rendering.

Inputs (download once into .deploy-stage/geonames/):
    CN.zip                https://download.geonames.org/export/dump/CN.zip
    admin1CodesASCII.txt  https://download.geonames.org/export/dump/admin1CodesASCII.txt

Run from the project root:
    .venv/Scripts/python.exe scripts/build_birth_places.py
"""

from __future__ import annotations

import hashlib
import json
import zipfile
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GEO = ROOT / ".deploy-stage" / "geonames"
OUT = ROOT / "apps" / "observatory" / "src" / "birthPlaces.ts"

FEATURE_CODES = {"PPLC": 0, "PPLA": 1, "PPLA2": 2, "PPLA3": 3}
CST = timezone(timedelta(hours=8))

# GeoNames ADM1 alternate names mix traditional/Japanese glyph variants
# (甘粛, 貴州, 黑龍江); pin the simplified-Chinese province names explicitly.
STANDARD_PROVINCES = {
    "01": "安徽", "02": "浙江", "03": "江西", "04": "江苏", "05": "吉林",
    "06": "青海", "07": "福建", "08": "黑龙江", "09": "河南", "10": "河北",
    "11": "湖南", "12": "湖北", "13": "新疆", "14": "西藏", "15": "甘肃",
    "16": "广西", "18": "贵州", "19": "辽宁", "20": "内蒙古", "21": "宁夏",
    "22": "北京", "23": "上海", "24": "山西", "25": "山东", "26": "陕西",
    "28": "天津", "29": "云南", "30": "广东", "31": "海南", "32": "四川",
    "33": "重庆",
}
# Xinjiang localities are tagged Asia/Urumqi in GeoNames, yet birth records
# in China are issued on Beijing time; accept both tags for the same profile.
ACCEPTED_TIMEZONES = {"Asia/Shanghai", "Asia/Urumqi"}


def _cjk(ch: str) -> bool:
    return "\u4e00" <= ch <= "\u9fff"


def _display_name(name: str, alternates: str) -> str:
    """Pick the first clean Chinese variant from the GeoNames alternatenames."""
    for candidate in alternates.split(","):
        candidate = candidate.strip()
        if 2 <= len(candidate) <= 10 and all(_cjk(ch) for ch in candidate):
            return candidate
    return name


def main() -> None:
    zip_path = GEO / "CN.zip"
    with zipfile.ZipFile(zip_path) as bundle:
        with bundle.open("CN.txt") as raw:
            rows = raw.read().decode("utf-8").splitlines()

    # Admin names (province = ADM1, prefecture = ADM2) share the same
    # alternatenames column, so Chinese display names come from one source.
    admin1_names: dict[str, str] = {}
    admin2_names: dict[str, str] = {}
    populated: list[list[str]] = []
    for line in rows:
        parts = line.split("\t")
        if len(parts) < 18 or parts[8] != "CN":
            continue
        if parts[6] == "A" and parts[7] == "ADM1":
            admin1_names[parts[10]] = STANDARD_PROVINCES.get(parts[10], _display_name(parts[1], parts[3]))
        elif parts[6] == "A" and parts[7] == "ADM2":
            admin2_names[f"{parts[10]}.{parts[11]}"] = _display_name(parts[1], parts[3])
        elif parts[6] == "P" and parts[7] in FEATURE_CODES and parts[17] in ACCEPTED_TIMEZONES:
            populated.append(parts)

    seen: set[tuple[str, str]] = set()
    name_counts: dict[tuple[str, str], int] = {}
    entries: list[dict] = []
    for parts in populated:
        province = admin1_names.get(parts[10])
        if province is None:
            continue
        name = _display_name(parts[1], parts[3])
        key = (province, name)
        name_counts[key] = name_counts.get(key, 0) + 1
        slug = "".join(ch for ch in parts[2].lower() if ch.isalnum() or ch == "-")
        entries.append({
            "id": slug,
            "name": name,
            "province": province,
            "prefecture": admin2_names.get(f"{parts[10]}.{parts[11]}", ""),
            "lat": round(float(parts[4]), 4),
            "lon": round(float(parts[5]), 4),
            "geonameId": int(parts[0]),
            "rank": FEATURE_CODES[parts[7]],
        })
        seen.add(key)

    for entry in entries:
        # Counties with the same name inside one province get a prefecture hint.
        if name_counts[(entry["province"], entry["name"])] > 1 and entry["prefecture"]:
            entry["name"] = f"{entry['name']}（{entry['prefecture']}）"

    by_id: set[str] = set()
    for entry in entries:
        if not entry["id"] or entry["id"] in by_id:
            entry["id"] = f"{entry['id']}-{entry['geonameId']}"
        by_id.add(entry["id"])

    provinces: dict[str, list[dict]] = defaultdict(list)
    for entry in entries:
        provinces[entry["province"]].append(entry)
    for members in provinces.values():
        members.sort(key=lambda item: (item["rank"], item["id"]))
    ordered_provinces = sorted(provinces, key=lambda name: (len(name), name))

    compact = [
        [entry["id"], entry["name"], entry["province"], entry["lat"], entry["lon"], entry["geonameId"]]
        for province in ordered_provinces
        for entry in provinces[province]
    ]

    sha256 = hashlib.sha256(zip_path.read_bytes()).hexdigest()
    stamp = datetime.now(CST).isoformat(timespec="seconds")
    payload = json.dumps(compact, ensure_ascii=False, separators=(",", ":"))

    OUT.write_text(
        "/* eslint-disable */\n"
        "// Generated by scripts/build_birth_places.py — do not edit by hand.\n"
        f"// Source: GeoNames CN.zip (CC BY 4.0), snapshot sha256 {sha256[:16]}…, built {stamp}.\n"
        f"// {len(compact)} places: PPLC+PPLA+PPLA2+PPLA3 (capital, province capitals, prefecture cities, counties/districts).\n\n"
        "export type BirthPlace = {\n"
        "  id: string\n"
        "  name: string\n"
        "  province: string\n"
        "  latitude: number\n"
        "  longitude: number\n"
        "  geonameId: number\n"
        "}\n\n"
        "export const birthPlaceSource = {\n"
        "  name: 'GeoNames CN.zip',\n"
        "  url: 'https://download.geonames.org/export/dump/CN.zip',\n"
        "  licenseUrl: 'https://download.geonames.org/export/dump/readme.txt',\n"
        "  license: 'CC BY 4.0',\n"
        f"  snapshotAt: '{stamp}',\n"
        f"  bytes: {zip_path.stat().st_size},\n"
        f"  sha256: '{sha256}',\n"
        "  coordinateKind: 'WGS84 representative point',\n"
        f"  placeCount: {len(compact)},\n"
        "} as const\n\n"
        "// [id, name, province, latitude, longitude, geonameId] grouped by province.\n"
        f"const placeRows: [string, string, string, number, number, number][] = {payload}\n\n"
        "export const birthPlaces: BirthPlace[] = placeRows.map(\n"
        "  ([id, name, province, latitude, longitude, geonameId]) => ({ id, name, province, latitude, longitude, geonameId }),\n"
        ")\n\n"
        "export const birthPlaceProvinces: string[] = [...new Set(placeRows.map((row) => row[2]))]\n",
        encoding="utf-8",
    )
    print(f"wrote {len(compact)} places in {len(ordered_provinces)} provinces -> {OUT}")


if __name__ == "__main__":
    main()
