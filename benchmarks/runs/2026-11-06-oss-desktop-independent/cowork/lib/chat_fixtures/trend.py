import argparse, json
import pandas as pd
p = argparse.ArgumentParser()
p.add_argument('--status', default='Done')
a = p.parse_args()
df = pd.read_excel('drive/field_programme_tracker.xlsx', sheet_name='Visits')
df = df.loc[df.Status.eq(a.status)].copy()
df['month'] = pd.to_datetime(df['Visit date'], dayfirst=True, errors='coerce', format='mixed').dt.strftime('%Y-%m')
result = df.groupby('month').size().reset_index(name='visits')
print(result.to_string(index=False))
print(json.dumps({'vega_lite': {'mark': 'line', 'encoding': {'x': {'field': 'month', 'type': 'ordinal'},
      'y': {'field': 'visits', 'type': 'quantitative'}}}, 'data': result.to_dict('records')}))
