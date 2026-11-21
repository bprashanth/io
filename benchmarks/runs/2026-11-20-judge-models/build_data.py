"""Build the synthetic judge set: 38 files about, near, or nowhere near "endangered species".

Every item is written here, in full, so the set is reproducible and reviewable. Names, places and numbers are
invented. `labels.json` holds the expected answer, whether the item is hard (a near miss or a trap), and why.

    python build_data.py          # writes data/ and labels.json (PDFs need LibreOffice: soffice)
"""
import csv
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

import docx
import openpyxl

HERE = Path(__file__).parent
DATA = HERE / 'data'

# (path under data/, expected, hard, why, content)
#   content: str for txt/py/csv-as-text, list of rows for csv/xlsx, list of paragraphs for docx/pdf
ITEMS = [
    # ------------------------------------------------------------------ yes
    ('Field data/iucn_sightings_kabini_2026.csv', 'yes', False, 'sightings with IUCN threat status per species',
     [['date', 'transect', 'species', 'iucn_status', 'count'],
      ['2026-03-02', 'T4', 'Asian elephant', 'EN', 7], ['2026-03-02', 'T4', 'Dhole', 'EN', 3],
      ['2026-03-03', 'T1', 'Indian vulture', 'CR', 2], ['2026-03-03', 'T2', 'Gaur', 'VU', 11],
      ['2026-03-04', 'T3', 'Bengal tiger', 'EN', 1], ['2026-03-05', 'T1', 'Sloth bear', 'VU', 2]]),
    ('Enforcement/pangolin_seizures_2025.xlsx', 'yes', False, 'seizure log of a CITES Appendix I species',
     [['Date', 'District', 'Item', 'Quantity (kg)', 'Species', 'CITES', 'Case no.'],
      ['2025-01-14', 'Malkangiri', 'scales', 12.5, 'Indian pangolin', 'App. I', 'WL/112/25'],
      ['2025-03-02', 'Koraput', 'live animal', 1, 'Indian pangolin', 'App. I', 'WL/140/25'],
      ['2025-06-21', 'Rayagada', 'scales', 4.2, 'Chinese pangolin', 'App. I', 'WL/201/25']]),
    ('Reports/vulture_recovery_plan.pdf', 'yes', False, 'recovery plan for critically endangered vultures',
     ['Gyps Vulture Recovery Plan, Central India, 2026-2030',
      'Populations of the white-rumped vulture (Gyps bengalensis) and Indian vulture (Gyps indicus) fell by more '
      'than 95% after veterinary diclofenac entered livestock carcasses. Both are listed as Critically Endangered.',
      'This plan sets out three actions: diclofenac-free zones of 100 km around the two remaining breeding '
      'colonies, safe feeding stations, and the release of 40 captive-bred birds by 2028.',
      'Monitoring: nest counts each February; carcass sampling for NSAIDs every quarter.']),
    ('Grants/bustard_grant_report_q3.pdf', 'yes', False, 'grant report on the great Indian bustard',
     ['Quarterly report to the Habitat Trust, July to September',
      'Project: Saving the Great Indian Bustard in the Thar grasslands. Fewer than 150 birds remain in the wild.',
      'This quarter we marked 6 km of power lines with bird diverters, after two collision deaths in May. The '
      'community grassland patrol recorded 9 sightings, including a female with a chick near Sam.',
      'Spending: 4.2 lakh of 5 lakh disbursed. Next quarter: a second hatchery egg collection.']),
    ('Scripts/population_trend.py', 'yes', False, 'computes declines for red-listed species',
     '"""Fit a log-linear trend to annual counts of red-listed species and flag steep declines."""\n'
     'import math\n\nRED_LIST = {"Gharial": "CR", "Hoolock gibbon": "EN", "Nilgiri tahr": "EN", "Lion-tailed macaque": "EN"}\n\n'
     'def annual_decline(counts):\n    """counts: list of (year, n). Returns the yearly % change."""\n'
     '    xs = [y for y, _ in counts]; ys = [math.log(n) for _, n in counts]\n'
     '    mx, my = sum(xs) / len(xs), sum(ys) / len(ys)\n'
     '    b = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sum((x - mx) ** 2 for x in xs)\n'
     '    return (math.exp(b) - 1) * 100\n\n'
     'def flag(species_counts, threshold=-5):\n'
     '    return {s: round(annual_decline(c), 1) for s, c in species_counts.items()\n'
     '            if s in RED_LIST and annual_decline(c) < threshold}\n'),
    ('Field data/hornbill_nest_notes.docx', 'yes', False, 'nest monitoring of a vulnerable hornbill',
     ['Great hornbill nest monitoring, Anamalai, season notes',
      'Nest tree 14 (Cullenia exarillata) active again; the male delivered figs 11 times in 3 hours.',
      'The great hornbill is listed as Vulnerable; logging of large fig and Cullenia trees is the main threat here.',
      'Two nests from last season failed after the trees were lopped. We will talk to the estate manager.']),
    ('Field data/camera_trap_detections_jan.csv', 'yes', True, 'no status column, but the species are endangered',
     [['camera_id', 'timestamp', 'species', 'individuals'],
      ['CT-07', '2026-01-03 02:14', 'tiger', 1], ['CT-07', '2026-01-05 21:40', 'dhole', 4],
      ['CT-11', '2026-01-09 04:02', 'Indian pangolin', 1], ['CT-02', '2026-01-12 23:55', 'tiger', 2],
      ['CT-11', '2026-01-19 01:31', 'rusty-spotted cat', 1]]),
    ('Volunteers/turtle_hatchery_rota.txt', 'yes', True, 'logistics, but for an olive ridley hatchery',
     'Olive ridley hatchery, Rushikulya, volunteer rota for March\n\n'
     'Night patrol 10 pm to 4 am: Meena, Arjun (Mon, Thu); Farhan, Lata (Tue, Fri); Sunil alone on Sundays.\n'
     'Move any nest laid below the high tide line into the hatchery within 2 hours. Note the nest number and egg count.\n'
     'Olive ridleys are a threatened species; do not use torches on the beach, use the red lamps only.\n'
     'Hatchlings are released at dawn only. Keep dogs off the beach.\n'),
    ('Budgets/tiger_corridor_budget_2026.xlsx', 'yes', True, 'a budget, but for a tiger corridor and anti-poaching',
     [['Line', 'Item', 'Amount (INR)', 'Notes'],
      [1, 'Anti-poaching camps (4 x 12 months)', 2880000, 'Kanha-Pench corridor'],
      [2, 'Underpass monitoring cameras', 640000, 'NH-44 wildlife underpasses'],
      [3, 'Compensation for livestock lost to tigers', 900000, 'paid within 30 days'],
      [4, 'Corridor village meetings', 120000, '']]),
    ('Policy/cites_cop21_brief.pdf', 'yes', False, 'brief on CITES listing changes',
     ['Policy brief: what CoP21 means for wildlife trade in South Asia',
      'Parties moved the Tokay gecko and two freshwater turtle species to Appendix I, banning commercial trade.',
      'For India this affects customs screening at five ports. We recommend training for 200 officers and a '
      'shared database of seizures of listed species.']),
    ('Scripts/poaching_alert.py', 'yes', True, 'code, protecting rhinos from poaching',
     '"""Send an SMS to the nearest ranger post when a fence sensor fires near a rhino area."""\n'
     'import json, urllib.request\n\nRHINO_ZONES = {"Kaziranga-E": (26.66, 93.53), "Pobitora": (26.23, 92.05)}\n\n'
     'def nearest_post(lat, lon, posts):\n    return min(posts, key=lambda p: (p["lat"] - lat) ** 2 + (p["lon"] - lon) ** 2)\n\n'
     'def alert(event, posts, send):\n    """event: {zone, lat, lon, time}. Greater one-horned rhinos are poached for horn."""\n'
     '    if event["zone"] in RHINO_ZONES:\n        p = nearest_post(event["lat"], event["lon"], posts)\n'
     '        send(p["phone"], f"Fence alarm in {event[\'zone\']} at {event[\'time\']}: possible poachers")\n'),
    ('Comms/press_release_frog.docx', 'yes', False, 'rediscovery of a critically endangered frog',
     ['For immediate release: frog not seen for 80 years found again in the Western Ghats',
      'Volunteers found three adults of a night frog last recorded in 1946. The species is assessed as Critically '
      'Endangered, known from a single stream.',
      'The landowner has agreed to keep a 50 metre buffer along the stream.']),
    ('Field data/seed_bank_accessions.csv', 'yes', True, 'plants, from the Red Data Book',
     [['accession', 'species', 'red_data_book', 'collected', 'seeds'],
      ['SB-0412', 'Ceropegia fantastica', 'Endangered', '2025-11-02', 340],
      ['SB-0413', 'Hubbardia heptaneuron', 'Critically endangered', '2025-11-09', 85],
      ['SB-0414', 'Dipterocarpus bourdillonii', 'Critically endangered', '2025-12-01', 60]]),
    ('Volunteers/red_panda_census_email.txt', 'yes', False, 'census volunteers for red pandas',
     'Subject: Red panda census, volunteers needed\n\nHi all,\nThe winter census of red pandas in Singalila starts '
     'on 4 January. Red pandas are endangered and the park has fewer than 40 left by the last count. We need 12 '
     'volunteers for 5 days to walk droppings transects. Training on 2 January.\nThanks, Dawa\n'),
    ('Field data/Sheet1.xlsx', 'yes', True, 'a bare file name; the rows are gharial nest counts',
     [['River stretch', 'Year', 'Nests', 'Hatchlings'],
      ['Chambal A', 2023, 41, 1210], ['Chambal A', 2024, 38, 1033], ['Chambal B', 2024, 22, 590],
      ['Chambal B', 2025, 19, 411], ['Note', 'gharial', 'Critically Endangered', 'sand mining at B']]),
    ('Education/endangered_animals_module.pdf', 'yes', False, 'a school module on endangered animals',
     ['Class 6 environment module: animals in danger',
      'Lesson 1: what does endangered mean? The IUCN Red List and its categories.',
      'Lesson 2: three Indian animals at risk: the tiger, the snow leopard, the Ganges river dolphin. Why each is '
      'declining, and what people are doing about it.', 'Activity: draw a food web that includes one of them.']),
    ('Reports/dolphin_survey_summary.txt', 'yes', False, 'survey of the endangered Ganges river dolphin',
     'Ganges river dolphin survey, Bhagalpur to Kahalgaon, November\n\n'
     'Boat-based count over 60 km found 43 dolphins (31 adults, 12 calves). The species is Endangered; '
     'gill nets and sand mining were seen at 7 locations.\n'),
    ('Grants/snow_leopard_proposal.docx', 'yes', False, 'proposal for snow leopard conservation',
     ['Proposal: community herding practices to reduce snow leopard conflict in Spiti',
      'Snow leopards are classified as Vulnerable. Most retaliation killing follows night attacks on corrals.',
      'We ask for funds for 30 predator-proof corrals and a livestock insurance pilot.']),

    # ------------------------------------------------------------------ no
    ('Reports/endangered_languages_report.pdf', 'no', True, 'endangered languages, not species',
     ['Endangered languages of the Andaman Islands',
      'Great Andamanese has fewer than ten fluent speakers. Jarawa and Onge are spoken by small communities.',
      'This report records word lists and recommends school materials in each language.']),
    ('Essays/dinosaur_extinction.docx', 'no', True, 'extinct, not endangered',
     ['Why the dinosaurs died', 'About 66 million years ago an asteroid struck near what is now Mexico.',
      'Dust blocked the sun, plants died, and most large animals followed. Birds are the dinosaurs that survived.']),
    ('Finance/zoo_ticket_sales.csv', 'no', True, 'a zoo, but only ticket sales',
     [['date', 'adult', 'child', 'revenue_inr'], ['2026-02-01', 812, 403, 56950], ['2026-02-02', 1290, 655, 90725],
      ['2026-02-03', 433, 120, 26410]]),
    ('Field data/garden_bird_checklist.csv', 'no', True, 'a species list with no threat at all',
     [['species', 'scientific_name', 'seen'], ['House sparrow', 'Passer domesticus', 'yes'],
      ['Common myna', 'Acridotheres tristis', 'yes'], ['Red-vented bulbul', 'Pycnonotus cafer', 'yes'],
      ['Rose-ringed parakeet', 'Psittacula krameri', 'no']]),
    ('Budgets/safari_tourism_budget.xlsx', 'no', True, 'wildlife tourism revenue, not conservation',
     [['Month', 'Jeep safaris', 'Revenue (INR)', 'Fuel', 'Guide fees'],
      ['October', 412, 1648000, 210000, 164800], ['November', 530, 2120000, 262000, 212000],
      ['December', 611, 2444000, 301000, 244400]]),
    ('Reports/forest_carbon_paper.pdf', 'no', True, 'a carbon paper with one passing mention of species',
     ['Above-ground carbon in teak and sal plantations, central India',
      'We measured 120 plots. Sal plots stored 1.6 times the carbon of teak plots of the same age.',
      'Mixed plantations may also offer habitat for some species, which we did not study.',
      'Methods: allometric equations, soil cores to 30 cm.']),
    ('Wildlife data/csv_cleaner.py', 'no', True, 'a generic cleaner that only sits in a wildlife folder',
     '"""Clean a CSV: strip spaces, drop empty rows, normalise dates to ISO."""\nimport csv, sys, datetime\n\n'
     'def clean(path_in, path_out):\n    with open(path_in) as f, open(path_out, "w", newline="") as g:\n'
     '        w = csv.writer(g)\n        for row in csv.reader(f):\n            row = [c.strip() for c in row]\n'
     '            if any(row):\n                w.writerow(row)\n'),
    ('Comms/bookstores_column.txt', 'no', True, '"endangered" used as a metaphor',
     'Endangered: the neighbourhood bookstore\n\nThree bookshops on our street closed this year. Rents doubled '
     'and readers moved online. The last one left, run by Mr Iyer since 1978, may be next.\n'),
    ('Admin/leave_policy.docx', 'no', False, 'HR policy',
     ['Leave policy, updated 2026', 'Staff get 24 days of paid leave a year, plus 12 days of sick leave.',
      'Field staff may carry over up to 10 days.']),
    ('Field data/cattle_vaccination.csv', 'no', False, 'livestock records',
     [['village', 'owner', 'animals', 'vaccine', 'date'], ['Moyar', 'K. Raju', 6, 'FMD', '2026-01-10'],
      ['Mavanalla', 'S. Bee', 3, 'FMD', '2026-01-10'], ['Masinagudi', 'P. Nair', 9, 'HS', '2026-01-12']]),
    ('Reports/lantana_removal.pdf', 'no', True, 'invasive plant removal, not threatened species',
     ['Lantana removal trial, Bandipur buffer', 'Cut-rootstock removal cleared 18 hectares in 40 days.',
      'Native grasses returned within one monsoon. Cost per hectare fell from 52,000 to 31,000 rupees.']),
    ('Admin/pet_adoptions.xlsx', 'no', False, 'pet shelter adoptions',
     [['Month', 'Dogs adopted', 'Cats adopted', 'Returned'], ['Jan', 21, 14, 2], ['Feb', 18, 9, 1]]),
    ('Scripts/species_name_normalizer.py', 'no', True, 'a name utility; a tiger appears only as test data',
     '"""Map common names to scientific names, ignoring case and extra spaces."""\n\nNAMES = {}\n\n'
     'def load(path):\n    for line in open(path):\n        common, sci = line.rstrip("\\n").split("\\t")\n'
     '        NAMES[common.strip().lower()] = sci.strip()\n\n'
     'def scientific(common):\n    return NAMES.get(" ".join(common.lower().split()))\n\n'
     'def test():\n    NAMES["tiger"] = "Panthera tigris"\n    assert scientific("  Tiger ") == "Panthera tigris"\n'),
    ('Comms/fish_curry_recipe.txt', 'no', False, 'a recipe',
     'Bengali fish curry\n\nRub 500 g of rohu with turmeric and salt. Fry lightly. Temper mustard oil with nigella '
     'and green chillies, add a paste of mustard seeds, simmer the fish for 8 minutes.\n'),
    ('Reports/heatwave_health.pdf', 'no', False, 'heat and public health',
     ['Heatwave action plan, Nagpur', 'Days above 45 degrees rose from 4 to 11 a year.',
      'Cooling centres, water points and work-hour changes cut heat admissions by a third.']),
    ('Grants/livelihoods_buffer_zone.docx', 'no', True, 'a livelihood project that only sits near a tiger reserve',
     ['Proposal: tailoring and millet processing for 60 women',
      'The villages lie in the buffer zone of the Melghat Tiger Reserve, 40 km from the nearest town.',
      'The project trains women in tailoring and sets up two millet mills run by self-help groups.']),
    ('Collections/museum_extinct_specimens.csv', 'no', True, 'extinct species in a museum, not endangered',
     [['specimen', 'species', 'status', 'acquired'], ['M-001', 'Dodo (Raphus cucullatus)', 'Extinct', 1898],
      ['M-002', 'Pink-headed duck', 'Extinct (last seen 1949)', 1925], ['M-003', 'Passenger pigeon', 'Extinct', 1910]]),
    ('Admin/library_red_list.txt', 'no', True, 'a "red list" of overdue books',
     'Library red list (books overdue more than 60 days)\n\n1. "Wings of Fire", issued to R. Das\n'
     '2. "The Hungry Tide", issued to M. Khan\n3. "Field Guide to Indian Birds", issued to A. Menon\n'),
    ('Finance/voucher_codes.xlsx', 'no', True, 'CR, EN, VU here are accounting codes',
     [['Code', 'Meaning', 'Count', 'Amount'], ['CR', 'Credit note', 14, 22000], ['EN', 'Entry adjustment', 3, 4100],
      ['VU', 'Voucher', 61, 190500], ['LC', 'Late charge', 2, 600]]),
    ('Comms/bengal_tigers_rugby.pdf', 'no', True, 'a sports team called the Bengal Tigers',
     ['Bengal Tigers win the inter-college rugby cup',
      'The Bengal Tigers beat the Deccan Chargers 24 to 17 in Pune on Sunday. Captain Rohit Sen scored twice.']),
]


def write(rel, content, tmp):
    p = DATA / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    ext = p.suffix
    if ext in ('.txt', '.py'):
        p.write_text(content)
    elif ext == '.csv':
        with open(p, 'w', newline='') as f:
            csv.writer(f).writerows(content)
    elif ext == '.xlsx':
        wb = openpyxl.Workbook()
        for row in content:
            wb.active.append(row)
        wb.save(p)
    elif ext in ('.docx', '.pdf'):
        d = docx.Document()
        d.add_heading(content[0], level=1)
        for para in content[1:]:
            d.add_paragraph(para)
        if ext == '.docx':
            d.save(p)
        else:
            src = Path(tmp) / (p.stem + '.docx')
            d.save(src)
            subprocess.run(['soffice', '--headless', '--convert-to', 'pdf', '--outdir', tmp, str(src)],
                           check=True, capture_output=True)
            shutil.move(Path(tmp) / (p.stem + '.pdf'), p)
    else:
        raise ValueError(rel)


def main():
    if DATA.exists():
        shutil.rmtree(DATA)
    with tempfile.TemporaryDirectory() as tmp:
        for rel, *_ , content in ITEMS:
            write(rel, content, tmp)
    labels = [{'path': rel, 'expected': exp, 'hard': hard, 'why': why} for rel, exp, hard, why, _ in ITEMS]
    (HERE / 'labels.json').write_text(json.dumps(labels, indent=1) + '\n')
    n = len(labels)
    print(f'{n} items: {sum(l["expected"] == "yes" for l in labels)} yes, '
          f'{sum(l["expected"] == "no" for l in labels)} no, {sum(l["hard"] for l in labels)} hard')


if __name__ == '__main__':
    main()
