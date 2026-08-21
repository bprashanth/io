#!/usr/bin/env python3
"""Deterministic final-page checks for dev-web-census-001."""

from __future__ import annotations

import argparse
import csv
import io
import json
import re
from pathlib import Path
from urllib.parse import urlparse, urlsplit

from playwright.sync_api import sync_playwright


POPULATION = {"Patna": 5_838_465, "Gaya": 4_391_418, "Nalanda": 2_877_653}
LAKH = {"Patna": 58.38, "Gaya": 43.91, "Nalanda": 28.78}
OFFICIAL_DOMAINS = {"censusindia.gov.in", "www.censusindia.gov.in", "data.gov.in", "www.data.gov.in"}
# 42526 is the official A-01 all-India/State/District population workbook;
# 42557 is the current all-India/State/District basic-population workbook;
# 6191/6420/6421/6427 are the PCA aggregate and district-level records.
VERIFIED_CENSUS_CATALOG_IDS = {"6191", "6420", "6421", "6427", "42526", "42557"}


def normalized_number_present(text: str, number: int) -> bool:
    digits_only = re.sub(r"(?<=\d)[,\s](?=\d)", "", text)
    return re.search(rf"(?<!\d){number}(?!\d)", digits_only) is not None


def artifact_ok(path: Path) -> bool:
    text = path.read_text(errors="replace")
    rows = list(csv.DictReader(io.StringIO(text)))
    if len(rows) != 3:
        return False
    fields = {str(field).strip().lower(): field for field in (rows[0].keys() if rows else []) if field}
    district_key = next((value for key, value in fields.items() if "district" in key), None)
    population_key = next(
        (value for key, value in fields.items() if "total population" in key and "lakh" not in key),
        next((value for key, value in fields.items() if "population" in key and "lakh" not in key), None),
    )
    year_key = next(
        (value for key, value in fields.items() if key == "year" or key == "census year" or key.endswith(" year")),
        next((value for key, value in fields.items() if "year" in key and "population" not in key), None),
    )
    source_key = next((value for key, value in fields.items() if "source" in key and ("url" in key or "link" in key)), None)
    if not all((district_key, population_key, year_key, source_key)):
        return False
    for district, population in POPULATION.items():
        row = next((item for item in rows if str(item.get(district_key, "")).strip().lower() == district.lower()), None)
        if not row:
            return False
        numeric = re.sub(r"[^0-9]", "", str(row.get(population_key, "")))
        if numeric != str(population) or str(row.get(year_key, "")).strip() != "2011":
            return False
        source = str(row.get(source_key, "")).strip()
        parsed = urlparse(source)
        catalog_match = re.search(r"/catalog/(\d+)(?:/|$)", parsed.path)
        if (
            parsed.hostname not in {"censusindia.gov.in", "www.censusindia.gov.in"}
            or not catalog_match
            or catalog_match.group(1) not in VERIFIED_CENSUS_CATALOG_IDS
        ):
            return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("url")
    parser.add_argument("output", type=Path)
    parser.add_argument("--workspace", type=Path)
    parser.add_argument("--network-mode", choices=("online", "offline"), default="online")
    args = parser.parse_args()
    result: dict[str, object] = {
        "case_id": "dev-web-census-001",
        "network_mode": args.network_mode,
        "checks": [],
        "failures": [],
    }

    def check(name: str, passed: bool, failure: str) -> None:
        result["checks"].append({"name": name, "passed": passed})
        if not passed:
            result["failures"].append(failure)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        parsed = urlsplit(args.url)
        allowed = f"{parsed.scheme}://{parsed.netloc}"
        blocked: list[str] = []

        def route_request(route, request) -> None:
            if request.url.startswith(allowed) or request.url.startswith(("data:", "blob:")):
                route.continue_()
            else:
                blocked.append(request.url)
                route.abort("blockedbyclient")

        if args.network_mode == "offline":
            page.route("**/*", route_request)
        errors: list[str] = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        response = page.goto(args.url, wait_until="networkidle", timeout=30_000)
        check("page-opens", bool(response and response.status == 200), "Dashboard did not return HTTP 200")
        body = page.locator("body").inner_text()
        check("census-year-visible", re.search(r"\b2011\b", body) is not None, "Census year 2011 is not visible")

        for district, population in POPULATION.items():
            passed = re.search(rf"\b{district}\b", body, re.I) is not None and normalized_number_present(body, population)
            check(f"{district.lower()}-exact-population", passed, f"Exact {district} population is not visible")
        for district, lakh in LAKH.items():
            # Accept the requested two-decimal representation or the exact
            # persons / 100,000 conversion. The exact value can fall on the
            # opposite side of the two-decimal rounding boundary (Nalanda).
            exact_lakh = POPULATION[district] / 100_000
            passed = re.search(
                rf"{district}[\s\S]{{0,900}}(?:{lakh:.2f}|{exact_lakh:.5f})\s*(?:lakh|L)",
                body,
                re.I,
            ) is not None
            check(f"{district.lower()}-lakh", passed, f"{district} population in lakh is not visible")
        check(
            "largest-and-difference",
            re.search(r"\bPatna\b", body, re.I) is not None
            and re.search(r"(?:largest|highest|most populous)", body, re.I) is not None
            and normalized_number_present(body, 1_447_047),
            "Patna as largest and the exact 1,447,047 difference are not both visible",
        )

        official_links = []
        for index in range(page.locator("a[href]").count()):
            href = page.locator("a[href]").nth(index).get_attribute("href") or ""
            if urlparse(href).hostname in OFFICIAL_DOMAINS:
                official_links.append(href)
        body_urls = re.findall(r"https?://[^\s<>'\"]+", body)
        official_links.extend(url for url in body_urls if urlparse(url.rstrip(".,)" )).hostname in OFFICIAL_DOMAINS)
        verified_links = [
            link
            for link in official_links
            if (match := re.search(r"/catalog/(\d+)(?:/|$)", urlparse(link.rstrip(".,)")).path))
            and match.group(1) in VERIFIED_CENSUS_CATALOG_IDS
        ]
        check("official-source-link", bool(verified_links), "No verified Census 2011 PCA source link is exposed")
        check(
            "publisher-visible",
            "registrar general" in body.lower() and "census commissioner" in body.lower(),
            "Official Census publisher is not visible",
        )

        candidates: list[dict[str, object]] = []
        delivered = False
        if args.workspace:
            for path in sorted(args.workspace.glob("*.csv")):
                passed = artifact_ok(path)
                candidates.append({"file": path.name, "passed": passed, "preview": path.read_text(errors="replace")[:1000]})
                delivered = delivered or passed
        result["artifact_download_candidates"] = candidates
        check(
            "correct-download-delivered",
            delivered,
            "No delivered three-row CSV preserves district, exact population, 2011 and official source URL",
        )

        page.set_viewport_size({"width": 390, "height": 844})
        width = page.evaluate("() => ({client: document.documentElement.clientWidth, scroll: document.documentElement.scrollWidth})")
        result["narrow_page_width"] = width
        check(
            "no-narrow-page-overflow",
            width["scroll"] <= width["client"] + 1,
            f"Narrow page is {width['scroll'] - width['client']} px wider than the viewport",
        )
        result["page_errors"] = errors
        result["blocked_external_requests"] = sorted(set(blocked))
        if errors:
            result["failures"].append("Browser page errors occurred")
        browser.close()

    result["passed"] = not result["failures"]
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
