#!/usr/bin/env python3
"""Compare fake-copy structure with manifest-described mistakes; no real cells are matched by position.

Run with the cowork venv. E1_FILEKIT_SOURCE optionally tests a staged filekit.py when
sandbox policy prevents installing the accompanying patch in the sibling project.
"""
import argparse
from collections import Counter, defaultdict
import datetime as dt
import json
import math
import os
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
COWORK = ROOT.parent / '2026-11-06-oss-desktop-independent/cowork'
sys.dont_write_bytecode = True
sys.path.insert(0, str(COWORK))
from lib import filekit as fk
if os.environ.get('E1_FILEKIT_SOURCE'):
    # Keep HERE and package imports anchored at the actual cowork installation.
    exec(compile(Path(os.environ['E1_FILEKIT_SOURCE']).read_text(), fk.__file__, 'exec'), fk.__dict__)
import openpyxl
from lib import fixkit

STEMS = ['tree_plots_transects', 'germination_protocol_filled', 'household_survey_messy',
         'field_visits_messy', 'tax_missing_info_fake']
NA = {'na', 'n/a', '-', '--', 'pending', 'tbd', 'none', 'nil', 'not available'}

def text(v):
    return '' if v is None else fk._cell_text(v)

def number(v):
    n = fk.as_number(v)
    return n if n is not None and math.isfinite(n) else None

def date(v):
    for fmt in fk.DATE_FORMATS + ['%d-%b-%y', '%d %B %Y']:
        try:
            return dt.datetime.strptime(v, fmt).date(), fmt
        except ValueError:
            pass
    return None, None

def template(row):
    vals = [v for v in row if v]
    return bool(vals) and all(v.upper() in {'MANDATORY', 'OPTIONAL', 'REQUIRED'} or
                             (len(v.split()) >= 5 and re.match(r'(?i)^(enter|if|describe|list|mention|e\.g\.|provide|select|write|specify|record)\b', v)) for v in vals)

class Book:
    def __init__(self, path, manifest, real=False):
        self.wb = openpyxl.load_workbook(path, data_only=True)
        self.tabs = {}
        for tab, h in manifest['headers'].items():
            ws = self.wb[tab]
            rows = [[text(c.value) for c in row] for row in ws]
            # Find the expected table, independent of filekit's header heuristic.
            scores = [sum(c in row for c in h['values']) for row in rows]
            header = scores.index(max(scores)) if scores and max(scores) >= max(2, len(h['values']) * .6) else None
            cols = {c: rows[header].index(c) for c in h['values'] if header is not None and c in rows[header]}
            body = list(range(header + 1, len(rows))) if header is not None else []
            if real:
                records = [r-1 for r in manifest['record_rows'][tab]]
            else:
                records = [i for i in body if any(rows[i]) and not template(rows[i]) and
                           not re.match(r'(?i)^(total|grand total|heading)\b', next((v for v in rows[i] if v), '')) and
                           sum(v == c for c, v in zip(rows[header], rows[i]) if v) < 2 and
                           sum(bool(v) for v in rows[i]) > 1]
            self.tabs[tab] = dict(ws=ws, rows=rows, header=header, cols=cols, body=body, records=records)
    def vals(self, tab, col, records=True):
        t = self.tabs[tab]
        if col not in t['cols']:
            return []
        return [t['rows'][i][t['cols'][col]] for i in t['records' if records else 'body']]
    def tuples(self, tab, cols):
        return list(zip(*(self.vals(tab, c) for c in cols)))


def count_relation(book, tab, col, other, keys):
    counts = Counter(k for k in book.tuples(other, keys) if all(k))
    vals = book.vals(tab, col)
    pairs = [(number(v), counts[k]) for v, k in zip(vals, book.tuples(tab, keys)) if number(v) is not None and all(k)]
    match = sum(abs(v-n) < 1e-8 for v,n in pairs)
    return {'rows': len(pairs), 'matching': match, 'mismatching': len(pairs)-match,
            'match_share': match/len(pairs) if pairs else None,
            'mismatch_share': (len(pairs)-match)/len(pairs) if pairs else None}


def clean_values(real, manifest, tab, col):
    t = real.tabs[tab]
    bad = {i['row']-1 for i in manifest['items'] if i['tab'] == tab and i['column'] == col}
    j = t['cols'].get(col)
    return [t['rows'][i][j] for i in t['records'] if i not in bad] if j is not None else []


def key_pair(item, real):
    tab, col = item['tab'], item['column']
    if item['kind'] == 'key_missing_species':
        return item['related_tab'], item['related_column'], tab, col
    candidates = []
    for other, t in real.tabs.items():
        if other == tab or (item.get('related_tab') and other != item['related_tab']):
            continue
        for c in t['cols']:
            a,b = set(real.vals(tab,col))-{''},set(real.vals(other,c))-{''}
            score = len(a & b)/max(1,len(a))
            if score >= .4:
                candidates.append((score,other,c))
    return (tab,col,*max(candidates)[1:]) if candidates else None


def detect(item, book, real, manifest):
    k,tab,col = item['kind'],item['tab'],item['column']
    t=book.tabs[tab]; rows=t['rows']; vals=book.vals(tab,col); filled=[v for v in vals if v]
    note='Detection scans the same tab/column, not the planted coordinate.'
    details={}
    if k == 'spacer':
        n=sum(not any(r) for r in rows[(t['header'] or 0)+1:])
    elif k == 'repeated_header':
        n=sum(sum(v == c for v,c in zip(r, manifest['headers'][tab]['values'])) >= .6*len(manifest['headers'][tab]['values']) for r in rows[(t['header'] or 0)+1:])
    elif k in {'subheading','notes_row'}:
        candidates=[r for r in rows if sum(bool(v) for v in r) == 1 and any(r)]
        if k == 'subheading':
            n=sum(len(next(v for v in r if v).split()) < 5 and not re.match(r'(?i)^total',next(v for v in r if v)) for r in candidates)
            note+=' Sparse short labels are ambiguous with legitimate single-cell records.'
        else:
            n=sum(len(next(v for v in r if v).split()) >= 5 for r in candidates)
            n+=sum(template(r) for r in rows)
            injected=item.get('injected')
            if isinstance(injected,list) and sum(v is not None for v in injected)>1:
                # Descriptive templates need not start with an imperative.
                n+=sum(r == [text(v) for v in injected] for r in rows)
            note+=' Sparse long text or instruction rows; altered descriptive prose may be ambiguous.'
    elif k == 'info_block':
        n=sum(sum(bool(v) for v in r)>=2 for r in rows[:t['header']]) if t['header'] is not None else 0
        note+=' Shape-only: pre-table multi-cell content; no claim that private values should survive.'
    elif k == 'merged_header':
        n=len(t['ws'].merged_cells.ranges)
    elif k == 'unit_in_cell':
        n=sum(bool(re.search(r'(?i)(?:rs\.?|inr|₹|\d\s*(?:cm|mm|kg|weeks?|days?|%))',v)) for v in filled)
    elif k == 'na_text':
        n=sum(v.lower() in NA for v in filled)
    elif k == 'not_a_number':
        n=sum(number(v) is None and v.lower() not in NA for v in filled)
        note+=' Includes unit text; junk is judged against the manifest numeric expectation.'
    elif k in {'bad_email','bad_phone'}:
        pattern=fk.EMAIL if k=='bad_email' else fk.PHONE
        if col not in t['cols']:
            # Contact preambles can contain several email/phone components in one cell.
            candidates=[v for r in rows for v in r if ':' in v and '/' in v]
            bits=[]
            for v in candidates:
                for part in v.split(';'):
                    m=re.search(r':\s*(.*?)\s*/\s*(.*)$',part)
                    if m: bits.append(m.group(1 if k=='bad_email' else 2).strip())
            filled=bits
            note+=' Contact components detected in preamble; absent preamble is a loss.'
        n=sum(not bool(pattern.fullmatch(v)) for v in filled)
        details['valid']=sum(bool(pattern.fullmatch(v)) for v in filled)
        if n and not details['valid']: note+=' No valid examples remain; the entire column may have lost its type.'
    elif k == 'required_missing':
        n=sum(v=='' for v in vals)
    elif k == 'out_of_range':
        clean=[number(v) for v in clean_values(real,manifest,tab,col)]
        clean=[v for v in clean if v is not None]
        if clean:
            lo,hi=min(clean),max(clean)
            n=sum(number(v) is not None and not lo<=number(v)<=hi for v in filled)
            details['clean_real_range']=[lo,hi]
        else: n=0
        if 'account number' in col.lower():
            n=sum(bool(v) and bool(re.fullmatch(r'\d+',v)) and len(v)<9 for v in filled)
            note+=' Account-number error is a length constraint, not a numeric magnitude.'
        else: note+=' Clean real min/max is an empirical plausible range; synthetic shifts can also cross it.'
    elif k in {'mixed_date_format','bad_date','future_date'}:
        clean=clean_values(real,manifest,tab,col)
        fmts=Counter(date(v)[1] for v in clean if date(v)[0])
        fmt=fmts.most_common(1)[0][0] if fmts else '%d/%m/%Y'
        reference=dt.date.fromisoformat(manifest['reference_date'])
        n=sum((date(v)[0] is None if k=='bad_date' else date(v)[1]!=fmt if k=='mixed_date_format' else date(v)[0]>reference) for v in filled if k=='bad_date' or date(v)[0])
        details.update(expected_format=fmt,reference_date=str(reference))
    elif k == 'dbh2_without_dbh1':
        n=sum(not a and bool(b) for a,b in book.tuples(tab,item['columns']))
    elif k == 'duplicate_id':
        counts=Counter(k for k in book.tuples(tab,item.get('columns',[col])) if all(k))
        n=sum(v-1 for v in counts.values())
    elif k == 'casing':
        groups=defaultdict(set)
        for v in filled: groups[v.casefold()].add(v)
        n=sum(len(v)-1 for v in groups.values())
        if isinstance(item.get('original'), str) and item['original'] and item['original'] != str(item['injected']):
            # Scientific binomials need not have a second copy to expose all-caps casing.
            original=item['original']
            if original[0].isupper() and any(ch.islower() for ch in original):
                n+=sum(v.isupper() for v in filled if any(ch.isalpha() for ch in v))
        note+=' Case-equivalent variants only; semantic substitutions such as Completed are not casing.'
    elif k in {'code_not_in_key','key_missing_species','code_typo','team_code'}:
        pair=key_pair(item,real)
        if pair:
            a,c,b,d=pair
            allowed={v.casefold() for v in book.vals(b,d) if v}
            invalid=[v for v in book.vals(a,c) if v and v.casefold() not in allowed]
            n=len(invalid)
            details['key_pair']=pair
            if k=='code_typo':
                import difflib
                n=sum(bool(difflib.get_close_matches(v.casefold(),allowed,n=1,cutoff=.7)) for v in invalid)
        elif k == 'code_typo' and isinstance(item.get('original'),str) and fk._id_like(item['original']):
            shape=lambda v: ''.join('A' if c.isalpha() else '9' if c.isdigit() else c for c in v)
            expected=Counter(shape(v) for v in clean_values(real,manifest,tab,col) if v).most_common(1)
            n=sum(shape(v)!=expected[0][0] for v in filled) if expected else 0
            note+=' Code typo judged by clean dominant code shape, without retaining real codes.'
        else:
            counts=Counter(filled)
            common=[v for v,n in counts.items() if n>=max(2,len(filled)*.04)]
            import difflib
            n=sum(count for v,count in counts.items() if v not in common and bool(difflib.get_close_matches(v,common,n=1,cutoff=.7)))
            note+=' No key tab: rare close spelling variants of frequent labels; necessarily heuristic.'
        if k=='team_code':
            n=sum(bool(re.fullmatch(r'[A-Z]{2,}\d+',v)) for v in filled)
            note+=' Shape-only accepted team codes, not proof of team semantics.'
    elif k=='count_mismatch':
        if item.get('related_tab'):
            other=item['related_tab']; keys=[c for c in real.tabs[tab]['cols'] if c in real.tabs[other]['cols'] and c!=col]
            details=count_relation(book,tab,col,other,keys)
            details.update(related_tab=other,keys=keys)
            n=details['mismatching']
            note+=' Survival requires both matching and mismatching rows, so all-wrong counts do not pass.'
            if not details['matching']: n=0
        else:
            n=int(sum(v.casefold()=='y' for v in filled)!=1 and bool(filled))
            note+=' Manifest rule: exactly one refund account, rather than a cross-tab count.'
    elif k=='end_before_start':
        n=sum(bool(date(a)[0] and date(b)[0] and date(a)[0]<date(b)[0]) for a,b in book.tuples(tab,item['columns']))
    elif k=='total':
        n=sum(bool(re.match(r'(?i)^(grand\s+)?total\b',next((v for v in r if v),''))) for r in rows)
    elif k=='total_mismatch':
        cols=item['columns']
        if 'Cancelled' in item.get('rule',''):
            real_status=real.vals(tab,cols[1]); fake_status=book.vals(tab,cols[1])
            # Identify the category by majority-zero amounts, independent of its spelling.
            groups=defaultdict(list)
            for a,s in book.tuples(tab,cols):
                if number(a) is not None: groups[s].append(number(a))
            candidates=[(sum(v==0 for v in vs)/len(vs),s) for s,vs in groups.items() if len(vs)>=3]
            best=max(candidates,default=(0,''))
            n=sum(number(a) not in (None,0) and s==best[1] for a,s in book.tuples(tab,cols)) if best[0]>=.5 else 0
            note+=' Cancellation inferred from a majority-zero category; if no such category remains, rule is lost.'
        elif len(cols)==3:
            op=(lambda a,b:a*b) if 'Price per unit' in cols else (lambda a,b:a-b)
            ns=[tuple(number(v) for v in row) for row in book.tuples(tab,cols)]
            n=sum(abs(op(a,b)-c)>1e-6 for a,b,c in ns if None not in (a,b,c))
            details['matching']=sum(abs(op(a,b)-c)<=1e-6 for a,b,c in ns if None not in (a,b,c))
            note+=' Arithmetic residual; all-wrong rows do not show preserved contrast.'
            if not details['matching']: n=0
        else:
            # A labelled totals row compared with preceding records in its column.
            j=t['cols'].get(col); n=0
            if j is not None:
                for i,r in enumerate(rows):
                    if re.match(r'(?i)^total\b',next((v for v in r if v),'')) and number(r[j]) is not None:
                        n+=abs(number(r[j])-sum(number(rows[q][j]) or 0 for q in t['records'] if q<i))>1e-6
    else:
        raise ValueError('Missing detector: '+k)
    return dict(fires=bool(n),count=int(n),note=note,**details)


def metrics(vals, expected=None):
    info=fk.classify(vals)
    expected=expected or info["kind"]
    nonblank=[v for v in vals if v]
    if expected=='number': parsed=[number(v) for v in nonblank]
    elif expected=='date': parsed=[date(v)[0] for v in nonblank]
    else: parsed=[]
    good=[v for v in parsed if v is not None]
    return dict(classify=info,rows=len(vals),blank_share=vals.count('')/len(vals) if vals else None,
                junk_share=sum(v is None for v in parsed)/len(vals) if parsed else (0 if expected in {'number','date'} else None),
                min=(min(good).isoformat() if expected=='date' else min(good)) if good else None,
                max=(max(good).isoformat() if expected=='date' else max(good)) if good else None,
                distinct_categories=len(set(nonblank)))


def relationships(real,fake,m):
    out=[]
    for tab,t in real.tabs.items():
        cols=list(t['cols'])
        for a in cols:
            for b in cols:
                if a==b: continue
                def rate(book):
                    rows=book.tuples(tab,[a,b]); blank=[not y for x,y in rows if not x]
                    return dict(antecedent_blank=len(blank),rate=sum(blank)/len(blank) if blank else None)
                rr=rate(real)
                if rr['antecedent_blank'] and rr['rate']>.95:
                    out.append(dict(type='blank_when_blank',tab=tab,a=a,b=b,real=rr,fake=rate(fake)))
        for c in cols:
            if re.search(r'(?i)\bid\b|\bno\b|\bcode\b',c):
                def uniqueness(book):
                    vs=[v for v in book.vals(tab,c) if v]
                    return dict(nonblank=len(vs),duplicates=len(vs)-len(set(vs)))
                out.append(dict(type='id_uniqueness',tab=tab,column=c,real=uniqueness(real),fake=uniqueness(fake),
                                note='Single-column diagnostic; tree IDs need the manifest composite key.'))
    seen=set()
    for item in m['items']:
        if item['kind']=='count_mismatch' and item.get('related_tab'):
            tab,col,other=item['tab'],item['column'],item['related_tab']
            keys=[c for c in real.tabs[tab]['cols'] if c in real.tabs[other]['cols'] and c!=col]
            sig=(tab,col,other)
            if sig not in seen:
                out.append(dict(type='cross_tab_count',tab=tab,column=col,related_tab=other,keys=keys,
                                real=count_relation(real,tab,col,other,keys),fake=count_relation(fake,tab,col,other,keys)))
                seen.add(sig)
        pair=key_pair(item,real) if item['kind'] in {'key_missing_species','code_not_in_key','code_typo'} else None
        if pair and pair not in seen:
            def coverage(book):
                a,c,b,d=pair; vs=[v.casefold() for v in book.vals(a,c) if v]; allowed={v.casefold() for v in book.vals(b,d) if v}
                return dict(values=len(vs),missing=sum(v not in allowed for v in vs),coverage=sum(v in allowed for v in vs)/len(vs) if vs else None)
            out.append(dict(type='key_coverage',pair=pair,real=coverage(real),fake=coverage(fake)));seen.add(pair)
    return out


def run(out):
    out.mkdir(parents=True,exist_ok=True)
    fk.TEACH_DIR=str(out/'mocks')
    fk.SKILLS_DIR=str(out/'no-skills')
    os.chdir(COWORK)
    summary=['# E1 fake-copy fidelity','',f"V2: {os.environ.get('IDLI_MOCK_V2') == '1'}. Source: {'staged patch' if os.environ.get('E1_FILEKIT_SOURCE') else 'installed filekit'}.",
             '', 'Kinds count once per file. Survival requires a real detector hit; ambiguous heuristics and missed detectors are detailed in JSON.', '',
             '| File | Kinds surviving / present | Detector missed |','|---|---:|---:|']
    reports=[]
    for stem in STEMS:
        m=json.loads((ROOT/'manifests'/f'{stem}.json').read_text()); path=ROOT/'fixtures'/f'{stem}.xlsx'
        _,mock,_=fk.make_mock(str(path),'Check this workbook for mistakes.',title=stem)
        real,fake=Book(path,m,True),Book(mock,m)
        items=[]
        for item in m['items']:
            r,f=detect(item,real,real,m),detect(item,fake,real,m)
            items.append(dict(id=item['id'],kind=item['kind'],tab=item['tab'],column=item['column'],real=r,fake=f,
                              status='detector missed' if not r['fires'] else 'survives' if f['fires'] else 'lost'))
        kinds={}
        for kind in sorted({i['kind'] for i in items}):
            cases=[i for i in items if i['kind']==kind]
            hit=any(i['real']['fires'] for i in cases)
            survives=any(i['status']=='survives' for i in cases)
            kinds[kind]=dict(real=hit,fake=survives,status='survives' if survives else 'lost' if hit else 'detector missed',
                             cases=len(cases),detector_missed=sum(i['status']=='detector missed' for i in cases))
        rf,_=fk.raw_sheets(str(path)); ff,_=fk.raw_sheets(mock)
        columns={tab:{c:dict(real=metrics(list(df[c])),fake=metrics(list(ff[tab][c]),fk.classify(df[c])['kind']) if tab in ff and c in ff[tab] else None)
                      for c in df} for tab,df in rf.items()}
        templates=[]
        for tab,t in real.tabs.items():
            h=t['header']
            for i in range(h+1,min(h+6,len(t['rows']))) if h is not None else []:
                row=t['rows'][i]
                if template(row) or any(x['tab']==tab and x['row']==i+1 and x['kind']=='notes_row' for x in m['items']) or (sum(bool(v) for v in row)>1 and all(not re.search(r'@|\d',v) for v in row) and
                                     sum(len(v.split())>=4 for v in row) >= .4*sum(bool(v) for v in row)):
                    templates.append(dict(tab=tab,real_row=i+1,kept_verbatim=row in fake.tabs[tab]['rows'],
                                          note='Short descriptive template rows are included as well as imperative/token instructions.'))
        report=dict(stem=stem,mock=str(Path(mock).relative_to(ROOT)),v2=os.environ.get('IDLI_MOCK_V2')=='1',
                    source='staged' if os.environ.get('E1_FILEKIT_SOURCE') else 'installed',kinds=kinds,items=items,
                    columns=columns,relationships=relationships(real,fake,m),template_rows=templates)
        (out/f'{stem}.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
        real.wb.close();fake.wb.close()
        survived=sum(k['fake'] for k in kinds.values()); missed=sum(not k['real'] for k in kinds.values())
        summary.append(f'| {stem} | {survived} / {len(kinds)} | {missed} |');reports.append(report)
    total=sum(len(r['kinds']) for r in reports); survived=sum(k['fake'] for r in reports for k in r['kinds'].values()); missed=sum(not k['real'] for r in reports for k in r['kinds'].values())
    summary.append(f'| **Total** | **{survived} / {total}** | **{missed}** |')
    for r in reports:
        summary+=['',f"## {r['stem']}",'','| Kind | Real | Fake survives |','|---|---|---|']
        summary += [f"| {k} | {'yes' if v['real'] else 'detector missed'} | {'yes' if v['fake'] else 'no' if v['real'] else 'unscored'} |" for k,v in r['kinds'].items()]
        summary+=['',f"Template rows kept verbatim: {sum(t['kept_verbatim'] for t in r['template_rows'])} / {len(r['template_rows'])}."]
    content='\n'.join(summary)+'\n';(out/'summary.md').write_text(content);print(content)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,default=ROOT/'results/e1'/('fixed' if os.environ.get('IDLI_MOCK_V2')=='1' else 'today'))
    args=p.parse_args();run(args.out.resolve())
