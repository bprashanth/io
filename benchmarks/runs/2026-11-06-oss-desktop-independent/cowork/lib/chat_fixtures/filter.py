import argparse, json
import pandas as pd
p = argparse.ArgumentParser()
p.add_argument('--ward', default='Kasewadi')
a = p.parse_args()
df = pd.read_excel('drive/households.xlsx')
result = df.loc[df.ward.eq(a.ward), ['household_head', 'ward', 'debts_inr', 'monthly_income_inr']]
print(result.to_string(index=False))
chart = result[['household_head', 'debts_inr']].rename(columns={'debts_inr': 'debt'})
print(json.dumps({'vega_lite': {'mark': 'bar', 'encoding': {'x': {'field': 'household_head', 'type': 'nominal'},
      'y': {'field': 'debt', 'type': 'quantitative'}}}, 'data': chart.to_dict('records')}))
