import argparse, json
import pandas as pd
p = argparse.ArgumentParser()
p.add_argument('--ward', default='Kasewadi')
p.add_argument('--months', type=float, default=6)
a = p.parse_args()
df = pd.read_excel('drive/households.xlsx')
valid = df.ward.eq(a.ward) & df.monthly_income_inr.gt(0)
result = df.loc[valid & df.debts_inr.gt(a.months * df.monthly_income_inr), ['household_head', 'debts_inr']]
print(f'{len(result)} households exceed {a.months:g} months of income. Missing or zero income excluded.')
print(result.to_string(index=False))
chart = result.rename(columns={'debts_inr': 'debt'})
print(json.dumps({'vega_lite': {'mark': 'bar', 'encoding': {'x': {'field': 'household_head', 'type': 'nominal'},
      'y': {'field': 'debt', 'type': 'quantitative'}}}, 'data': chart.to_dict('records')}))
