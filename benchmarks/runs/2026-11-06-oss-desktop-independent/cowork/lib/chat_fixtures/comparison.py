import argparse, json
import pandas as pd
p = argparse.ArgumentParser()
p.add_argument('--ward_a', default='Kasewadi')
p.add_argument('--ward_b', default='Ramtekdi')
a = p.parse_args()
df = pd.read_excel('drive/households.xlsx')
result = df.loc[df.ward.isin([a.ward_a, a.ward_b])].groupby('ward').debts_inr.mean().reset_index(name='average_debt')
print(result.to_string(index=False))
print(json.dumps({'vega_lite': {'mark': 'bar', 'encoding': {'x': {'field': 'ward', 'type': 'nominal'},
      'y': {'field': 'average_debt', 'type': 'quantitative'}}}, 'data': result.to_dict('records')}))
