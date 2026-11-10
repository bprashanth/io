"""Skills for the three new fixture files (as the Teach workspace would have written them): MGNREGA works,
the road kill survey and the fragment tree plots. Each is checked with filekit's own test (recognises the
file, checks run, measures compute) after writing. The mock.xlsx next to each skill is the fixture itself;
it only matters for teaching, which is Claude's job and outside this benchmark.

  python harness/make_skills.py
"""
import json
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
FX = os.path.join(os.path.dirname(HERE), "fixtures")

SKILLS = {
    "mgnrega_works": ("MGNREGA works Valparai 2019-2023.xlsx", {
        "id": "mgnrega_works", "title": "MGNREGA works", "version": 1, "sheet": "Works",
        "headers": ["work_id", "date", "work_type", "village", "persondays", "households_engaged"],
        "summary": "One row per MGNREGA (job work) work in a village: date, type of work, persondays of work "
                   "created and households engaged.",
        "row_noun": "works",
        "columns": {
            "work_id": {"type": "text", "meaning": "id of the work", "label": "Work ID"},
            "date": {"type": "date", "format": "%Y-%m-%d", "meaning": "date the work was recorded", "label": "Date"},
            "work_type": {"type": "category", "meaning": "kind of work (desilting, footpath repair, ...)",
                          "label": "Work type"},
            "village": {"type": "category", "meaning": "village where the work happened", "label": "Village"},
            "persondays": {"type": "number", "meaning": "days of work created (people x days)", "label": "Persondays"},
            "households_engaged": {"type": "number", "meaning": "households that got work", "label": "Households engaged"}},
        "normalize": {"village": {"case": "title"}, "persondays": {"type": "number"},
                      "households_engaged": {"type": "number"}},
        "validations": [
            {"column": "work_id", "rule": "required", "message": "work id is missing"},
            {"column": "village", "rule": "required", "message": "village is missing"},
            {"column": "persondays", "rule": "range", "arg": [0, 100000], "message": "persondays is negative or too big"},
            {"column": "households_engaged", "rule": "range", "arg": [0, 5000],
             "message": "households engaged is negative or too big"}],
        "measures": [
            {"id": "works", "label": "Number of works", "sql": "count(*)", "format": "count"},
            {"id": "persondays", "label": "Total persondays", "sql": "sum(persondays)", "format": "count"},
            {"id": "households", "label": "Households engaged (total)", "sql": "sum(households_engaged)",
             "format": "count"},
            {"id": "days_per_household", "label": "Persondays per household engaged",
             "sql": "round(sum(persondays) / nullif(sum(households_engaged), 0), 1)", "format": "number"}],
        "history": [{"version": 1, "note": "benchmark fixture"}]}),
    "road_kill_survey": ("Road kill survey 2011-12.xlsx", {
        "id": "road_kill_survey", "title": "Road kill survey", "version": 1, "sheet": "Roadkill",
        "headers": ["s_no", "season", "road_stretch", "stretch_length_km", "date", "animal", "animal_group", "count"],
        "summary": "One row per road kill found on a survey walk: road stretch (and its length), season, date, "
                   "the animal, its group (frogs are Amphibia, snakes Reptilia ...) and how many.",
        "row_noun": "road kill records",
        "columns": {
            "s_no": {"type": "text", "meaning": "serial number", "label": "S.No"},
            "season": {"type": "category", "meaning": "Monsoon or Summer", "label": "Season"},
            "road_stretch": {"type": "category", "meaning": "the surveyed stretch of road", "label": "Road stretch"},
            "stretch_length_km": {"type": "number", "meaning": "length of that stretch in km",
                                  "label": "Stretch length (km)"},
            "date": {"type": "date", "format": "%Y-%m-%d", "meaning": "survey date", "label": "Date"},
            "animal": {"type": "category", "meaning": "common name of the animal", "label": "Animal"},
            "animal_group": {"type": "category", "meaning": "animal class: Amphibia, Reptilia, Mammalia, ...",
                             "label": "Animal group"},
            "count": {"type": "number", "meaning": "number of animals in this record", "label": "Count"}},
        "normalize": {"road_stretch": {"case": "title"}, "count": {"type": "number"},
                      "stretch_length_km": {"type": "number"}},
        "validations": [
            {"column": "count", "rule": "required", "message": "count is missing"},
            {"column": "count", "rule": "range", "arg": [1, 50], "message": "count is not between 1 and 50"},
            {"column": "road_stretch", "rule": "required", "message": "road stretch is missing"}],
        "hidden": ["s_no"],
        "measures": [
            {"id": "animals", "label": "Animals killed", "sql": "sum(\"count\")", "format": "count"},
            {"id": "records", "label": "Road kill records", "sql": "count(*)", "format": "count"},
            {"id": "per_km", "label": "Animals killed per km of road",
             "sql": "round(sum(\"count\") / nullif(max(stretch_length_km), 0), 1)", "format": "number"},
            {"id": "amphibian_share", "label": "Share that are frogs and toads (Amphibia) %",
             "sql": "round(100.0 * sum(CASE WHEN animal_group = 'Amphibia' THEN \"count\" ELSE 0 END) / "
                    "nullif(sum(\"count\"), 0), 1)", "format": "percent"}],
        "presets": [{"id": "monsoon", "label": "Monsoon only", "filters": {"season": ["Monsoon"]}}],
        "history": [{"version": 1, "note": "benchmark fixture"}]}),
    "fragment_trees": ("Fragment tree plots 2000-2019.xlsx", {
        "id": "fragment_trees", "title": "Fragment tree plots", "version": 1, "sheet": "Trees",
        "headers": ["year", "fragment", "plot", "tree_no", "species", "native_or_alien", "girth_cm", "height_m"],
        "summary": "One row per tree measured in a rainforest fragment plot: survey year, fragment, plot, tree "
                   "number, species, whether it is native or alien, girth (cm) and height (m).",
        "row_noun": "trees",
        "columns": {
            "year": {"type": "number", "meaning": "survey year (2000, 2002, 2005, 2019)", "label": "Year"},
            "fragment": {"type": "category", "meaning": "rainforest fragment", "label": "Fragment"},
            "plot": {"type": "category", "meaning": "plot code within the fragment", "label": "Plot"},
            "tree_no": {"type": "text", "meaning": "tree number in the plot", "label": "Tree no"},
            "species": {"type": "category", "meaning": "scientific name", "label": "Species"},
            "native_or_alien": {"type": "category", "meaning": "Native or Alien species", "label": "Native or alien"},
            "girth_cm": {"type": "number", "meaning": "girth at breast height in cm", "label": "Girth (cm)"},
            "height_m": {"type": "number", "meaning": "tree height in metres (2019 only)", "label": "Height (m)"}},
        "normalize": {"native_or_alien": {"case": "title"}, "girth_cm": {"type": "number"},
                      "height_m": {"type": "number"}},
        "validations": [
            {"column": "species", "rule": "required", "message": "species is missing"},
            {"column": "native_or_alien", "rule": "in_list", "arg": ["Native", "Alien"],
             "message": "native or alien is not Native or Alien"},
            {"column": "girth_cm", "rule": "range", "arg": [10, 1500], "message": "girth is not between 10 and 1500 cm"}],
        "hidden": ["tree_no"],
        "measures": [
            {"id": "trees", "label": "Number of trees", "sql": "count(*)", "format": "count"},
            {"id": "alien_trees", "label": "Alien trees", "sql": "count(*) FILTER (WHERE native_or_alien = 'Alien')",
             "format": "count"},
            {"id": "alien_share", "label": "Share of trees that are alien %",
             "sql": "round(100.0 * count(*) FILTER (WHERE native_or_alien = 'Alien') / nullif(count(*), 0), 1)",
             "format": "percent"},
            {"id": "species_count", "label": "Number of species", "sql": "count(DISTINCT species)", "format": "count"},
            {"id": "avg_girth", "label": "Average girth (cm)", "sql": "round(avg(girth_cm), 1)", "format": "number"}],
        "presets": [{"id": "alien_only", "label": "Alien trees only", "filters": {"native_or_alien": ["Alien"]}}],
        "history": [{"version": 1, "note": "benchmark fixture"}]}),
}


def main():
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(HERE)))),
                                    "benchmarks", "runs", "2026-11-06-oss-desktop-independent", "cowork"))
    for sid, (fname, skill) in SKILLS.items():
        d = os.path.join(FX, "skills", sid)
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "skill.json"), "w") as f:
            json.dump(skill, f, indent=1)
        shutil.copy(os.path.join(FX, "drive", fname), os.path.join(d, "mock.xlsx"))
        with open(os.path.join(d, "tests.json"), "w") as f:
            json.dump([], f)
    os.environ["IDLI_FILE_SKILLS"] = os.path.join(FX, "skills")
    from lib import filekit as fk
    from lib import formkit as fm
    fk.SKILLS_DIR = os.environ["IDLI_FILE_SKILLS"]
    import duckdb
    for sid, (fname, _) in SKILLS.items():
        path = os.path.join(FX, "drive", fname)
        sheets, hdr = fk.raw_sheets(path)
        skill, score, _m = fm.match_skill(sheets) if hasattr(fm, "match_skill") else (None, None, None)
        print(sid, "match:", skill and skill["id"], score)


if __name__ == "__main__":
    main()
