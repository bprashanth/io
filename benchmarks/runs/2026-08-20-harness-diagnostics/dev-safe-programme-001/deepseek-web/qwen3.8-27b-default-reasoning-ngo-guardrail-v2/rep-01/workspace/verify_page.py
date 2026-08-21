#!/usr/bin/env python3
"""Open index.html in headless Chromium, exercise controls, verify displayed values
against independently recomputed expectations, and check desktop/narrow layouts."""
import json, subprocess, sys, time, os

sys.path.insert(0, os.path.dirname(__file__))
from playwright.sync_api import sync_playwright

EXPECTED = json.loads(subprocess.run(
    [sys.executable, "verify_expected.py"], capture_output=True, text=True, check=True
).stdout)

failures = []

def check(label, actual, expected):
    ok = actual == expected
    if not ok:
        failures.append(f"{label}: expected {expected!r}, got {actual!r}")
    print(("PASS" if ok else "FAIL"), label, "" if ok else f"(expected {expected!r}, got {actual!r})")

def table_rows(page, table_id):
    return page.eval_on_selector_all(
        f"#{table_id} tbody tr",
        "rows => rows.map(r => Array.from(r.cells).map(c => c.textContent.trim()))"
    )

def year_table_values(page, table_id, districts):
    """Map rows to {district: [enrolled, completed, employed, cr, eoe, eoc]}."""
    out = {}
    for row in table_rows(page, table_id):
        d = row[0]
        out[d] = row[1:]
    return out

def main():
    base = os.path.dirname(os.path.abspath(__file__))
    server = subprocess.Popen(
        [sys.executable, "-m", "http.server", "8099", "--bind", "127.0.0.1", "--directory", base],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(0.6)
    url = "http://127.0.0.1:8099/index.html"

    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            ctx = browser.new_context(viewport={"width": 1280, "height": 900})
            page = ctx.new_page()
            page.goto(url)
            page.wait_for_load_state("networkidle")

            # --- 1. Default state: year=2023, compare=2022 ---
            check("default year select", page.eval_on_selector("#year-select", "s => s.value"), "2023")
            check("default compare select", page.eval_on_selector("#compare-select", "s => s.value"), "2022")
            check("main-year title", page.eval_on_selector("#main-year-title", "h => h.textContent"), "Districts in 2023 (shown year)")
            check("compare block visible by default", page.eval_on_selector("#compare-block", "s => !s.hidden"), True)

            for d in EXPECTED["districts"]:
                exp = EXPECTED["year2023"][d]
                got = year_table_values(page, "main-table", d)[d]
                check(f"main 2023 {d}", got, [exp["enrolled"], exp["completed"], exp["employed"],
                                                exp["completionRate"], exp["employedOfEnrolled"], exp["employedOfCompleted"]])
                expc = EXPECTED["year2022"][d]
                gotc = year_table_values(page, "compare-table", d)[d]
                check(f"compare 2022 {d}", gotc, [expc["enrolled"], expc["completed"], expc["employed"],
                                                   expc["completionRate"], expc["employedOfEnrolled"], expc["employedOfCompleted"]])

            # change table 2022 -> 2023
            check("change title", page.eval_on_selector("#change-title", "h => h.textContent"), "Change from 2022 to 2023")
            rows = table_rows(page, "change-table")
            for row in rows:
                d = row[0]
                exp = EXPECTED["change_2022_to_2023"][d]
                check(f"change {d}", row[1:], [exp["completionRate"], exp["employedOfEnrolled"], exp["employedOfCompleted"]])

            # formulas + source visible
            body = page.eval_on_selector("body", "b => b.textContent")
            for needle in ["completed_training ÷ women_enrolled × 100",
                           "employed_at_6_months ÷ women_enrolled × 100",
                           "employed_at_6_months ÷ completed_training × 100",
                           "women_livelihood_outcomes.csv",
                           "synthetic women livelihood outcomes fixture"]:
                check(f"page shows {needle!r}", needle in body, True)

            # --- 1b. "Why is Purnia lower" section present and correct ---
            for needle in ["Why is Purnia lower than Nalanda? (2023)",
                           "What this file cannot tell us",
                           "Purnia 73.0% × 63.0% = 46.0% (598 ÷ 1,300)",
                           "Nalanda 87.0% × 74.7% = 65.0% (650 ÷ 1,000)",
                           "14.0 pp lower) and employment among completers 63.0% vs 74.7% (11.7 pp lower",
                           "The same pattern is in 2022 (completion 70.0% vs 85.0%; employment out of all enrolled 42.0% vs 60.0%)",
                           "This file alone cannot say which intervention to make in Purnia"]:
                check(f"why-section shows {needle!r}", needle in body, True)

            # no horizontal overflow at desktop width
            check("no horizontal overflow (desktop 1280)",
                  page.evaluate("() => document.documentElement.scrollWidth <= window.innerWidth"), True)
            page.screenshot(path="shot_desktop.png", full_page=True)

            # --- 2. Exercise controls: year=2022, compare=2023 ---
            page.eval_on_selector("#year-select", "s => { s.value='2022'; s.dispatchEvent(new Event('change')); }")
            page.eval_on_selector("#compare-select", "s => { s.value='2023'; s.dispatchEvent(new Event('change')); }")
            check("year select after change", page.eval_on_selector("#year-select", "s => s.value"), "2022")
            check("compare select after change", page.eval_on_selector("#compare-select", "s => s.value"), "2023")
            check("main-year title after change", page.eval_on_selector("#main-year-title", "h => h.textContent"), "Districts in 2022 (shown year)")
            check("change title after change", page.eval_on_selector("#change-title", "h => h.textContent"), "Change from 2023 to 2022")
            for d in EXPECTED["districts"]:
                exp = EXPECTED["year2022"][d]
                got = year_table_values(page, "main-table", d)[d]
                check(f"main 2022 {d}", got, [exp["enrolled"], exp["completed"], exp["employed"],
                                                exp["completionRate"], exp["employedOfEnrolled"], exp["employedOfCompleted"]])
                expc = EXPECTED["year2023"][d]
                gotc = year_table_values(page, "compare-table", d)[d]
                check(f"compare 2023 {d}", gotc, [expc["enrolled"], expc["completed"], expc["employed"],
                                                   expc["completionRate"], expc["employedOfEnrolled"], expc["employedOfCompleted"]])
            for row in table_rows(page, "change-table"):
                d = row[0]
                exp = EXPECTED["change_2023_to_2022"][d]
                check(f"change {d} (2023 to 2022)", row[1:], [exp["completionRate"], exp["employedOfEnrolled"], exp["employedOfCompleted"]])

            # --- 3. Compare = none hides the block ---
            page.eval_on_selector("#compare-select", "s => { s.value='none'; s.dispatchEvent(new Event('change')); }")
            check("compare block hidden when none", page.eval_on_selector("#compare-block", "s => s.hidden"), True)

            # --- 4. Reload keeps state via URL params (year=2022 was saved) ---
            page.goto(url)
            page.wait_for_load_state("networkidle")
            check("reload keeps year via URL/localStorage", page.eval_on_selector("#year-select", "s => s.value"), "2022")
            check("reload keeps compare via URL/localStorage", page.eval_on_selector("#compare-select", "s => s.value"), "none")

            # --- 5. URL params take precedence: ?year=2023&compare=2022 ---
            page.goto(url + "?year=2023&compare=2022")
            page.wait_for_load_state("networkidle")
            check("URL param year wins", page.eval_on_selector("#year-select", "s => s.value"), "2023")
            check("URL param compare wins", page.eval_on_selector("#compare-select", "s => s.value"), "2022")

            # --- 5b. District comparison: defaults Purnia vs Nalanda in 2023 ---
            check("district-a default", page.eval_on_selector("#district-a", "s => s.value"), "Purnia")
            check("district-b default", page.eval_on_selector("#district-b", "s => s.value"), "Nalanda")
            drows = table_rows(page, "district-table")
            dexpected_2023 = [
                ["Women enrolled (women)", "1,300", "1,000", "\u2014"],
                ["Completed training (women)", "949", "870", "\u2014"],
                ["Employed at 6 months (women)", "598", "650", "\u2014"],
                ["Training completion rate (%)", "73.0", "87.0", "+14.0 pp"],
                ["Employment after 6 months, out of all enrolled (%)", "46.0", "65.0", "+19.0 pp"],
                ["Employment after 6 months, out of training completers (%)", "63.0", "74.7", "+11.7 pp"],
            ]
            check("district table 2023 (Purnia vs Nalanda)", drows, dexpected_2023)
            summary = page.eval_on_selector("#district-summary", "p => p.textContent")
            for needle in ["Nalanda's training completion rate (87.0%) is 14.0 pp higher than Purnia's (73.0%)",
                           "Nalanda's employment after 6 months, out of all enrolled (65.0%) is 19.0 pp higher than Purnia's (46.0%)",
                           "Nalanda's employment after 6 months, out of training completers (74.7%) is 11.7 pp higher than Purnia's (63.0%)"]:
                check(f"district summary contains {needle!r}", needle in summary, True)
            check("district caption 2023", page.eval_on_selector("#district-table caption", "c => c.textContent"),
                  "Raw counts and rates for Purnia and Nalanda in 2023")

            # change year to 2022 -> gaps recompute for 2022
            page.eval_on_selector("#year-select", "s => { s.value='2022'; s.dispatchEvent(new Event('change')); }")
            dexpected_2022 = [
                ["Women enrolled (women)", "1,200", "900", "\u2014"],
                ["Completed training (women)", "840", "765", "\u2014"],
                ["Employed at 6 months (women)", "504", "540", "\u2014"],
                ["Training completion rate (%)", "70.0", "85.0", "+15.0 pp"],
                ["Employment after 6 months, out of all enrolled (%)", "42.0", "60.0", "+18.0 pp"],
                ["Employment after 6 months, out of training completers (%)", "60.0", "70.6", "+10.6 pp"],
            ]
            check("district table 2022 (Purnia vs Nalanda)", table_rows(page, "district-table"), dexpected_2022)
            check("district caption 2022", page.eval_on_selector("#district-table caption", "c => c.textContent"),
                  "Raw counts and rates for Purnia and Nalanda in 2022")

            # swap districts -> gaps flip sign
            page.eval_on_selector("#district-a", "s => { s.value='Nalanda'; s.dispatchEvent(new Event('change')); }")
            page.eval_on_selector("#district-b", "s => { s.value='Purnia'; s.dispatchEvent(new Event('change')); }")
            dexpected_2022_swap = [
                ["Women enrolled (women)", "900", "1,200", "\u2014"],
                ["Completed training (women)", "765", "840", "\u2014"],
                ["Employed at 6 months (women)", "540", "504", "\u2014"],
                ["Training completion rate (%)", "85.0", "70.0", "-15.0 pp"],
                ["Employment after 6 months, out of all enrolled (%)", "60.0", "42.0", "-18.0 pp"],
                ["Employment after 6 months, out of training completers (%)", "70.6", "60.0", "-10.6 pp"],
            ]
            check("district table 2022 swapped (Nalanda vs Purnia)", table_rows(page, "district-table"), dexpected_2022_swap)

            # reload keeps district picks via URL params
            page.goto(url)
            page.wait_for_load_state("networkidle")
            check("reload keeps district a", page.eval_on_selector("#district-a", "s => s.value"), "Nalanda")
            check("reload keeps district b", page.eval_on_selector("#district-b", "s => s.value"), "Purnia")

            # --- 5c. Download button produces the exact 2023 Purnia-vs-Nalanda CSV ---
            page.goto(url + "?year=2023&a=Purnia&b=Nalanda")
            page.wait_for_load_state("networkidle")
            with page.expect_download() as dl_info:
                page.click("#district-download")
            download = dl_info.value
            check("download filename", download.suggested_filename, "district-comparison-2023-purnia-vs-nalanda.csv")
            dl_path = os.path.join(base, "_download_check.csv")
            download.save_as(dl_path)
            with open(dl_path, encoding="utf-8") as fh:
                downloaded = fh.read()
            artifact_path = os.path.join(base, "district-comparison-2023-purnia-vs-nalanda.csv")
            with open(artifact_path, encoding="utf-8") as fh:
                ondisk = fh.read()
            os.remove(dl_path)
            check("downloaded CSV matches independently generated file", downloaded, ondisk)
            import io as _io, csv as _csv
            parsed = list(_csv.reader(_io.StringIO(ondisk)))
            check("CSV header row", parsed[0], ["Metric", "Purnia", "Nalanda", "Gap (Nalanda minus Purnia)"])
            check("CSV completion row", parsed[4], ["Training completion rate (%)", "73.0", "87.0", "+14.0 pp"])
            check("CSV employed-of-enrolled row", parsed[5],
                  ["Employment after 6 months, out of all enrolled (%)", "46.0", "65.0", "+19.0 pp"])
            check("CSV employed-of-completers row", parsed[6],
                  ["Employment after 6 months, out of training completers (%)", "63.0", "74.7", "+11.7 pp"])
            check("CSV source rows present",
                  ["Source file,women_livelihood_outcomes.csv" in ondisk.replace("\r\n", "\n"),
                   "synthetic women livelihood outcomes fixture" in ondisk,
                   "Year,2023" in ondisk.replace("\r\n", "\n")], [True, True, True])

            # --- 6. Narrow layout: 390px wide, no page-level horizontal overflow ---
            page.set_viewport_size({"width": 390, "height": 844})
            page.goto(url + "?year=2023&compare=2022")
            page.wait_for_load_state("networkidle")
            check("no horizontal overflow (narrow 390)",
                  page.evaluate("() => document.documentElement.scrollWidth <= window.innerWidth"), True)
            check("tables reachable at narrow width", page.eval_on_selector("#main-table tbody tr", "r => r.cells.length"), 7)
            page.screenshot(path="shot_narrow.png", full_page=True)

            browser.close()
    finally:
        server.terminate()
        server.wait()

    print()
    if failures:
        print(f"{len(failures)} FAILURE(S):")
        for f in failures:
            print(" -", f)
        sys.exit(1)
    print("ALL CHECKS PASSED")

if __name__ == "__main__":
    main()
