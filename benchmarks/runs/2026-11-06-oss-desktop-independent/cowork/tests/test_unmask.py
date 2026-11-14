"""Synthetic reveal, lookup, map and launcher checks. No real accounts or searches."""
import io
import json
from unittest.mock import patch
import pandas as pd
import pytest
from lib import privacy, ccproxy, reveals, idli_mcp, launchsettings, maps

@pytest.fixture
def data(tmp_path, monkeypatch):
    monkeypatch.setenv('IDLI_DATA',str(tmp_path));monkeypatch.setenv('IDLI_WORKSPACE','synthetic-workspace')
    monkeypatch.setenv('IDLI_SCANNER','http://127.0.0.1:1/scan')
    frame=pd.DataFrame({'Name':['Asha Sample','Ravi Example','Mina Test'],
                        'Ward':['Yerawada Ward','River Ward','Garden Ward'],
                        'household_id':['HH-01','HH-02','HH-03'],
                        'lat':['18.52345','18.62345','18.72345'],
                        'notes':['Unclassified value','Another value','Last value']})
    frame.to_csv(tmp_path/'households.csv',index=False)
    privacy.set(tmp_path,'households.csv',mode='mask',columns={c:True for c in frame})
    return tmp_path

def code(data,value):return privacy.session_vault(data).forward[privacy.normalise(value)]
def request(text):return {'messages':[{'role':'user','content':text}]}
def approve(data,value='Yerawada Ward',workspace='synthetic-workspace',kind='unmask'):
    r=reveals.create(data,code(data,value),'Match a published total',workspace,kind,'Statistics for {value}' if kind=='lookup' else None)
    assert 'id' in r
    assert reveals.decide(data,r['id'],True)=={'decision':'approved'}
    return r['id']

@pytest.mark.parametrize('column,expected',[(c,'personal') for c in ['Name','household_head','owner','respondent','farmer','phone','email','Address','Aadhaar','PAN','voter','ration','account','ifsc','upi','record_id','ID','lat','lon','gps','coordinates','unknown','mystery']]+[(c,'contextual') for c in ['Ward','village','district','block','town','organisation','organisation_name','programme','scheme','category','district_name']])
def test_column_classes(column,expected):assert privacy.column_class(column)==expected

def test_code_info_and_personal_use_wins(data):
    assert privacy.code_info(data,code(data,'Yerawada Ward'))=={'file':'households.csv','column':'Ward','class':'contextual'}
    assert privacy.code_info(data,code(data,'Unclassified value'))['class']=='personal'
    assert privacy.code_info(data,'PLACE_999') is None
    pd.DataFrame({'Name':['Yerawada Ward']}).to_csv(data/'other.csv',index=False)
    privacy.set(data,'other.csv',mode='mask',columns={'Name':True})
    assert privacy.code_info(data,code(data,'Yerawada Ward'))['class']=='personal'

def test_proxy_reveal_hide_cache_and_personal_belt(data):
    transformer=ccproxy.Transformer(data);body=request('Yerawada Ward and Asha Sample')
    assert 'Yerawada Ward' not in str(transformer.outbound(body)[0])
    approve(data);out,_=transformer.outbound(body)
    assert out['messages'][0]['content'].startswith('Yerawada Ward and NAME_')
    assert not transformer.leaks(out)
    assert transformer.leaks(request('Asha Sample'))
    rows=privacy.reveals(data)
    rows.append({'code':code(data,'Asha Sample'),'value':'Asha Sample','column':'Name','file':'households.csv','workspace':'synthetic-workspace','reason':'Invalid personal entry','at':'synthetic'})
    privacy._write(data/'.idli/reveals.json',rows);transformer.refresh()
    assert transformer.leaks(request('Asha Sample'))
    assert 'Asha Sample' not in str(transformer.outbound(request('Asha Sample'))[0])
    reveals.hide(data,rows[0]['code'],rows[0]['workspace'],rows[0]['at'])
    assert 'Yerawada Ward' not in str(transformer.outbound(body)[0])

def test_revealed_value_not_scanned_again(data):
    approve(data)
    class Scanner:
        status='ok'
        def __call__(self,text):
            pos=text.find('Yerawada')
            return [(pos,pos+len('Yerawada Ward'),'person_name',1)] if pos>=0 else []
    with patch.object(privacy,'Scanner',Scanner):
        assert ccproxy.Transformer(data).outbound(request('Yerawada Ward'))[0]['messages'][0]['content']=='Yerawada Ward'

def test_personal_still_guarded_after_mask_switch_off(data):
    privacy.session_vault(data);privacy.set(data,'households.csv',columns={'Name':False,'Ward':True})
    transformer=ccproxy.Transformer(data)
    assert transformer.leaks(request('Asha Sample'))
    assert 'Asha Sample' not in str(transformer.outbound(request('Asha Sample'))[0])

@pytest.mark.parametrize('name',['Asha Sample','HH-01','18.52345','Unclassified value'])
def test_tools_refuse_personal_without_page(data,name):
    with patch('lib.uiswitch.open_url',side_effect=AssertionError('No personal consent page')):
        assert idli_mcp.unmask(code(data,name),'Read it')['refused']==reveals.PERSONAL
        assert idli_mcp.lookup(code(data,name),'Details {value}','Read it')['refused']==reveals.PERSONAL
        assert idli_mcp.unmask('PLACE_999','Read it')['refused']==reveals.PERSONAL

def test_budget_workspace_and_hide_does_not_refund(data):
    for _ in range(3):approve(data)
    assert reveals.remaining(data,'synthetic-workspace')==0
    assert 'refused' in reveals.create(data,code(data,'River Ward'),'Read table','synthetic-workspace')
    approve(data,kind='lookup');assert reveals.remaining(data,'synthetic-workspace')==0
    row=privacy.reveals(data)[0];reveals.hide(data,row['code'],row['workspace'],row['at'])
    assert reveals.remaining(data,'synthetic-workspace')==0
    reveals.allow_more(data,'synthetic-workspace');approve(data,'River Ward')
    assert reveals.remaining(data,'synthetic-workspace')==2
    assert reveals.remaining(data,'another-workspace')==3

def test_pending_requests_cannot_overspend_and_decisions_are_single_use(data):
    for _ in range(2):approve(data)
    pending=[reveals.create(data,code(data,'River Ward'),'Match table','synthetic-workspace')['id'] for _ in range(2)]
    assert reveals.decide(data,pending[0],True)['decision']=='approved'
    assert reveals.decide(data,pending[0],True)['decision']=='approved'
    assert reveals.decide(data,pending[1],True)['decision']=='budget'
    assert len(privacy.reveals(data))==3

def test_denial_timeout_invalid_query_and_changed_class(data):
    c=code(data,'River Ward')
    assert 'refused' in reveals.create(data,c,'Reason','synthetic-workspace','lookup','no placeholder')
    for decision in ['denied','timeout','changed']:
        ident=reveals.create(data,c,'Match table','synthetic-workspace')['id']
        if decision=='denied':r=reveals.decide(data,ident,False)
        elif decision=='timeout':
            with patch.object(reveals.time,'time',return_value=10**12):r=reveals.decide(data,ident,True)
        else:
            with patch.object(privacy,'code_info',return_value={'class':'personal'}):r=reveals.decide(data,ident,True)
        assert r['decision']==decision
    assert privacy.reveals(data)==[]

def test_lookup_http_top_six_and_masks_all_files_even_revealed(data):
    approve(data)
    pd.DataFrame({'Email':['private@example.test']}).to_csv(data/'second.csv',index=False)
    privacy.set(data,'second.csv',mode='mask',columns={'Email':True})
    html=''.join(f'<div><a class="result__a" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fexample.test%2FYerawada%2520Ward">Yerawada Ward <b>{i}</b></a><a class="result__snippet">Asha Sample private@example.test in Yerawada Ward</a></div>' for i in range(8))
    with patch.object(reveals.urllib.request,'urlopen',return_value=io.BytesIO(html.encode())) as http:
        out=reveals.lookup_results(data,code(data,'Yerawada Ward'),'Statistics for {value}','Yerawada Ward')
    assert len(out['results'])==6
    assert all(set(r)=={'title','url','snippet'} for r in out['results'])
    assert not privacy.known_leaks(json.dumps(out),privacy.session_vault(data))
    assert code(data,'Yerawada Ward') in json.dumps(out)
    req=http.call_args.args[0]
    assert req.full_url.startswith('https://html.duckduckgo.com/html/?') and 'Yerawada+Ward' in req.full_url
    assert req.get_header('User-agent')=='Idli/1.0' and http.call_args.kwargs['timeout']==10

def test_query_cannot_send_another_private_value(data):
    ident=reveals.create(data,code(data,'River Ward'),'Check table','synthetic-workspace','lookup','{value} Asha Sample')['id']
    query=reveals.consent_data(data,ident)['query']
    assert '{value}' in query and 'Asha Sample' not in query and 'NAME_' in query

def test_tools_need_page_approval_and_failure_stays_hidden(data):
    with patch('lib.uiswitch.open_url',return_value={'ok':False}),patch('lib.journey.page_url',return_value='http://synthetic.test/'):
        assert 'refused' in idli_mcp.unmask(code(data,'River Ward'),'Match table')
    assert privacy.reveals(data)==[]
    with patch.object(reveals,'ask',return_value={'refused':'Kept hidden'}),patch.object(reveals,'search',side_effect=AssertionError()):
        assert idli_mcp.lookup(code(data,'River Ward'),'{value}','Match table')=={'refused':'Kept hidden'}

def test_consent_code_preserved_in_json_and_stream(data):
    vault=privacy.session_vault(data);c=code(data,'Yerawada Ward')
    block={'type':'tool_use','name':'mcp__idli__lookup','input':{'code':c,'query':'Statistics {value}'}}
    assert ccproxy.Transformer(data).restore(block)['input']['code']==c
    sse=ccproxy.SSE(vault)
    events=[{'type':'content_block_start','index':0,'content_block':{**block,'input':{}}}]
    raw=json.dumps(block['input'])
    events += [{'type':'content_block_delta','index':0,'delta':{'type':'input_json_delta','partial_json':part}} for part in [raw[:20],raw[20:]]]
    events += [{'type':'content_block_stop','index':0}]
    output=b''.join(sse.process(sse.event(e)) for e in events).decode()
    assert 'Yerawada Ward' not in output and c in output

def test_settings_merge_idempotent(tmp_path):
    path=tmp_path/'.claude/settings.json';path.parent.mkdir()
    before={'theme':'dark','permissions':{'allow':['Read'],'deny':['Bash(rm *)'],'ask':['Write']},'env':{'EXAMPLE':'synthetic'}}
    path.write_text(json.dumps(before))
    for _ in range(2):launchsettings.merge(tmp_path)
    saved=json.loads(path.read_text())
    assert saved=={**before,'permissions':{**before['permissions'],'ask':['Write',*launchsettings.ASK]}}
    assert path.stat().st_mode & 0o777==0o600

@pytest.mark.parametrize('name',[' Pune DISTRICT ','P U N E','pune','Poona'])
def test_district_matching(name):assert maps.match_district(name,'Maharashtra')['properties']['name']=='Pune'

def test_map_validation_and_local_boundaries():
    for name in maps.FILES:
        assert maps.boundary(name)['type']=='Topology'
        assert len(json.dumps(maps.boundary(name)).encode())<2_000_000
    gps={'usermeta':{'idli_map':{'type':'gps','lat':'lat','lon':'lon'}}}
    for lat in ['hidden','NaN']:
        with pytest.raises(maps.MapError,match='numeric latitude'):maps.prepare(gps,[{'lat':lat,'lon':73}])
    district={'usermeta':{'idli_map':{'type':'district','field':'district','value':'count'}}}
    with pytest.raises(maps.MapError,match='No district names matched'):maps.prepare(district,[{'district':'Imaginary','count':12}])
    with pytest.raises(maps.MapError,match='External boundary'):maps.prepare({**district,'data':{'url':'https://example.test/map'}},[])
    with pytest.raises(maps.MapError,match='Use /geo'):maps.boundary('../private.json')
    out=maps.prepare(district,[{'district':'Pune','count':12},{'district':'Imaginary','count':8}])
    assert 'Unmatched districts: Imaginary.' in out['description']
    assert out['layer'][1]['data']['values'][0]['properties']['district']=='Pune'
    assert maps.match_district('Aurangabad') is None
    assert maps.match_district('Puen','Maharashtra') is None
    assert maps.match_district('Nashikk','Maharashtra')['properties']['name']=='Nashik'

@pytest.mark.parametrize('value',['Asha Sample','HH-01','18.52345','Unclassified value'])
def test_every_personal_value_ignores_forged_reveal(data,value):
    privacy._write(data/'.idli/reveals.json',[{'code':code(data,value),'value':value,'kind':'unmask'}])
    transformer=ccproxy.Transformer(data)
    assert transformer.leaks(request(value))
    assert value not in str(transformer.outbound(request(value))[0])

@pytest.mark.parametrize('heading',['ward_farmer','programme_owner','district_employee','scheme_contact_person'])
def test_contextual_word_does_not_override_person_heading(heading):
    assert privacy.column_class(heading)=='personal'


def test_lookup_log_never_allows_proxy_value(data):
    approve(data,kind='lookup')
    assert privacy.reveals(data)[0]['kind']=='lookup'
    assert privacy.revealed_values(data)=={}
    assert ccproxy.Transformer(data).leaks(request('Yerawada Ward'))


def test_name_backstop_and_scanner_code_remain_personal(data):
    pd.DataFrame({'Helper':['Asha Sample','Ravi Example','Mina Test']}).to_csv(data/'helpers.csv',index=False)
    rows=privacy.review(data,'helpers.csv',data/'helpers.csv')['suggestions']
    assert rows[0]['mask'] and "names" in rows[0]['reason']
    vault=privacy.session_vault(data)
    vault.token('Scanned Place Name','person_name');privacy._save(vault)
    pd.DataFrame({'Ward':['Scanned Place Name']}).to_csv(data/'places.csv',index=False)
    privacy.set(data,'places.csv',mode='mask',columns={'Ward':True})
    assert privacy.code_info(data,code(data,'Scanned Place Name'))['class']=='personal'


def test_map_errors_reach_mcp_as_clear_messages(data,monkeypatch,capsys):
    import sys
    chart=data/'chart.csv';chart.write_text('district,count\nImaginary district,12\n')
    spec={'usermeta':{'idli_map':{'type':'district','field':'district','value':'count'}}}
    message={'id':1,'method':'tools/call','params':{'name':'idli_show','arguments':{
        'title':'District totals','vega_lite':spec,'data_csv':str(chart)}}}
    monkeypatch.setattr(sys,'stdin',io.StringIO(json.dumps(message)+'\n'))
    idli_mcp.main();out=json.loads(capsys.readouterr().out)['result']
    assert out['isError'] and 'No district names matched' in out['content'][0]['text']
    bad={'usermeta':{'idli_map':{'type':'district'}},'layer':[{'data':{'url':'/geo/india-districts.topo.json','format':{'type':'topojson','feature':'wrong'}},'mark':'geoshape'}]}
    with pytest.raises(maps.MapError,match='matching the boundary file'):maps.prepare(bad,[])
    maps.boundary.cache_clear();maps.features.cache_clear()
    with patch.object(maps,'GEO',data):
        with pytest.raises(maps.MapError,match='missing or invalid'):maps.prepare({'usermeta':{'idli_map':{'type':'gps'}}},[])
    maps.boundary.cache_clear();maps.features.cache_clear()


def test_lookup_sends_only_the_approved_query(data):
    c=code(data,'River Ward')
    approved={'query':'Approved search {value}','value':'River Ward'}
    with patch.object(reveals,'ask',return_value=approved),patch.object(reveals,'search',return_value=[]) as search:
        assert idli_mcp.lookup(c,'Unapproved Asha Sample {value}','Check table')['code']==c
        search.assert_called_once_with('Approved search River Ward')
    with patch.object(reveals,'search',side_effect=AssertionError('No personal search')):
        with pytest.raises(ValueError,match='Names, contacts'):reveals.lookup_results(data,code(data,'Asha Sample'),'{value}','Asha Sample')


def test_budget_write_failure_does_not_publish_reveal(data):
    ident=reveals.create(data,code(data,'River Ward'),'Match table','synthetic-workspace')['id']
    write=privacy._write
    def fail_budget(path,obj):
        if path.name=='reveal-budget.json':raise OSError('Synthetic write failure')
        return write(path,obj)
    with patch.object(privacy,'_write',side_effect=fail_budget):
        with pytest.raises(OSError):reveals.decide(data,ident,True)
    assert privacy.reveals(data)==[]
    assert reveals.consent_data(data,ident)['decision']=='pending'
