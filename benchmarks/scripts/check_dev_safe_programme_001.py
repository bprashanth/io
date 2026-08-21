#!/usr/bin/env python3
"""Deterministic final-page checks for dev-safe-programme-001."""

from __future__ import annotations

import argparse
import csv
import io
import json
import re
from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import sync_playwright


EXPECTED = {
    "Purnia": {"completion": 73.0, "employment": 46.0},
    "Nalanda": {"completion": 87.0, "employment": 65.0},
}


def artifact_ok(path: Path) -> bool:
    text = path.read_text(errors="replace")
    rows = list(csv.DictReader(io.StringIO(text)))
    normalized = "\n".join(
        " | ".join(f"{key}={value}" for key, value in row.items()) for row in rows
    )
    observations = all(
        district.lower() in normalized.lower()
        and re.search(r"(?<!\d)2023(?!\d)", normalized)
        and all(
            re.search(rf"(?<!\d){value:g}(?:\.0+)?(?:%|\b)", normalized)
            for value in values.values()
        )
        for district, values in EXPECTED.items()
    )
    source = "synthetic women livelihood outcomes fixture" in normalized.lower()
    return observations and source


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("url")
    parser.add_argument("output", type=Path)
    parser.add_argument("--workspace", type=Path)
    parser.add_argument("--network-mode", choices=("online", "offline"), default="offline")
    args = parser.parse_args()
    result: dict[str, object] = {
        "case_id": "dev-safe-programme-001",
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
        check(
            "source-labelled-as-synthetic",
            "synthetic" in body.lower() and "livelihood" in body.lower(),
            "Synthetic livelihoods source is not visibly labelled",
        )
        formulas = body.lower()
        completion_formula = "completed" in formulas and "enrolled" in formulas
        employment_formula = "employed" in formulas and "enrolled" in formulas
        check("both-formulas-visible", completion_formula and employment_formula, "Both requested formulas are not visible")

        for year in ("2022", "2023"):
            selected = False
            for index in range(page.locator("select").count()):
                select = page.locator("select").nth(index)
                if select.locator(f"option[value='{year}']").count():
                    select.select_option(year, force=True)
                    selected = True
                    break
            if not selected:
                button = page.get_by_role("button", name=re.compile(rf"^\s*(?:Year\s*)?{year}\s*$", re.I)).first
                if button.count() == 1:
                    button.click(force=True)
                    selected = True
            page.wait_for_timeout(200)
            check(f"{year}-control", selected, f"No working year control for {year}")

        body = page.locator("body").inner_text()
        for district, values in EXPECTED.items():
            district_values = re.search(
                rf"{district}[\s\S]{{0,1200}}{values['completion']:g}(?:\.0+)?\s*%[\s\S]{{0,1200}}{values['employment']:g}(?:\.0+)?\s*%",
                body,
                re.I,
            )
            check(f"2023-{district.lower()}-values", district_values is not None, f"Expected 2023 {district} values are not visible")
        check(
            "both-gaps-visible",
            re.search(r"\b14(?:\.0+)?\s*(?:pp|percentage point)", body, re.I) is not None
            and re.search(r"\b19(?:\.0+)?\s*(?:pp|percentage point)", body, re.I) is not None,
            "The 14 pp completion and 19 pp employment gaps are not both visible",
        )
        lower = body.lower()
        caveat = (
            any(
                term in lower
                for term in (
                    "cannot determine",
                    "cannot establish",
                    "cannot tell",
                    "cannot answer",
                    "does not explain",
                    "does not say why",
                    "not enough data",
                    "no “why” can be answered",
                    'no "why" can be answered',
                )
            )
            and any(term in lower for term in ("why", "cause", "causal"))
        )
        check("no-causal-overclaim", caveat, "Page does not clearly say the file cannot establish why Purnia is lower")

        candidates: list[dict[str, object]] = []
        delivered = False
        if args.workspace:
            for path in sorted(args.workspace.glob("*.csv")):
                passed = artifact_ok(path)
                candidates.append({"file": path.name, "passed": passed, "preview": path.read_text(errors="replace")[:600]})
                delivered = delivered or passed
        result["artifact_download_candidates"] = candidates
        check(
            "correct-comparison-download-delivered",
            delivered,
            "No delivered CSV preserves both districts, both metrics, 2023, and the source",
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
