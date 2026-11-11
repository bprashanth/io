"""Offline E3 reference audit. Run with cowork/.venv/bin/python; writes only refcheck.md.

Raw = pandas at the detected header; cleaned = chartkit.tables with a saved taught
skill. Intended answers additionally follow the owner's readable-value policy.
No fixture values are replaced with the manifest's pre-injection originals.
"""
import json
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
COWORK = ROOT.parent / '2026-11-06-oss-desktop-independent/cowork'
sys.path.insert(0, str(COWORK))
import pandas as pd
from lib import chartkit, filekit as fk, fixkit


def load(path):
    return json.loads(path.read_text())


def numeric(s):
    return pd.to_numeric(s, errors='coerce')


def counts(df, group, hit, valid=None, money=False):
    d = pd.DataFrame({'group': df[group] if group else 'All', 'hit': hit}, index=df.index)
    if valid is not None:
        d = d[valid]
    out = []
    for g, part in d.groupby('group', dropna=False, sort=True):
        name = '(unknown)' if pd.isna(g) else str(g)
        n = float(part.hit.sum()) if money else int(part.hit.sum())
        den = len(part)
        out.append((name, n, den, n if money else 100 * n / den))
    return out


def fmt(groups, money=False):
    return '; '.join(f'{g}: {n:g}/{d}' + (f' = Rs {v:,.0f}' if money else f' = {v:.2f}%')
                     for g, n, d, v in groups)


def refs(groups):
    return [round(g[3], 2) for g in groups if g[0] != '(unknown)']


def size(s, old=False):
    return s.map(lambda x: None if pd.isna(x) else
                 'Small' if (x <= 10 if old else x < 10) else 'Medium' if x <= 30 else 'Large')


def aggregate(chat, df, intended=False):
    df = df.copy()
    if 'tree-canopy-size' in chat:
        df['size'] = size(numeric(df.dbh_1_cm))
        return counts(df, 'size', df.canopy_y_n.eq('Y'), df['size'].notna())
    if 'tree-recorder' in chat:
        return counts(df, None, df.canopy_y_n.eq('Y'), df.canopy_y_n.isin(['Y', 'N']))
    if 'village-debt' in chat:
        x = numeric(df.debts_inr)
        return counts(df, 'village', x.gt(0), x.notna())
    if 'ward-land' in chat:
        x = numeric(df.land_acres)
        return counts(df, 'ward', x.gt(1), x.notna())
    if 'germination' in chat:
        x = numeric(df.germination_success)
        threshold = 80 if chat.endswith('odd') else 70
        return counts(df, None, x.gt(threshold), x.between(0, 100))
    status = df.status_done_follow_up_cancelled.fillna('').astype(str).str.strip().str.lower()
    cancelled = status.isin(['cancelled', 'cancel']) if intended else status.eq('cancelled')
    if 'village-chart' in chat:
        x = numeric(df.amount_disbursed_rs)
        return counts(df, 'officer_district', x, ~cancelled & x.notna(), money=True)
    return counts(df, 'officer_district' if 'district' in chat else None, cancelled)


def data(c):
    stem, chat = c['ref_file'], c['id']
    skills = sorted(ROOT.glob(f'results/e3-logs/*/{chat}/teach/*/skill/skill.json'))
    p = skills[0] if skills else ROOT / f'results/e6/fake/{stem}/skill/skill.json'
    skill = load(p)
    skill['_dir'] = str(p.parent)
    path = ROOT / f'fixtures/{stem}.xlsx'
    tables = chartkit.tables(str(path), skill)
    tab = next(iter(tables))
    cleaned = tables[tab].copy()
    sheets, headers = fk.raw_sheets(str(path), preserve_na=True)
    source = sheets[tab]
    kept = fixkit.keep_rows(source, skill['tabs'][tab])
    assert len(kept) == len(cleaned), 'Row alignment changed'
    cleaned.index = [fk.sheet_row(kept, i, headers[tab]) for i in range(len(kept))]
    raw = pd.read_excel(path, sheet_name=tab, header=headers[tab] - 1)
    raw.index = range(headers[tab] + 1, headers[tab] + 1 + len(raw))
    raw.columns = [fk.slug(col) for col in raw.columns]
    if stem == 'field_visits_messy':
        officers = pd.read_excel(path, sheet_name='Officers').set_index('Name').District
        raw['officer_district'] = raw.field_officer.map(officers)
    policy = cleaned.copy()
    if stem == 'tree_plots_transects':
        # The SQL cleaner drops cm suffixes. Read the three unambiguous measurements.
        for row in policy.index:
            value = str(raw.loc[row, 'dbh_1_cm']).strip()
            if re.fullmatch(r'\d+(?:\.\d+)?\s*cm', value):
                policy.loc[row, 'dbh_1_cm'] = float(re.search(r'\d+(?:\.\d+)?', value)[0])
    if stem == 'germination_protocol_filled':
        # chartkit currently retains the two template instruction rows.
        policy = policy[numeric(policy.no).notna()]
    return raw, cleaned, policy, p, tab


REASONS = {
 'e3-tree-canopy-size': 'Wrong boundary and dropped units; Small <10, Medium 10–30, Large >30.',
 'e3-tree-recorder-canopy': 'Right: 608/888 trees, layout excluded.',
 'e3-household-village-debt': 'Wrong: casing merges Pudur, Metu remains separate; unknown debt excluded and disclosed.',
 'e3-household-ward-land': 'Right: all records retained; no authority to delete repeated IDs.',
 'e3-field-village-chart': 'No numeric ref; district disbursement chart required.',
 'e3-field-district-cancel': 'Wrong under readable-status policy: cancel is Cancelled (District 2).',
 'e3-field-officer-cancel': 'Wrong: total row excluded; cancel included.',
 'e3-germination-summary': 'Wrong: use valid scalar percentages and strict >70; charts use ≥70.',
 'e3-germination-odd': 'Wrong: use valid scalar percentages and strict >80; charts use ≥80.',
}


def verdict(row, corrected):
    chat, run = row['chat'], row['run']
    if row['answered_how'] != 'chart':
        return 'FAIL: no chart/answer'
    if 'village-chart' in chat:
        return 'PASS chart requirement; amount wrong: District 2 Rs 60,100 vs 59,550 (cancel not excluded)'
    if 'tree-recorder' in chat:
        if run.endswith('9b-r0'):
            return 'FAIL: plot/origin breakdown, no overall share'
        return ('PASS: overall reference line' if run.endswith('9b-r1') else
                'PASS: overall value in title; equal transect bars also match (not chance)')
    if 'field-officer' in chat:
        return ('FAIL labels: Cancelled=33.2%, cancel=0.4%; unrelated Done=33.6% matches'
                if not run.endswith('9b-r1') else
                'FAIL: Cancelled=33.2%, separate cancel=0.4%; 34% is another status')
    if 'district-cancel' in chat:
        return 'FAIL: status chart splits cancel (1/83) from Cancelled; old numeric pass is incomplete'
    if 'village-debt' in chat:
        return 'FAIL: deletes rows 3,43,83 (repeated IDs); numeric tolerance hides Pudur error'
    if 'ward-land' in chat and run == 'muse30b-r0':
        return 'FAIL: deletes rows 3,43,83; wrong ward denominators'
    if 'germination' in chat:
        return 'FAIL: ≥ instead of > (≥ alternative would pass)'
    if 'tree-canopy-size' in chat:
        return 'PASS within 0.6; exact Medium is low by 0.315pp (12 cm dropped)'
    ok = all(any(abs(v - g) <= .6 for g in row['got']) for v in corrected)
    return 'PASS' if ok else 'FAIL: corrected numbers absent'


def main():
    scenarios = load(ROOT / 'scenarios/e3.json')['conversations']
    runs = load(ROOT / 'results/e3/rescore.json')
    lines = ['# E3 reference check', '',
        'Offline; regenerated by `harness/e3_refcheck.py` with the cowork venv. '
        'R0/R1 = local-qwen35-9b-r0/r1; M = muse30b-r0. Missing runs are absent from rescore.json.', '',
        'Conventions: percentages use readable observations (unknown debts excluded, not treated as zero); '
        'retain repeated records unless the owner authorizes deletion; retain Metu separately because no skill maps it to Mettu. '
        '“Clear” is interpreted as strict >, consistent with the old germination refs. '
        'Use the control question’s valid_pct (0–100 scalar) population there. '
        'These choices are stated because the hard questions alone do not specify unknown-value denominators or threshold inclusivity.', '',
        'The generator log contains no reference code. Reconstructions below reproduce the old numbers but are inferences, not recovered source. '
        'Raw pandas means read_excel at the actual header (row 8 for germination); blank/layout rows remain. '
        'Cleaned means the actual chartkit.tables result, before chart-specific filters. '
        'Intended adds the owner policy where the current cleaner falls short. Counts are numerator/denominator; '
        'disbursement uses rupee sum/visit count. Unknown district is shown separately and omitted from numeric lists.', '']
    summaries = []
    seen_stems = set()
    for c in scenarios:
        chat = c['id']
        raw, clean, policy, skill, tab = data(c)
        a, b, intended = aggregate(chat, raw), aggregate(chat, clean), aggregate(chat, policy, True)
        corrected = refs(intended)
        # Size classes follow the taught order, rather than alphabetical order.
        if 'tree-canopy-size' in chat:
            corrected = [round(next(v for g, n, d, v in intended if g == k), 2)
                         for k in ['Small', 'Medium', 'Large']]
        old = c['steps'][5]['check'].get('ref', {}).get('numbers', [])
        money = 'village-chart' in chat
        lines += [f'**{chat}** — {c["steps"][3]["user"]}', '',
                  f'Skill: `{skill.parent.relative_to(ROOT)}`; tab `{tab}`.', '',
                  f'Raw: {fmt(a, money)}.  ', f'Cleaned: {fmt(b, money)}.  ',
                  f'Intended: {fmt(intended, money)}.', '']
        if 'tree' in chat:
            if 'size' in chat:
                # Inferred old recipe: parse cm, but use right-closed size bins.
                old_df = policy.copy()
                old_df['size'] = size(old_df.dbh_1_cm, old=True)
                old_groups = counts(old_df, 'size', old_df.canopy_y_n.eq('Y'), old_df['size'].notna())
                assert sorted(refs(old_groups)) == sorted(old)
                lines += [f'Old ref reconstruction: parse cm, then ≤10 / (10,30] / >30: {fmt(old_groups)}. '
                          'The taught skill instead specifies <10 / [10,30] / >30.', '']
            else:
                assert round(100 * 608 / 888, 2) == old[0]
                lines += ['Old ref reconstruction: count Y among Y/N records, 608/888 = 68.47%.', '']
            layout = sorted(set(raw.index) - set(clean.index))
            units = list(raw.index[raw.dbh_1_cm.astype(str).str.contains('cm', na=False) & raw.canopy_y_n.isin(['Y','N'])])
            blanks = list(raw.index[raw.dbh_1_cm.isna() & raw.canopy_y_n.isin(['Y','N'])])
            tens = list(raw.index[numeric(raw.dbh_1_cm).eq(10)])
            lines += [f'Rows: excluded raw layout/blank rows {layout}; DBH units at {units} are "12 cm", '
                      f'currently NULL in chartkit, intended 12; missing DBH at {blanks} stays unknown. '
                      f'DBH exactly 10 at {tens} moves from old Small to taught Medium. '
                      'All 888 Y/N records remain for overall canopy; duplicates and unrelated validation errors do not remove trees.', '']
        elif 'household' in chat:
            if 'debt' in chat:
                lines += ['Old ref reconstruction: four canonical villages Anaikatti/Kallar/Mettu/Pudur, '
                          '85/100, 83/100, 86/100, 86/100; requires merging Metu into Mettu and casing into Pudur, '
                          'and treating three unknown debts as non-positive. Raw pandas alone does not yield four groups.', '']
            else:
                assert refs(intended) == old
                lines += ['Old ref reconstruction: `(Land > 1).mean()` by Ward 1–6, all 400 records.', '']
            lines += ['Rows: village casing 11 (pudur), 51 (PUDUR), 91 (pudur) becomes Pudur; '
                      '12/52/92 are Metu and remain distinct from Mettu. Debt 6="n/a", 46="pending", 86="-" '
                      'becomes NULL (raw pandas also loses n/a); omit these three only for debt-rate denominators. '
                      'Repeated ID pairs 2/3, 42/43, 82/83 are retained: different villages/measurements do not establish which household is a duplicate. '
                      'Land has no missing/unreadable values. Muse ward chart wrongly drops rows 3/43/83: '
                      'ward 2 becomes 34/66, ward 4 33/66, ward 6 33/65.', '']
        elif 'field' in chat:
            if 'officer' in chat:
                assert round(100 * 83 / 251, 2) == old[0]
                lines += ['Old ref reconstruction: 83 exact Cancelled / 251 nonblank rows, including the Total row = 33.07%.', '']
            elif 'district' in chat:
                lines += ['Old ref reconstruction: exact Cancelled counts District 1 0/81, District 2 0/83, District 3 83/83; unknown district omitted.', '']
            else:
                lines += ['Old ref: chart_show only; no numeric reference. Intended totals use the skill’s default exclusion of cancelled visits.', '']
            lines += ['Rows: 255 is Total (Rs 121,300), not a visit; fully empty rows 63/134/205 are also absent from chartkit. '
                      'Row 3 done is readable Done; row 33 Completed is readable Done; row 64 cancel is readable Cancelled '
                      '(Officer H, District 2). The current skill has no status normalization. '
                      'Rows 2/32/62 have Offcer A/B/C, unmatched lookup, hence unknown district (0/3 cancellations); '
                      'no automatic spelling repair assumed. Row 255 has no officer. '
                      'Rupee strings at 5/35/66 (1,200/2,000/900) are parsed by chartkit; raw pandas coercion loses them. '
                      'The overall intended rate is 84/250; exact-label cleaned rate is 83/250.', '']
        else:
            threshold = 80 if chat.endswith('odd') else 70
            n = int(numeric(raw.germination_success).gt(threshold).sum())
            assert round(100 * n / 60, 2) == old[0]
            lines += [f'Old ref reconstruction: numeric success >{threshold}, {n}/60 actual protocol rows '
                      '(includes impossible percentages as successes; unknown values count against all 60).', '',
                      'Rows: header is 8; metadata 1–7 is not data. Instruction rows 9/10 survive chartkit but '
                      'are not protocols. Protocol rows are 11–70 (60 records). '
                      'Exclude success 16=120, 34=-5, 52=140 (out of range), 21=good, 39=70-80%, 57=excellent '
                      '(no valid scalar percentage): 54 readable valid observations. '
                      'Do not restore manifest original values. Missing names, repeated species names, storage n/a, casing, '
                      'seed depth units and duration units do not change these success counts.', '',
                      'Threshold/denominator sensitivity: valid observations with ≥70 give 36/54=66.67%, ≥80 18/54=33.33%; '
                      'strict >70 gives 35/54=64.81%, >80 16/54=29.63%. If the owner instead wants all 60 protocols '
                      'as denominator, valid strict successes are 35/60=58.33% and 16/60=26.67%, with six unknown/invalid outcomes disclosed. '
                      'The 70–80% range is not converted to an invented scalar.', '']
        per_run = []
        for row in runs:
            if row['chat'] != chat:
                continue
            label = {'local-qwen35-9b-r0': 'R0', 'local-qwen35-9b-r1': 'R1', 'muse30b-r0': 'M'}.get(row['run'], row['run'])
            v = verdict(row, corrected)
            per_run.append(f'{label}: {v}')
        # Keep shared workbook row evidence once, with an explicit cross-reference.
        if c['ref_file'] in seen_stems:
            for i in range(len(lines) - 1, -1, -1):
                if lines[i].startswith('Rows:'):
                    lines[i] = 'Rows: same workbook row differences detailed under the earlier chat above.'
                    break
        seen_stems.add(c['ref_file'])
        lines += ['Runs: ' + '; '.join(per_run) + '.', '']
        old_text = str(old) if old else 'chart_show'
        new_text = str(corrected) if not money else 'chart_show; Rs ' + ', '.join(f'{v:g}' for v in corrected)
        summaries.append([chat, c['steps'][3]['user'], old_text, new_text, REASONS[chat], '; '.join(per_run)])
    lines += ['Numeric tolerance remains 0.6 percentage points, but a matching unrelated bar is not an answer. '
              'Large-pass audit: overall status charts do answer the requested overall dimension, but split readable synonyms; '
              'district status stacks likewise need normalization. Tree R1 explicitly marks the overall share; '
              'Muse states it in the title (rounded), and identical transect shares are an actual property of these fixtures. '
              'Muse’s village-chart display is supported by saved code and chart_show title despite rescore’s missing-code error; its amounts still fail the readable-status policy.', '',
              '| chat | question | old ref | corrected ref | reason | per-run verdicts |',
              '| --- | --- | --- | --- | --- | --- |']
    lines += ['| ' + ' | '.join(x.replace('|', '\\|') for x in row) + ' |' for row in summaries]
    out = ROOT / 'results/e3/refcheck.md'
    out.write_text('\n'.join(lines) + '\n')
    print('\n'.join(lines[-11:]))


if __name__ == '__main__':
    main()
