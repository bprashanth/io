"""Plain-assert regression tests: PYTHONPATH=. .venv/bin/python lib/test_mock_v2.py."""
import os
import random
import tempfile
from pathlib import Path

import pandas as pd
from lib import filekit as fk


def test_instructions():
    assert fk._instruction_row(['Enter the full scientific name', 'MANDATORY', ''])
    assert fk._instruction_row(['If applicable describe the storage method', 'Optional'])
    assert fk._instruction_row(['e.g. describe the seed storage method'])
    for private in ['Jane Doe', 'Enter the email person@example.org now',
                    'Enter the phone number 9000000001', '1234567890', 'Jane Doe needs more information', 'Enter the name of Ravi Patil']:
        assert not fk._instruction_row([private, 'MANDATORY']), private


def test_relations():
    parent = pd.DataFrame({'ID': ['A001', 'A002', 'A003', 'A004', 'A005'],
                           'Count': ['70', '70', '70', '70', '71']})
    child = pd.DataFrame({'ID': [v for v in parent.ID for _ in range(70)],
                          'Value': ['2']*350})
    # The real difference must survive even when a mock's 300-row cap removes children.
    sheets = {'Parent': parent, 'Child': child}
    mocks = {'Parent': parent.assign(ID=['X001','X002','X003','X004','X005'], Count='999'),
             'Child': child.head(300).assign(ID='wrong')}
    fk._mock_v2(sheets, mocks)
    counts = mocks['Child'].groupby('ID').size()
    residuals = [float(r.Count) - counts.get(r.ID, 0) for r in mocks['Parent'].itertuples()]
    assert residuals == [0,0,0,0,1], residuals
    assert mocks['Parent'].ID.nunique()==5
    parent2=pd.DataFrame({'Transect':['1','1','2','2','3'], 'Plot':['1','2','1','2','1'], 'Trees':['2','2','2','2','3']})
    child2=pd.DataFrame({'Transect':[v for v in parent2.Transect for _ in range(2)],
                         'Plot':[v for v in parent2.Plot for _ in range(2)], 'Species':['fake']*10})
    mocks2={'Parent':parent2.assign(Trees='99'), 'Child':child2.copy()}
    fk._mock_v2({'Parent':parent2,'Child':child2},mocks2)
    counts2=mocks2['Child'].groupby(['Transect','Plot']).size()
    assert [float(r.Trees)-counts2.get((r.Transect,r.Plot),0) for r in mocks2['Parent'].itertuples()]==[0,0,0,0,1]

    rows = pd.DataFrame({'Label':['record']*5+['Total'], 'A':['1']*5+['5'],
                         'B':['2']*5+['10'], 'Total':['3','3','3','3','4','16']})
    fake = pd.DataFrame({'Label':['fake']*5+['Total'], 'A':['10']*5+['9'],
                         'B':['20']*5+['9'], 'Total':['99']*6})
    fk._mock_v2({'Data':rows},{'Data':fake})
    assert list(fake.Total[:5])==['30','30','30','30','31']
    assert fake.loc[5,'A']=='50' and fake.loc[5,'B']=='100'
    assert fake.loc[5,'Total']=='151'
    rows.loc[5,'A']='8'  # A deliberately incorrect grand total keeps its +3 residual.
    fk._mock_v2({'Data':rows},{'Data':fake})
    assert fake.loc[5,'A']=='53'


def test_column_quirks():
    vals=pd.Series(['5']*20+['2cm','3 weeks','approx 12','n/a','','many'])
    saved=os.environ.get('IDLI_MOCK_V2')
    try:
        os.environ.pop('IDLI_MOCK_V2',None)
        old,_=fk.mock_column(vals,'Depth',random.Random(7))
        os.environ['IDLI_MOCK_V2']='0'
        off,_=fk.mock_column(vals,'Depth',random.Random(7))
        assert old==off
        os.environ['IDLI_MOCK_V2']='1'
        new,_=fk.mock_column(vals,'Depth',random.Random(7))
        assert new[20].endswith('cm') and new[21].endswith('weeks')
        assert new[22].startswith('approx ') and new[23]=='n/a' and new[24]==''
        assert new[25]=='unknown quantity'
    finally:
        if saved is None: os.environ.pop('IDLI_MOCK_V2',None)
        else: os.environ['IDLI_MOCK_V2']=saved


def test_workbook():
    saved=(fk.TEACH_DIR,fk.SKILLS_DIR,os.environ.get('IDLI_MOCK_V2'))
    try:
        with tempfile.TemporaryDirectory() as d:
            fk.TEACH_DIR=str(Path(d)/'teach');fk.SKILLS_DIR=str(Path(d)/'no-skills')
            p=Path(d)/'source.xlsx'
            rows=pd.DataFrame({'Name':['Enter the full scientific name','MANDATORY','Jane Doe','Ann Smith','Lee Jones'],
                               'Care':['Describe the way seeds are stored','OPTIONAL','','shade','']})
            rows.to_excel(p,index=False)
            os.environ['IDLI_MOCK_V2']='1'
            _,mock,_=fk.make_mock(str(p),'Check it')
            result,_=fk.raw_sheets(mock)
            assert list(result['Sheet1'].iloc[0])==list(rows.iloc[0])
            assert list(result['Sheet1'].iloc[1])==list(rows.iloc[1])
            assert result['Sheet1'].Care.tolist()[2:]==['',result['Sheet1'].Care.iloc[3],'']
            assert 'Jane Doe' not in result['Sheet1'].Name.tolist()
            p2=Path(d)/'numbers.xlsx'
            pd.DataFrame({'Depth':['10']*20+['n/a','2cm','']}).to_excel(p2,index=False)
            _,mock2,_=fk.make_mock(str(p2),'Check numbers')
            import openpyxl
            wb=openpyxl.load_workbook(mock2)
            assert wb['Sheet1'].cell(22,1).value=='n/a'
            assert wb['Sheet1'].cell(23,1).value.endswith('cm')
            wb.close()
    finally:
        fk.TEACH_DIR,fk.SKILLS_DIR,flag=saved
        if flag is None: os.environ.pop('IDLI_MOCK_V2',None)
        else: os.environ['IDLI_MOCK_V2']=flag


if __name__=='__main__':
    for test in (test_instructions,test_relations,test_column_quirks,test_workbook):
        test()
        print('ok  '+test.__name__)
    print('ALL PASSED')
