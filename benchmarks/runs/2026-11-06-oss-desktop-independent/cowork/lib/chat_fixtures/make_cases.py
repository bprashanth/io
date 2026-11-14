"""Synthetic, fixed phrasing set. Expected values are written before running the mapper."""
import json
from pathlib import Path

cases = []
def add(qid, params, phrases):
    cases.extend({'type': qid, 'text': text, 'qid': qid, 'params': params} for text in phrases)
add('ranking', {'metric': 'debt', 'limit': 3}, [
 'Which three wards have the largest average debts?', 'Rank the top 3 wards by debt.',
 'Where is mean household debt highest? Give me the first three.', 'Show the three most indebted wards on average.',
 'Order wards by average debt and keep three.', 'Top three areas by mean debt, please.',
 'Give me a league table of the 3 wards with highest debt per household.',
 'I want the leading three wards for average debt.', 'Rank wards on debt.', 'Which wards are at the top for debt?'])
add('filter', {'ward': 'Ramtekdi'}, [
 'List the households in Ramtekdi.', 'Who lives in Ramtekdi and what are their income and debts?',
 'Show only Ramtekdi families.', 'Can I see household records for Ramtekdi?',
 'Give the names, income and debt for households from Ramtekdi.', 'Filter the household list to Ramtekdi.',
 'Pull up Ramtekdi household details.', 'I need the families belonging to Ramtekdi.',
 'Show every household in ramtekdi.', 'For Ramtekdi, list each household and its debt.'])
add('threshold', {'ward': 'Kasewadi', 'months': 8}, [
 'Which families in Kasewadi owe more than 8 months of income?',
 'In Kasewadi, find households with debt above eight months of earnings.',
 'Who in kasewadi has debt over 8 times their monthly income?',
 'List Kasewadi families whose debt would take more than 8 months of income to repay.',
 'Filter Kasewadi households to a debt to monthly income ratio greater than eight.',
 'Find the households in Kasewadi over the 8-month debt threshold.',
 'Any Kasewadi households owing over eight months of income?',
 'Show Kasewadi households with debts exceeding 8 months of earnings.',
 'Whose debt is bigger than eight monthly incomes in Kasewadi?',
 'Kasewadi: debt greater than 8 months of income, please.'])
add('comparison', {'ward_a': 'Kasewadi', 'ward_b': 'Ramtekdi'}, [
 'Compare Kasewadi and Ramtekdi on average debt.', 'What is the difference in mean debt between Kasewadi and Ramtekdi?',
 'Kasewadi versus Ramtekdi: household debt averages.', 'Put Kasewadi beside Ramtekdi for average debts.',
 'How does Kasewadi stack up against Ramtekdi on average debt?',
 'Show mean household debt for Kasewadi and Ramtekdi side by side.',
 'Is average debt higher in Kasewadi or Ramtekdi?', 'Contrast the average debts of Kasewadi with Ramtekdi.',
 'Can we compare the debt per family in Kasewadi to Ramtekdi?', 'Two wards, Kasewadi and Ramtekdi: compare their mean debt.'])
add('trend', {'status': 'Follow-up'}, [
 'How many Follow-up visits were there each month?', 'Show the monthly trend of follow-up field visits.',
 'Plot follow-up visit counts over time.', 'Has the number of follow-up visits changed month by month?',
 'Give a time series of visits marked Follow-up.', 'Break down Follow-up visits by month.',
 'Track the volume of follow-up visits across the months.', 'Monthly counts, only Follow-up visits please.',
 'Draw a line chart of follow-up visit numbers by month.', 'Over time, what happened to the count of follow-up visits?'])
# Three refusals adjacent to each question type; no irrelevant request gets a nearby supported answer.
invalid = {
 'ranking': ['Rank wards by their median rent.', 'Which ward will have the highest debt next year?', 'What is the best restaurant?'],
 'filter': ['List household phone numbers in Ramtekdi.', 'List households in Pune Central.', 'Delete the Ramtekdi households.'],
 'threshold': ['Which households owe more than 50000 rupees?', 'Which Kasewadi families have savings over 6 months of income?', 'Predict which families will default.'],
 'comparison': ['Compare average incomes of Kasewadi and Ramtekdi.', 'Why does Kasewadi have higher debt than Ramtekdi?', 'Compare school attendance in these wards.'],
 'trend': ['Show monthly household debt over time.', 'Forecast field visits for next year.', 'Plot rainfall by month.']}
for typ, phrases in invalid.items():
 cases.extend({'type':typ,'text':t,'qid':None,'params':{}} for t in phrases)
Path(__file__).with_name('mapping_cases.json').write_text(json.dumps(cases, indent=2)+'\n')
