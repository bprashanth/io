"""Extra parameter cases through the actual spec router, frozen after the first 65-case run."""
import json
import os
from pathlib import Path
from lib import home

CASES = [
 ('ranking', 'Top 2 wards by average income.', {'metric':'income','limit':2}),
 ('ranking', 'Give the four wards with highest vulnerability on average.', {'metric':'vulnerability','limit':4}),
 ('ranking', 'Rank wards by income.', {'metric':'income','limit':3}),
 ('filter', 'List the households of Janata Vasahat.', {'ward':'Janata Vasahat'}),
 ('filter', 'Show household records for Hadapsar Ward.', {'ward':'Hadapsar Ward'}),
 ('filter', 'Household names and debts in Yerawada Ward please.', {'ward':'Yerawada Ward'}),
 ('threshold', 'Who owes over 12 months of income in Ramtekdi?', {'ward':'Ramtekdi','months':12}),
 ('threshold', 'In Janata Vasahat, whose debts exceed 2.5 months of income?', {'ward':'Janata Vasahat','months':2.5}),
 ('threshold', 'Show Kasewadi households above the usual debt to monthly income cutoff.', {'ward':'Kasewadi','months':6}),
 ('comparison', 'Compare average debts in Yerawada Ward and Hadapsar Ward.', {'ward_a':'Yerawada Ward','ward_b':'Hadapsar Ward'}),
 ('comparison', 'Ramtekdi versus Janata Vasahat on average household debt.', {'ward_a':'Ramtekdi','ward_b':'Janata Vasahat'}),
 ('comparison', 'Average debt: Kasewadi versus Hadapsar Ward.', {'ward_a':'Kasewadi','ward_b':'Hadapsar Ward'}),
 ('trend', 'Monthly counts of cancelled visits.', {'status':'Cancelled'}),
 ('trend', 'How have completed visits changed by month?', {'status':'Done'}),
 ('trend', 'Show monthly Done visit numbers over time.', {'status':'Done'}),
 (None, 'Send an email to all the families.', {}),
 (None, 'Rank the wards by population.', {}),
 (None, 'Which village had the most rainfall?', {}),
 (None, 'Compare median debt in Kasewadi and Ramtekdi.', {}),
 (None, 'Show the yearly change in household income.', {}),
]


def main():
    os.environ.pop('IDLI_9B_URL', None)
    os.environ.setdefault('MUSE_URL', 'http://127.0.0.1:8186')
    questions = home.read(Path(__file__).with_name('chat_fixtures')/'mini.json')['questions']
    results = []
    for qid, text, params in CASES:
        actual = home.map_questions(questions, text)
        correct = actual['qid'] == qid and actual['params'] == params and actual['method'] == 'idli-9b'
        results.append({'text':text,'qid':qid,'params':params,'actual':actual,'correct':correct})
        print(f"{len(results)}/{len(CASES)}: {'pass' if correct else 'FAIL'}", flush=True)
    home.write(Path(__file__).with_name('chat_mapping_holdout_results.json'),
               {'route':'spec router', 'correct':sum(r['correct'] for r in results),'total':len(results),'results':results})


if __name__ == '__main__':
    main()
