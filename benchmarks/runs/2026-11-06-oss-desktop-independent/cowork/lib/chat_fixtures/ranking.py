import argparse, json
import pandas as pd
p = argparse.ArgumentParser()
p.add_argument('--metric', default='debt')
p.add_argument('--limit', type=int, default=3)
a = p.parse_args()
df = pd.read_excel('drive/households.xlsx')
column = {'debt': 'debts_inr', 'income': 'monthly_income_inr', 'vulnerability': 'vulnerability_score_1to10'}[a.metric]
result = df.groupby('ward')[column].mean().nlargest(a.limit).reset_index(name='average')
print(result.to_string(index=False))
print(json.dumps({'vega_lite': {'mark': 'bar', 'encoding': {'x': {'field': 'ward', 'type': 'nominal'},
      'y': {'field': 'average', 'type': 'quantitative'}}}, 'data': result.to_dict('records')}))
