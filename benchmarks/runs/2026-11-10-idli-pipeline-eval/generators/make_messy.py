#!/usr/bin/env python3
"""Deterministic, invented spreadsheet fixtures and independently checkable manifests.

Run from generators/: python make_messy.py --out ../fixtures --manifests ../manifests
Use --check with the same paths to verify the saved workbooks, without regenerating.
All dates are synthetic strings; the fixed survey cutoff is 31 March 2024.
"""
import argparse
import calendar
from collections import Counter
from datetime import date, datetime, timedelta
import json
from pathlib import Path
import random
import re
import sys
import zipfile

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

SEED = 731942
CUTOFF = '31/03/2024'
VILLAGES = ['Kallar', 'Pudur', 'Mettu', 'Anaikatti']
SPECIES = [('cesaur', 'Cestrum aurantiacum', 'Orange shrub', 'Alien'),
           ('syzcum', 'Syzygium cumini', 'Jamun', 'Native'),
           ('ficben', 'Ficus benghalensis', 'Banyan', 'Native'),
           ('acamea', 'Acacia mearnsii', 'Wattle', 'Alien'),
           ('litflo', 'Litsea floribunda', 'Laurel', 'Native'),
           ('olepan', 'Olea paniculata', 'Olive', 'Native'),
           ('permac', 'Persea macrantha', 'Bay', 'Native')]
KINDS = set('repeated_header subheading total notes_row spacer merged_header info_block '
            'unit_in_cell na_text mixed_date_format bad_date future_date code_typo '
            'code_not_in_key team_code casing out_of_range duplicate_id required_missing '
            'not_a_number bad_phone bad_email dbh2_without_dbh1 count_mismatch '
            'key_missing_species total_mismatch end_before_start'.split())


def day(i):
    return (date(2023, 4, 1) + timedelta(days=i % 360)).strftime('%d/%m/%Y')


class Fixture:
    def __init__(self, stem):
        self.stem = stem
        self.wb = Workbook()
        self.wb.remove(self.wb.active)
        self.manifest = {'file': stem + '.xlsx', 'data_rows': {}, 'items': [],
                         'seed': SEED, 'reference_date': '2024-03-31',
                         'headers': {}, 'record_rows': {}}
        self.claimed = set()

    def sheet(self, name, headers, header_row=1):
        ws = self.wb.create_sheet(name)
        for col, value in enumerate(headers, 1):
            ws.cell(header_row, col, value)
        self.manifest['headers'][name] = {'row': header_row, 'values': headers}
        self.manifest['record_rows'][name] = []
        self.manifest['data_rows'][name] = 0
        ws.freeze_panes = f'A{header_row + 1}'
        return ws

    def record(self, ws, values):
        ws.append(values)
        self.manifest['record_rows'][ws.title].append(ws.max_row)
        self.manifest['data_rows'][ws.title] += 1
        return ws.max_row

    def item(self, ws, row, column, category, kind, original, injected,
             fix=None, expect='flag', in_doc=True, **extra):
        obj = dict(id=f'm{len(self.manifest["items"]) + 1:03d}', tab=ws.title,
                   row=row, column=column, category=category, kind=kind,
                   expect=expect, in_doc=in_doc, original=original,
                   injected=injected, fix=fix)
        obj.update(extra)
        self.manifest['items'].append(obj)
        return obj

    def change(self, ws, row, column, value, kind, category='value',
               in_doc=True, expect='flag', columns=None, **extra):
        headers = self.manifest['headers'][ws.title]['values']
        col = headers.index(column) + 1
        key = (ws.title, row, col)
        if key in self.claimed:
            raise ValueError(f'Overlapping injections: {key}')
        self.claimed.add(key)
        old = ws.cell(row, col).value
        if old == value:
            raise ValueError(f'Injection did not change {key}')
        ws.cell(row, col).value = value
        if columns:
            extra['columns'] = columns
        return self.item(ws, row, column, category, kind, old, value,
                         old if expect == 'flag' else value, expect, in_doc, **extra)

    def layout(self, ws, kind, values, row=None, merges=()):
        row = row or ws.max_row + 1
        width = max(len(values), len(self.manifest['headers'][ws.title]['values']))
        for col, value in enumerate(values, 1):
            ws.cell(row, col, value)
        # Materialize even a fully empty spacer row.
        ws.cell(row, width)
        for merge in merges:
            ws.merge_cells(merge)
        snapshot = [ws.cell(row, col).value for col in range(1, width + 1)]
        self.item(ws, row, '(whole row)', 'layout', kind, None, snapshot,
                  expect='skip', merged_ranges=list(merges))
        return row

    def save(self, out, manifests, documentation):
        for ws in self.wb:
            hrow = self.manifest['headers'][ws.title]['row']
            for row in ws:
                for cell in row:
                    cell.font = Font(name='Arial', size=10)
                    cell.alignment = Alignment(vertical='top', wrap_text=True)
                    if cell.row == hrow:
                        cell.font = Font(name='Arial', size=10, bold=True, color='FFFFFF')
                        cell.fill = PatternFill('solid', fgColor='28546A')
            for col in range(1, ws.max_column + 1):
                ws.column_dimensions[get_column_letter(col)].width = 23
            ws.sheet_view.showGridLines = False
        self.wb.properties.creator = 'Synthetic field team'
        self.wb.properties.created = self.wb.properties.modified = datetime(2024, 4, 1)
        target = out / self.manifest['file']
        self.wb.save(target)
        # Normalize ZIP metadata too, so two generations are byte-for-byte identical.
        with zipfile.ZipFile(target) as archive:
            entries = [(info.filename, archive.read(info.filename)) for info in archive.infolist()]
        with zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED) as archive:
            for name, content in entries:
                if name == 'docProps/core.xml':
                    # openpyxl overrides modified during save, after properties are set.
                    content = re.sub(rb'(<dcterms:modified[^>]*>)[^<]+',
                                     rb'\g<1>2024-04-01T00:00:00Z', content)
                info = zipfile.ZipInfo(name, (2024, 4, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                archive.writestr(info, content)
        (manifests / (self.stem + '.json')).write_text(
            json.dumps(self.manifest, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
        (out / (self.stem + '.doc.md')).write_text(documentation.strip() + '\n', encoding='utf-8')


def tree_fixture(out, manifests):
    f = Fixture('tree_plots_transects')
    headers = ['Transect', 'Plot', 'Tree No', 'Species code', 'DBH 1 (cm)', 'DBH 2 (cm)',
               'DBH 3 (cm)', 'Height (m)', 'Canopy (Y/N)', 'Notes', 'Date (dd/mm/yyyy)', 'Recorder']
    raw = f.sheet('Raw 10x10m Data', headers)
    density = f.sheet('Density', ['Transect', 'Plot', 'No. of trees', 'No. of Cestrum'])
    seedlings = f.sheet('Seedlings', ['Transect', 'Plot', 'Species code', 'Count', 'Height class'])
    key = f.sheet('Species key', ['Code', 'Scientific name', 'Common name', 'Native/Alien'])
    rng = random.Random(SEED)
    rows, plots = [], []
    for t in range(1, 9):
        if t > 1:
            f.layout(raw, 'repeated_header', headers)
        if t % 2 == 0:
            f.layout(raw, 'subheading', [f'Transect {t}'])
        for p in range(1, 6):
            n = 23 if p == 1 else 22  # 111 per transect; 888 trees.
            codes = []
            for i in range(1, n + 1):
                code = SPECIES[(i + t + p) % len(SPECIES)][0]
                codes.append(code)
                rows.append(f.record(raw, [f'T{t}', p, i, code, round(rng.uniform(5, 65), 1),
                            8.5 if i % 9 == 0 else None, None, round(rng.uniform(2, 24), 1),
                            'Y' if i % 3 else 'N', None, day(i + t), f'Recorder {t}']))
            plots.append(f.record(density, [f'T{t}', p, n, codes.count('cesaur')]))
            f.record(seedlings, [f'T{t}', p, 'cesaur', 4 + p, '<10cm'])
            f.record(seedlings, [f'T{t}', p, 'syzcum', 2 + p, '10-50cm'])
        if t % 2 == 0:
            f.layout(raw, 'spacer', [])
            f.layout(raw, 'notes_row', ['Field team note: shade measurements were taken at noon.'])
    for species in SPECIES:
        f.record(key, list(species))
    # Accepted team codes are deliberately distinct from the formal key.
    for j in range(3):
        base = j * 35
        changes = [(0, 'DBH 1 (cm)', '12 cm', 'unit_in_cell', False),
                   (1, 'Height (m)', 'n/a', 'na_text', False),
                   (2, 'Species code', 'cesaurx', 'code_typo', True),
                   (3, 'Species code', f'novel{j}', 'code_not_in_key', True),
                   (4, 'Species code', ['UKS1', 'Fern', 'UKS1'][j], 'team_code', True),
                   (5, 'Species code', ['CESAUR', 'cesaur ', 'CesaUr'][j], 'casing', True),
                   (6, 'DBH 1 (cm)', 900, 'out_of_range', True),
                   (7, 'Date (dd/mm/yyyy)', '2023-05-12', 'mixed_date_format', False),
                   (8, 'Date (dd/mm/yyyy)', '31/02/2024', 'bad_date', True)]
        for offset, col, value, kind, documented in changes:
            f.change(raw, rows[base + offset], col, value, kind, in_doc=documented,
                     expect='ok' if kind == 'team_code' else 'flag')
        # Select a clean existing second-stem tree and remove its first measurement.
        r = rows[base + 17]
        if raw.cell(r, 6).value is None:
            r = next(x for x in rows[base + 10:base + 34] if raw.cell(x, 6).value)
        f.change(raw, r, 'DBH 1 (cm)', None, 'dbh2_without_dbh1', 'cross',
                 columns=['DBH 1 (cm)', 'DBH 2 (cm)'])
        r = rows[150 + j * 25 + 1]
        previous = rows[150 + j * 25]
        f.change(raw, r, 'Tree No', raw.cell(previous, 3).value, 'duplicate_id',
                 columns=['Transect', 'Plot', 'Tree No'])
        dr = plots[j * 7]
        f.change(density, dr, 'No. of trees', density.cell(dr, 3).value + 7,
                 'count_mismatch', 'cross', columns=['Transect', 'Plot', 'No. of trees'],
                 related_tab=raw.title)
    # Remove the last three key records; each is used repeatedly in clean tree data.
    # The manifest captures the actual deleted cells, including names and origin.
    for r in (8, 7, 6):
        original = [key.cell(r, c).value for c in range(1, 5)]
        key.delete_rows(r)
        f.manifest['record_rows'][key.title].remove(r)
        f.manifest['data_rows'][key.title] -= 1
        f.item(key, r, 'Code', 'cross', 'key_missing_species', original[0], None,
               original[0], removed_key_row=original, related_tab=raw.title,
               related_column='Species code')
    f.save(out, manifests, '''# Tree plots and transects — team handover
We count each standing tree once in a 10 × 10 m plot. Raw 10x10m Data has one tree per record;
Transect, Plot and Tree No together identify it uniquely. Transects are T1–T8 and plots are 1–5.
Species code identifies the taxon; DBH 1, 2 and 3 are stem diameters in centimetres (0–250),
Height is in metres (0–60), Canopy is Y or N, Notes is optional field context, Date is the
observation date (dd/mm/yyyy), and Recorder is the invented team label. Dates must be valid and
no later than 31 March 2024. A second stem requires DBH 1; a third requires DBH 1 and DBH 2.
Use canonical lower-case species codes exactly as in Species key. UKS1 (unidentified) and Fern
are accepted special team codes and do not need key entries.

Density has one row per Transect and Plot: No. of trees must equal the raw records in that plot,
and No. of Cestrum counts cesaur trees. Seedlings has one species and height-class count per
plot: Count is a nonnegative integer and Height class is <10cm, 10-50cm or >50cm. Species key
has one Code, Scientific name, Common name and Native/Alien classification per formal taxon.
Every formal species used in trees or seedlings must have a key entry. Section headings,
repeated column headings, blank separators and prose notes are navigation, not observations.
These are invented training data; all names, measurements and plot assignments are synthetic.
''')


def germination_fixture(out, manifests):
    f = Fixture('germination_protocol_filled')
    headers = ['No.', 'Scientific Name (Botanical)', 'Local / Common name(s)',
               'Time of year for seed collection', 'Processing of fruits/seeds', 'Seed storage',
               'Seed treatment', 'Seed sowing media', 'Container (germination)', 'Seed depth',
               'Germination facilities / Nursery Care', 'Duration until germination',
               '% Germination success', 'Growing media', 'Container', 'Watering technique']
    ws = f.sheet('Germination', headers, 8)
    labels = ['GENERAL INFORMATION', 'Nursery Name', 'About your nursery, project, organisation',
              'Ecoregion(s) you serve', 'Contact Person(s) of nursery, propagation experts (email / phone number)']
    answers = ['Synthetic propagation register', 'Mettu Seed House', 'Invented restoration training project',
               'Invented upland woodland', 'Person A: a@example.invalid / 9000000001; '
               'Person B: b@example.invalid / 9000000002; Person C: c@example.invalid / 9000000003']
    for r, (label, answer) in enumerate(zip(labels, answers), 1):
        f.layout(ws, 'info_block', [None, label, None, answer], row=r)
    f.layout(ws, 'merged_header', [None, 'SPECIES', None, 'SEED PROCESSING', None, None,
             'GERMINATION', None, None, None, None, None, None, 'FIRST TRANSPLANT'], row=6,
             merges=['B6:C6', 'D6:F6', 'G6:M6', 'N6:P6'])
    f.layout(ws, 'merged_header', [None] * 6 + ['Procedures'] + [None] * 4 + ['Success', None, 'Procedures'],
             row=7, merges=['G7:K7', 'L7:M7', 'N7:P7'])
    descriptions = ['Sequential protocol number', 'Accepted binomial species name', 'Local name used by team',
                    'Collection month or season', 'Cleaning and fruit removal method', 'Storage method and conditions',
                    'Pretreatment before sowing', 'Substrate used for sowing', 'Type of germination container',
                    'Sowing depth in centimetres', 'Shade, humidity and care instructions',
                    'Elapsed days from sowing to emergence', 'Percent of seeds germinated, number from 0 to 100',
                    'Transplant substrate', 'Transplant container', 'Watering method after transplant']
    f.layout(ws, 'notes_row', descriptions, row=9)
    mandatory = {2, 5, 7, 8, 9, 12, 13}
    f.layout(ws, 'notes_row', ['MANDATORY' if c in mandatory else 'OPTIONAL' for c in range(1, 17)], row=10)
    genera = ['Ficus', 'Syzygium', 'Litsea', 'Olea', 'Persea', 'Cestrum']
    epithets = ['alba', 'rubra', 'longa', 'brevis', 'montana', 'minor', 'major', 'viridis', 'tenuis', 'rotunda']
    rows = []
    for i in range(60):
        rows.append(f.record(ws, [i + 1, f'{genera[i // 10]} {epithets[i % 10]}', f'Seed plant {i + 1}',
                    'June–August', 'Remove pulp and rinse', 'Dry cool room', 'Soak overnight',
                    'Sand and compost', 'Tray', 1.5, 'Shade; mist daily', 21 + i % 9,
                    60 + i % 35, 'Loam and compost', 'Bag', 'Fine rose']))
    for j in range(3):
        b = j * 18
        for offset, col in enumerate(['Scientific Name (Botanical)', 'Processing of fruits/seeds', 'Seed treatment']):
            f.change(ws, rows[b + offset], col, None, 'required_missing')
        f.change(ws, rows[b + 3], 'Seed depth', ['2cm', 'approx 1 cm', '1 cm'][j], 'unit_in_cell', in_doc=False)
        f.change(ws, rows[b + 4], 'Duration until germination', ['3 weeks', '21 days', '2-3 wk'][j],
                 'unit_in_cell', in_doc=False)
        f.change(ws, rows[b + 5], '% Germination success', [120, -5, 140][j], 'out_of_range')
        f.change(ws, rows[b + 6], 'Seed storage', ['n/a', '-', 'pending'][j], 'na_text', in_doc=False)
        old = ws.cell(rows[b + 7], 2).value
        f.change(ws, rows[b + 7], 'Scientific Name (Botanical)', old.upper(), 'casing')
        f.change(ws, rows[b + 8], 'Scientific Name (Botanical)', ws.cell(rows[b + 9], 2).value, 'duplicate_id')
        f.change(ws, rows[b + 10], '% Germination success', ['good', '70-80%', 'excellent'][j], 'not_a_number')
    # Three email and three phone errors share the specified single contact cell.
    # Represent the atomic cell edit once per kind with explicit constituent details.
    clean_contact = ws['D5'].value
    bad_contact = 'Person A: a@ / 123; Person B: b.example.invalid / 456; Person C: c@@example.invalid / 789'
    ws['D5'] = bad_contact
    # Update the containing layout snapshot so all manifest items describe final cells.
    f.manifest['items'][4]['injected'][3] = bad_contact
    for kind, clean, bad in [('bad_email', ['a@example.invalid', 'b@example.invalid', 'c@example.invalid'],
                             ['a@', 'b.example.invalid', 'c@@example.invalid']),
                            ('bad_phone', ['9000000001', '9000000002', '9000000003'], ['123', '456', '789'])]:
        for index in range(3):
            f.item(ws, 5, 'Contact Person(s) of nursery, propagation experts (email / phone number)',
                   'value', kind, clean_contact, bad_contact, clean_contact,
                   cell='D5', component=index + 1, original_component=clean[index], injected_component=bad[index])
    f.save(out, manifests, '''# Nursery germination protocols — team handover
This is the filled synthetic nursery protocol template. The information block gives our nursery,
purpose, ecoregion and expert contacts. Contacts use valid email addresses and ten-digit phone
numbers. The merged bands group seed processing, germination and first transplant procedures;
the description and MANDATORY/OPTIONAL rows explain the template and are not species records.

Each numbered row is one unique species protocol. Scientific Name is a binomial with a capitalized
genus and lower-case epithet; Local / Common names are optional. Time of year is the collection
season. Processing describes fruit cleaning; Seed storage describes conditions; Seed treatment
is the presowing method. Seed sowing media is the substrate and Container (germination) the vessel.
Seed depth is a numeric depth in cm. Germination facilities / Nursery Care describes shade and
watering. Duration until germination is a numeric number of days. % Germination success is a
numeric percentage on a 0–100 scale. Growing media, Container and Watering technique describe
first transplant care. No. is a sequential identifier. Blank optional fields are fine.

Scientific Name, Processing, Seed treatment, Seed sowing media, Container (germination), Duration
and % success are mandatory. Each scientific name appears once. We use invented training
binomials and common names here; these are examples of how to record protocols, not botanical
or propagation advice. Dates and durations describe synthetic observations only.
''')


def tax_info(f, ws, start):
    # Five fields fit in three rows by using two key/value pairs per row.
    fields = [('Name', 'Person A', 'PAN', 'AAAAA9999A'),
              ('Period', '01 April 2023 to 31 March 2024', 'Financial Year (FY)', '2023-24'),
              ('Assessment Year (AY)', '2024-25', None, None)]
    for r, values in enumerate(fields, start):
        f.layout(ws, 'info_block', [values[0], values[1], None, values[2], values[3]], row=r)


def tax_fixture(out, manifests):
    f = Fixture('tax_missing_info_fake')
    q = f.sheet('Missing Information', ['Sl No', 'Topic', 'Our understanding', 'Your response', 'Amount (INR)'], 7)
    tax_info(f, q, 3)
    for i in range(1, 13):
        f.record(q, [i, f'Invented topic {i}', 'Please confirm the synthetic amount', 'Confirmed', i * 1000])
    bank_headers = ['IFS Code', 'Name of the Bank', 'Type of account', 'Account Number (9 digits or more)',
                    'Savings account interest earned', 'Closing balance as on 31 March 2024', 'Refund account (Y/N)']
    bank = f.sheet('India Bank Account', bank_headers, 7)
    tax_info(f, bank, 2)
    f.layout(bank, 'notes_row', ['Details of all Bank Accounts held in India at any time during the FY'], row=6)
    br = [f.record(bank, [f'FAKE0AB{i:04d}', f'Imaginary Bank {i + 1}', 'Savings', f'00000000{i + 1:04d}',
                          1000 + i * 75, 50000 + i * 1000, 'Y' if i == 0 else 'N']) for i in range(8)]
    for j in range(3):
        f.change(bank, br[j], bank_headers[3], str(1234 + j), 'out_of_range')
        f.change(bank, br[j + 3], 'IFS Code', f'BAD{j}', 'code_typo')
        f.change(bank, br[j], bank_headers[4], f'Rs. {1000 + j * 75:,}', 'unit_in_cell', in_doc=False)
        f.change(bank, br[j + 4], bank_headers[5], ['NA', '-', 'pending'][j], 'na_text', in_doc=False)
    f.change(bank, br[1], 'Refund account (Y/N)', 'Y', 'count_mismatch', 'cross',
             columns=['Refund account (Y/N)'], rule='Exactly one refund account')
    ch = ['Sl No', 'Particulars', 'Type of Asset', 'Date of sale (dd-mmm-yy)', 'Price per unit', 'Currency',
          'No of units', 'Sale consideration', 'Expenses on Transfer', 'Net Sale Consideration (INR)',
          'Date of purchase (dd-mmm-yy)', 'Purchase price per unit', 'Cost of acquisition']
    cap = f.sheet('Capital Gain', ch, 8)
    f.layout(cap, 'merged_header', [None] * 5 + ['Sale details'] + [None] * 6 + ['Purchase details'], row=7,
             merges=['F7:L7', 'M7:Q7'])
    cr = []
    for i in range(15):
        cr.append(f.record(cap, [i + 1, f'Imaginary holding {i + 1}', 'Share', '12-Mar-24', 200 + i, 'INR',
                                10, (200 + i) * 10, 20, (200 + i) * 10 - 20, '12-May-23', 150, 1500]))
    for j in range(3):
        f.change(cap, cr[j], ch[3], '12-Mar-22', 'end_before_start', 'cross', columns=[ch[3], ch[10]])
        f.change(cap, cr[3 + j], ch[9], 123, 'total_mismatch', 'cross', columns=[ch[7], ch[8], ch[9]])
        f.change(cap, cr[6 + j], ch[7], 9999, 'total_mismatch', 'cross', columns=[ch[4], ch[6], ch[7]])
        f.change(cap, cr[9 + j], ch[3], ['2024-03-12', '12/03/2024', '12 March 2024'][j],
                 'mixed_date_format', in_doc=False)
        f.change(cap, cr[12 + j], ch[4], ['many', 'unknown', 'ten'][j], 'not_a_number')
    totals = ['Total'] + [None] * 12
    for col in [7, 8, 9, 10, 13]:
        totals[col - 1] = sum(cap.cell(r, col).value for r in cr)
    f.layout(cap, 'total', totals)
    travel = f.sheet('Travel Calendar', ['Month', 'Non-work/vacation days in India', 'Work days in India'])
    tr = []
    for i in range(12):
        year, month = (2023, i + 4) if i < 9 else (2024, i - 8)
        tr.append(f.record(travel, [date(year, month, 1).strftime('%b %Y'), 8,
                                   calendar.monthrange(year, month)[1] - 8]))
    for j in range(3):
        f.change(travel, tr[j], 'Work days in India', 45 + j, 'out_of_range')
        f.change(travel, tr[j + 4], 'Non-work/vacation days in India', ['n/a', 'NA', '-'][j],
                 'na_text', in_doc=False)
    total = f.layout(travel, 'total', ['Total', 96, sum(travel.cell(r, 3).value for r in tr)])
    f.change(travel, total, 'Work days in India', 999, 'total_mismatch', 'cross',
             columns=['Non-work/vacation days in India', 'Work days in India'])
    f.manifest['items'][-2]['injected'][2] = 999
    f.save(out, manifests, '''# Missing tax information — synthetic team handover
All identities, account numbers, banks and amounts are invented. This is a training questionnaire,
not a filed return. The identity block gives Name, fake PAN, Period, FY and AY; two key/value
pairs share a row where necessary. FY is April 2023–March 2024 and AY is 2024–25.

Missing Information has one question per Sl No. Topic names the issue, Our understanding gives
our working assumption, Your response records confirmation, and Amount is INR. India Bank
Account has one account per row. IFS Code must be four letters, zero, then six alphanumeric
characters. Name of the Bank and Type of account describe the account. Account Number is a
text identifier of at least nine digits; preserve leading zeros. Savings interest and Closing
balance at 31 March 2024 are nonnegative numeric INR. Refund account is Y or N with exactly
one Y across accounts.

Capital Gain has one disposal per Sl No: Particulars identify the holding, Type of Asset gives
its class, sale and purchase dates use dd-mmm-yy, Price per unit and Purchase price per unit
are INR, Currency is INR, and No of units is a positive quantity. Sale consideration equals
Price per unit × No of units. Expenses on Transfer are INR; Net Sale Consideration equals
Sale consideration minus Expenses. Cost of acquisition equals Purchase price per unit × units.
Sale cannot precede purchase. Travel Calendar has one month per row; both India-day columns
are nonnegative integers and their sum cannot exceed the calendar month's days. Total rows
sum the numeric records above, with unavailable values excluded until resolved. Titles,
identity blocks, group bands and totals are not records.
''')


def household_fixture(out, manifests):
    f = Fixture('household_survey_messy')
    hh = ['Household ID', 'Village', 'Ward', 'Head of household', 'Phone', 'Members',
          'Monthly income (INR)', 'Debts (INR)', 'Savings (INR)', 'Land (acres)', 'Survey date']
    house = f.sheet('Households', hh)
    members = f.sheet('Members', ['Household ID', 'Name', 'Age', 'Sex', 'Works (Y/N)'])
    hr, mr = [], []
    for i in range(400):
        n = 2 + i % 5
        hid = f'HH{i + 1:04d}'
        hr.append(f.record(house, [hid, VILLAGES[i % 4], i % 6 + 1, f'Person H{i + 1:04d}',
                                  f'90000{i:05d}', n, 8000 + 100 * (i % 80), i % 7 * 1000,
                                  i % 11 * 500, round(i % 8 * .25, 2), day(i)]))
        for j in range(n):
            mr.append(f.record(members, [hid, f'Person H{i + 1:04d} M{j + 1}',
                                         25 + i % 50 if j == 0 else 5 + (i + j) % 70,
                                         'F' if j % 2 else 'M', 'Y' if j == 0 else 'N']))
    for j in range(3):
        base = j * 40
        f.change(house, hr[base + 1], 'Household ID', house.cell(hr[base], 1).value, 'duplicate_id')
        f.change(house, hr[base + 2], 'Phone', ['123', '90000abcde', '+??'][j], 'bad_phone')
        f.change(house, hr[base + 3], 'Monthly income (INR)', ['Rs 8,000', '8k', 'Rs. 12,000'][j],
                 'unit_in_cell', in_doc=False)
        f.change(house, hr[base + 4], 'Debts (INR)', ['n/a', 'pending', '-'][j], 'na_text', in_doc=False)
        f.change(house, hr[base + 5], 'Members', 0, 'out_of_range')
        f.change(house, hr[base + 6], 'Survey date', ['2023-05-12', '12 Mar 2024', '2024-01-10'][j],
                 'mixed_date_format', in_doc=False)
        f.change(house, hr[base + 7], 'Survey date', '15/01/2030', 'future_date')
        f.change(house, hr[base + 8], 'Members', 20, 'count_mismatch', 'cross', related_tab='Members')
        f.change(house, hr[base + 9], 'Village', ['pudur ', 'PUDUR', 'pudur'][j], 'casing', expect='ok')
        f.change(house, hr[base + 10], 'Village', 'Metu', 'code_typo')
        f.change(members, mr[600 + j * 20], 'Age', 140, 'out_of_range')
        f.change(members, mr[700 + j * 20], 'Household ID', f'HHX{j:04d}', 'code_not_in_key',
                 related_tab='Households')
    f.save(out, manifests, '''# Village household survey — team handover
These are invented livelihoods interviews. Households has one row per household, identified by
unique Household ID. Village is one of Kallar, Pudur, Mettu or Anaikatti; differences in case
and surrounding whitespace are accepted. Ward is a positive local ward number. Head of
household is a synthetic person label and Phone is exactly ten digits, stored as text.
Members is the household's positive integer size and must equal the number of Members records
for that Household ID. Monthly income, Debts and Savings are nonnegative numeric INR amounts;
Land is a nonnegative numeric acreage. Survey date uses dd/mm/yyyy and must be a valid date
no later than our fixed reporting cutoff, 31 March 2024.

Members has one person per row, with Household ID linking to an existing household, Name the
invented person label, Age in completed years (0–110), Sex F or M, and Works Y or N. Every
person belongs to exactly one household; each household needs at least one member. Household
counts and the person records should agree before analysing income per capita. Do not infer
real identities from these generated labels. Amounts and dates are entirely synthetic and
exist only to exercise the survey import and review workflow.
''')


def visits_fixture(out, manifests):
    f = Fixture('field_visits_messy')
    vh = ['Visit date', 'Village', 'Field officer', 'Households visited', 'Amount disbursed (Rs)',
          'Status (Done / Follow-up / Cancelled)', 'Notes']
    visits = f.sheet('Visits', vh)
    officers = f.sheet('Officers', ['Name', 'District', 'Phone', 'Email'])
    names = [f'Officer {chr(65 + i)}' for i in range(9)]
    rr = []
    for i, name in enumerate(names):
        rr.append(f.record(officers, [name, f'District {i % 3 + 1}', f'910000000{i}',
                                     f'officer{i}@example.invalid']))
    vr = []
    for i in range(250):
        status = ['Done', 'Follow-up', 'Cancelled'][i % 3]
        vr.append(f.record(visits, [day(i), VILLAGES[i % 4], names[i % 9],
                                   0 if status == 'Cancelled' else i % 12 + 1,
                                   0 if status == 'Cancelled' else 500 + 50 * (i % 10), status, None]))
        if i in (60, 130, 200):
            f.layout(visits, 'spacer', [])
    for j in range(3):
        b = j * 30
        f.change(visits, vr[b], 'Field officer', f'Offcer {chr(65 + j)}', 'code_typo')
        f.change(visits, vr[b + 1], vh[5], ['done', 'Completed', 'cancel'][j], 'casing')
        f.change(visits, vr[b + 3], vh[4], ['Rs. 1,200', 'Rs. 2,000', 'Rs. 900'][j],
                 'unit_in_cell', in_doc=False)
        f.change(visits, vr[b + 4], 'Visit date', '01/06/2030', 'future_date')
        f.change(visits, vr[b + 2], vh[4], 750, 'total_mismatch', 'cross',
                 columns=[vh[4], vh[5]], rule='Cancelled visits disburse zero')
        f.change(officers, rr[j], 'Email', ['a@', 'missing-at.example.invalid', 'a@@b.invalid'][j], 'bad_email')
        f.change(officers, rr[j + 3], 'Phone', ['12', 'phone', '123456789012'][j], 'bad_phone')
    f.layout(visits, 'total', ['Total', None, None,
             sum(visits.cell(r, 4).value for r in vr),
             sum(visits.cell(r, 5).value for r in vr if isinstance(visits.cell(r, 5).value, (int, float)))])
    f.save(out, manifests, '''# Field visits register — team handover
Visits contains one visit per row. Visit date is dd/mm/yyyy, valid and no later than the
fixed reporting cutoff of 31 March 2024. Village names are Kallar, Pudur, Mettu and Anaikatti.
Field officer must match a Name in Officers exactly. Households visited is a nonnegative
integer count; Amount disbursed (Rs) is a nonnegative numeric rupee amount. Status must be
exactly Done, Follow-up or Cancelled, including capitalization. A Cancelled visit must have
zero amount disbursed and zero households visited. Notes is optional free-text field context.
The final total sums counts and numeric disbursements, excluding unavailable values until
resolved; blank separator rows and the total are not visit records.

Officers contains one officer per Name: District is the synthetic service area, Phone is a
text string of exactly ten digits, and Email must have one @ with nonempty local and domain
parts and a dotted domain. All names, districts and contacts are fictional. The reserved
example.invalid domain is deliberate and is acceptable for this training workbook; do not
try to contact these people. This register is designed to teach reconciling recorded visits
with the staff directory and checking status-dependent disbursement rules.
''')


def check(out, manifests):
    paths = sorted(manifests.glob('*.json'))
    expected = {'tree_plots_transects', 'germination_protocol_filled', 'tax_missing_info_fake',
                'household_survey_messy', 'field_visits_messy'}
    errors, verified, seen_kinds = [], 0, set()
    found = {path.stem for path in paths}
    if found != expected:
        errors.append(f'Manifest set differs: missing={sorted(expected - found)}, extra={sorted(found - expected)}')
    for path in paths:
        manifest = json.loads(path.read_text(encoding='utf-8'))
        count, categories, kinds = 0, Counter(), Counter()
        try:
            wb = load_workbook(out / manifest['file'], data_only=False)
            assert (out / (path.stem + '.doc.md')).is_file(), 'Missing documentation'
            for tab, header in manifest['headers'].items():
                ws = wb[tab]
                actual = [ws.cell(header['row'], c).value for c in range(1, len(header['values']) + 1)]
                assert actual == header['values'], f'{tab}: headers differ'
                records = manifest['record_rows'][tab]
                assert len(records) == manifest['data_rows'][tab], f'{tab}: data row count differs'
                assert len(set(records)) == len(records), f'{tab}: duplicate record row coordinates'
                assert all(any(ws.cell(r, c).value is not None for c in range(1, ws.max_column + 1))
                           for r in records), f'{tab}: empty data record'
            ids = set()
            for item in manifest['items']:
                label = f'{path.stem}/{item["id"]}'
                try:
                    assert item['id'] not in ids, 'Duplicate manifest ID'
                    ids.add(item['id'])
                    assert item['kind'] in KINDS, 'Unknown kind'
                    assert item['expect'] in {'flag', 'skip', 'ok'}, 'Invalid expectation'
                    assert isinstance(item['in_doc'], bool), 'in_doc must be boolean'
                    assert item['row'] >= 1, 'Invalid row'
                    ws, row = wb[item['tab']], item['row']
                    if item['category'] == 'layout':
                        assert item['column'] == '(whole row)' and item['fix'] is None
                        assert item['expect'] == 'skip'
                        assert row not in manifest['record_rows'][ws.title], 'Layout counted as data'
                        actual = [ws.cell(row, c).value for c in range(1, len(item['injected']) + 1)]
                        assert actual == item['injected'], f'Layout differs: {actual!r}'
                        for merged in item.get('merged_ranges', []):
                            assert merged in {str(r) for r in ws.merged_cells.ranges}, f'Missing merge {merged}'
                        if item['kind'] == 'spacer':
                            assert all(c.value is None for c in ws[row]), 'Spacer is not empty'
                        if item['kind'] == 'repeated_header':
                            assert actual == manifest['headers'][ws.title]['values'], 'Not a header'
                    else:
                        if 'cell' in item:
                            actual = ws[item['cell']].value
                        else:
                            header = manifest['headers'][ws.title]
                            col = header['values'].index(item['column']) + 1
                            assert ws.cell(header['row'], col).value == item['column']
                            actual = ws.cell(row, col).value
                        assert actual == item['injected'], f'Expected {item["injected"]!r}, got {actual!r}'
                        if item['kind'] == 'team_code':
                            assert item['expect'] == 'ok'
                        if item['kind'] == 'key_missing_species':
                            assert item['original'] not in [ws.cell(r, 1).value for r in
                                                          manifest['record_rows'][ws.title]]
                            related = wb[item['related_tab']]
                            h = manifest['headers'][related.title]['values']
                            col = h.index(item['related_column']) + 1
                            assert sum(related.cell(r, col).value == item['original'] for r in
                                       manifest['record_rows'][related.title]) >= 3
                    count += 1
                except (AssertionError, KeyError, ValueError) as exc:
                    errors.append(f'{label}: {exc}')
                categories[item['category']] += 1
                kinds[item['kind']] += 1
                seen_kinds.add(item['kind'])
            wb.close()
        except (AssertionError, OSError, KeyError, ValueError) as exc:
            errors.append(f'{path.stem}: {exc}')
        verified += count
        rows_text = ', '.join(f'{tab}={n}' for tab, n in manifest['data_rows'].items())
        print(f'{manifest["file"]}: data rows [{rows_text}]')
        print(f'  verified {count}/{len(manifest["items"])} items; categories: ' +
              ', '.join(f'{key}={value}' for key, value in sorted(categories.items())))
        print('  kinds: ' + ', '.join(f'{key}={value}' for key, value in sorted(kinds.items())))
    if KINDS - seen_kinds:
        errors.append('Missing required kinds: ' + ', '.join(sorted(KINDS - seen_kinds)))
    for error in errors:
        print('ERROR: ' + error)
    print(f'CHECK {"FAILED" if errors else "PASSED"}: {len(paths)} files, {verified} manifest items verified, {len(errors)} errors')
    return 1 if errors else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=Path('../fixtures'))
    parser.add_argument('--manifests', type=Path, default=Path('../manifests'))
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    if args.check:
        return check(args.out, args.manifests)
    args.out.mkdir(parents=True, exist_ok=True)
    args.manifests.mkdir(parents=True, exist_ok=True)
    for generator in [tree_fixture, germination_fixture, tax_fixture, household_fixture, visits_fixture]:
        generator(args.out, args.manifests)
    print('Generated 5 deterministic workbooks, 5 documentation files and 5 manifests.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
