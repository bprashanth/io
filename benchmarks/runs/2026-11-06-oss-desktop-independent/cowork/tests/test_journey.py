"""Synthetic Drivey contract checks. No account, model, Drive or running Paseo needed.
Run: python -m unittest discover -s tests -p 'test_journey.py' -v
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import urllib.parse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from lib import modes, minimap, home, journey, formserver, idli_mcp, uiswitch, drivestubs, privacy
from sites.files import tools

FILES = [{'local': 'drive/visits.xlsx', 'title': 'Visits'}]
QUESTION = {'id': 'total', 'question': 'How many visits in each ward?', 'script': 'analysis.py',
            'params': {'ward': {'type': 'choice', 'choices': ['All', 'Garden'], 'default': 'All'}}}
SPEC = {'mark': 'bar', 'encoding': {'x': {'field': 'ward', 'type': 'nominal'},
                                 'y': {'field': 'visits', 'type': 'quantitative'}}}
SCRIPT = '''import argparse, json
p=argparse.ArgumentParser();p.add_argument('--ward',default='All');a=p.parse_args()
assert a.ward in ('All','Garden')
print('Visits: 12')
print(json.dumps({'vega_lite': %r, 'data':[{'ward':'Garden','visits':12},{'ward':'River','visits':8}]}))
''' % SPEC


class Transcript:
    def __init__(self, model='idli-9b'):
        self.j = {'model': model, 'tools': [{'name': 'mcp__cowork__'+n} for n in modes.DRIVEY_TOOLS]
                  + [{'name': 'AskUserQuestion'}, {'name': 'Read'}], 'messages': []}
    def said(self, text):
        self.j['messages'].append({'role': 'user', 'content': text})
        return self.next()
    def next(self):
        with patch.object(modes, '_nine_call', side_effect=AssertionError('Chat model must never run')):
            r = modes.respond(self.j)
        self.j['messages'].append({'role': 'assistant', 'content': r['content']})
        self.r = r
        return r
    def result(self, obj):
        call = [b for b in self.r['content'] if b['type'] == 'tool_use'][-1]
        self.j['messages'].append({'role': 'user', 'content': [{'type': 'tool_result', 'tool_use_id': call['id'],
                                   'content': json.dumps(obj) if isinstance(obj, dict) else obj}]})
        return self.next()
    def choose(self, answer):
        card = [b for b in self.r['content'] if b['type'] == 'tool_use'][-1]
        q = card['input']['questions'][0]['question']
        return self.result('"'+q+'"="'+answer+'". You can now continue')
    def tool(self):
        return [b for b in self.r['content'] if b['type'] == 'tool_use'][-1]
    def text(self):
        return '\n'.join(b.get('text', '') for b in self.r['content'])


class RouterTests(unittest.TestCase):
    def fetched(self):
        t=Transcript();t.said('How many visits? @Drive/visits.xlsx')
        self.assertEqual(t.tool()['input'], {'paths': ['Drive/visits.xlsx'], 'question': 'How many visits?'})
        t.result({'files':FILES, 'masked_question':'How many visits?'})
        self.assertEqual(t.tool()['input']['questions'][0]['header'], 'Privacy')
        self.assertIn('Visits', t.text())
        return t
    def test_first_message_no_files_every_model(self):
        for model in ['idli-9b', 'muse-glimmer-30b', 'idli-steam']:
            t=Transcript(model);t.said('Can you help?');self.assertEqual(t.text(),modes.PICK_FILES)
    def test_plain_python_no_pandas(self):
        code = 'import sys;sys.path.insert(0,sys.argv[1]);from lib import modes,minimap;assert "pandas" not in sys.modules'
        subprocess.run(['/usr/bin/python3','-I','-c',code,str(ROOT)],check=True)
    def test_identity_requires_exact_cowork_tools(self):
        t=Transcript();t.j['tools'].append({'name':'mcp__cowork__file_ask'})
        self.assertIsNone(modes.drivey_route(t.j))
    def test_reminder_and_system_after_question(self):
        t=Transcript();t.j['messages']=[{'role':'user','content':'How many? @"Drive/My folder/visits.xlsx"'},
            {'role':'user','content':'<system-reminder>Reminder</system-reminder>'}, {'role':'system','content':'Note'}]
        t.next();self.assertEqual(t.tool()['input']['paths'],['Drive/My folder/visits.xlsx'])
    def test_folder_paths(self):
        t=Transcript();t.said('Compare @Drive/Reports/');self.assertEqual(t.tool()['input']['paths'],['Drive/Reports/'])
    def test_download_failure_and_partial(self):
        t=Transcript();t.said('@Drive/missing.xlsx');t.result({'files':[],'errors':[{'error':'internal detail'}]})
        self.assertIn('with @ again',t.text());self.assertNotIn('internal detail',t.text())
        t=Transcript();t.said('@Drive/visits.xlsx');t.result({'files':FILES,'errors':[{}]})
        self.assertIn('Some files',t.text())
    def test_unsupported_files_explain_how_to_continue(self):
        t=Transcript();t.said('@Drive/report.pdf');t.result({'files':[],'unsupported':['report.pdf']})
        self.assertIn('spreadsheet copies',t.text());self.assertIn('pick them with @',t.text())
    def test_check_review_done_handoff(self):
        t=self.fetched();t.choose('Check each file');self.assertFalse(t.tool()['input']['preview_only'])
        t.result({'files':FILES,'url':'http://dashboard.localhost:8797/privacy-review?embed=1&a=left-chat',
                  'masked_question':'Original'})
        self.assertIn('[Privacy review]',t.text())
        t.said('Privacy checked');self.assertTrue(t.tool()['input']['preview_only'])
        t.result({'files':FILES,'masked_question':'Updated masked question','preview_only':True})
        self.assertIn('Updated masked question',t.tool()['input']['questions'][0]['question'])
        t.choose('Switch to Claude');self.assertTrue(t.tool()['name'].endswith('claude_handoff'))
        self.assertEqual(t.tool()['input']['question'],'How many visits?')
        t.result({'reply':'Claude has it on the right.'});self.assertIn('right',t.text())
        t.said('Something new');self.assertEqual(t.text(),modes.PICK_FILES)
    def test_accept_not_yet(self):
        t=self.fetched();t.choose("Accept Idli's choices");self.assertTrue(t.tool()['input']['preview_only'])
        t.result({'files':FILES,'masked_question':'How many?', 'preview_only':True})
        t.choose('Not yet');self.assertEqual(t.text(),'OK. Change the question or files and send again.')
    def test_dismiss_card(self):
        t=self.fetched();t.result('dismissed');self.assertIn('Nothing was sent',t.text())
    def test_privacy_failures(self):
        t=self.fetched();t.choose('Check each file');t.result({'error':'secret error code'})
        self.assertNotIn('secret',t.text())
    def mini(self):
        t=Transcript();t.said('Open Mini: Visits [visits]');self.assertEqual(t.tool()['input'],{'id':'visits'})
        t.result({'id':'visits','files':FILES,'questions':[QUESTION],'reply':'Our story\nWard: All, Garden\n![chart](views/a.svg)'})
        self.assertIn('Our story',t.text());return t
    def test_mini_open_does_not_call_model(self):
        with patch.object(minimap,'map_questions',side_effect=AssertionError('No mapping on open')):self.mini()
    def test_mini_mapping_answer(self):
        t=self.mini()
        with patch.object(minimap,'map_questions',return_value={'qid':'total','params':{'ward':'Garden'}}) as mapper:
            t.said('Visits in Garden?');mapper.assert_called_once()
        self.assertEqual(t.tool()['input'],{'id':'visits','qid':'total','params':{'ward':'Garden'}})
        t.result({'reply':'Using: visits in Garden\n12\n![chart](views/b.svg)'});self.assertIn('Using:',t.text())
    def test_mini_decline_masked_consent_context(self):
        t=self.mini()
        with patch.object(minimap,'map_questions',return_value={'qid':None}):t.said('Predict Garden next year')
        self.assertEqual(t.tool()['input']['mini_id'],'visits')
        t.result({'files':FILES,'mini_id':'visits','masked_question':'Predict PLACE_001 next year','preview_only':True})
        self.assertIn("This Mini can't answer that",t.tool()['input']['questions'][0]['question'])
        self.assertIn('PLACE_001',t.tool()['input']['questions'][0]['question'])
        t.choose('Switch to Claude');self.assertEqual(t.tool()['input']['mini_id'],'visits')
    def query_mini(self):
        t=Transcript();t.said('Open Mini: Visits [visits]')
        t.result({'id':'visits','files':FILES,'questions':[QUESTION],'can_query':True,'reply':'Our story'});return t
    def test_mini_query_service_table(self):
        t=self.query_mini()
        with patch.object(minimap,'map_questions',return_value={'qid':None}):t.said('Which ward had most visits in May?')
        self.assertIn('external service',t.text());self.assertIn('codes',t.text())
        self.assertEqual(t.tool()['input'],{'id':'visits','question':'Which ward had most visits in May?'})
        t.result({'question':'q','reply':'**Visits in May**\n\n| Ward | Visits |\n|---|---|\n| Garden | 12 |','rows':1})
        self.assertIn('Visits in May',t.text())
    def test_mini_query_asks_back_then_answers(self):
        t=self.query_mini()
        with patch.object(minimap,'map_questions',return_value={'qid':None}):t.said('big trees')
        t.result({'clarify':'What counts as big?','options':[{'label':'Girth over 100 cm','question':'Which species have trees over 100 cm girth?'},'Which are the 10 tallest trees?']})
        card=t.tool()['input']['questions'][0]
        self.assertEqual(card['header'],'Be specific');self.assertEqual(len(card['options']),3)
        self.assertEqual(card['options'][-1]['label'],'Ask Claude')
        self.assertEqual(card['options'][0]['label'],'Girth over 100 cm');t.choose(card['options'][0]['label'])
        self.assertEqual(t.tool()['input'],{'id':'visits','question':'Which species have trees over 100 cm girth?'})
    def test_mini_query_ask_claude_or_failure_offers_claude(self):
        t=self.query_mini()
        with patch.object(minimap,'map_questions',return_value={'qid':None}):t.said('big trees')
        t.result({'clarify':'What counts as big?','options':['A?','B?']});t.choose('Ask Claude')
        self.assertEqual(t.tool()['input']['mini_id'],'visits');self.assertTrue(t.tool()['input']['preview_only'])
        t=self.query_mini()
        with patch.object(minimap,'map_questions',return_value={'qid':None}):t.said('Predict Garden next year')
        t.result({'error':'The query was not a single read-only question.'})
        self.assertEqual(t.tool()['input']['question'],'Predict Garden next year');self.assertEqual(t.tool()['input']['mini_id'],'visits')
    def test_drive_mention_leaves_mini(self):
        t=self.mini();t.said('Compare @Drive/visits.xlsx');self.assertTrue(t.tool()['name'].endswith('drive_fetch'))
    def test_failed_mini_and_unknown_tool_never_fall_through(self):
        t=Transcript();t.said('Open Mini: Missing [missing]');t.result({'error':'missing'});self.assertIn('try again',t.text())
    def test_old_done_after_not_yet_or_changed_question(self):
        t=self.fetched();t.choose("Accept Idli's choices");t.result({'files':FILES,'masked_question':'Question','preview_only':True})
        t.choose('Not yet');t.said('Privacy checked');self.assertEqual(t.text(),modes.PICK_FILES)
        t=self.fetched();t.said('A different question');t.said('Privacy checked');self.assertEqual(t.text(),modes.PICK_FILES)
    def test_words(self):
        self.assertEqual(minimap.plain('up → down · done'),'up  ->  down  -  done')


class Fixture(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='idli-journey-synthetic-')
        self.base=Path(self.temp.name);self.data=self.base/'data';self.work=self.base/'work';self.bin=self.base/'bin'
        for path in [self.data/'drive', self.work, self.bin]:path.mkdir(parents=True)
        from openpyxl import Workbook
        wb=Workbook();ws=wb.active;ws.title='Visits';ws.append(['name','ward','visits'])
        ws.append(['Asha Sample','Garden',12]);ws.append(['Rehan Sample','River',8]);ws.append(['Mira Sample','Garden',5]);wb.save(self.data/'drive/visits.xlsx')
        (self.work/'analysis.py').write_text(SCRIPT)
        (self.work/'chart.csv').write_text('ward,visits\nGarden,12\nRiver,8\n')
        self.log=self.base/'paseo-log.jsonl'
        fake=self.bin/'paseo'
        fake.write_text('''#!/usr/bin/python3
import os,sys,json
from pathlib import Path
args=sys.argv[1:]
with open(os.environ['JOURNEY_FAKE_LOG'],'a') as f:f.write(json.dumps(args)+'\\n')
if args[:2]==['workspace','ls']: print(json.dumps([{'workspaceId':'ws-one','cwd':os.environ['IDLI_DATA'],'name':'Drivey'},{'workspaceId':'ws-two','cwd':os.environ['IDLI_DATA'],'name':'Other'}]))
elif args[:2]==['terminal','ls']: print(json.dumps([{'id':'term-one','workspaceId':'ws-one','name':'Claude'},{'id':'term-two','workspaceId':'ws-two','name':'Claude'}]))
elif args[0]=='ls': print(json.dumps([{'id':'left-one','labels':{'idli.ws':'ws-one','idli.left':'1'}}]))
elif args[0]=='status': print(json.dumps({'serverId':'server-one'}))
else: print('{}')
''');fake.chmod(0o755)
        self.env=patch.dict(os.environ,{'PATH':str(self.bin)+':'+os.environ['PATH'],'JOURNEY_FAKE_LOG':str(self.log),
            'IDLI_DATA':str(self.data),'COWORK_DATA_DIR':str(self.data),'IDLI_CLAUDE_WORK':str(self.work),
            'IDLI_WORKSPACE':'ws-one','PASEO_AGENT_ID':'left-one','IDLI_AUTHOR':'Sample Team','IDLI_SCANNER':''})
        self.env.start()
        self.scanner=patch.object(privacy.Scanner,'__call__',return_value=[])
        self.scanner.start()
        self.ui=patch.object(uiswitch,'show_terminal',return_value={'ok':True});self.ui.start()
        self.ensure=patch.object(formserver,'ensure',return_value=(8797,'synthetic-token-for-local-tests'));self.ensure.start()
        home.write(self.data/'.idli/home.json', {'workspace_files':{'ws-one':FILES}})
    def tearDown(self):
        self.scanner.stop();self.ensure.stop();self.ui.stop();self.env.stop();self.temp.cleanup()
    def calls(self):return [json.loads(s) for s in self.log.read_text().splitlines()] if self.log.exists() else []
    def make_view(self, ident='chart-one', workspace='ws-one', pinned=False):
        home.write(self.data/f'views/{ident}.json',{'title':'Visits by ward','spec':SPEC,'data_csv':str(self.work/'chart.csv'),
                 'workspace':workspace,'agent':'term-one','sources':['drive/visits.xlsx'],'script':str(self.work/'analysis.py'),'pinned':pinned})
        return ident
    def make_draft(self, count=2):
        qs=[dict(QUESTION,id='total-'+str(i)) for i in range(count)]
        return journey.draft_mini(self.data,'A week of visits','A simple view of our visits.',qs,'Saved scripts', 'ws-one','Sample Team')
    def edits(self, ident):
        d=journey.draft_data(self.data,ident)
        return {'name':d['name'],'goal':d['goal'],'questions':d['questions'],'charts':[v['id'] for v in d['charts']]}


class ToolTests(Fixture):
    def test_drive_fetch_uses_real_masking_fake_drive(self):
        blob=(self.data/'drive/visits.xlsx').read_bytes()
        with patch.object(drivestubs,'refresh',return_value={'visits.xlsx':{'id':'synthetic','kind':'Microsoft Excel','title':'Visits'}}),patch('lib.drivefetch.fetch',return_value=blob):
            r=tools.t_drive_fetch(['Drive/visits.xlsx'],'Asha Sample in Garden?')
        self.assertNotIn('Asha Sample',r['masked_question']);self.assertNotIn('Garden',r['masked_question'])
        self.assertEqual(home.read(self.data/'.idli/home.json')['workspace_files']['ws-one'][0]['local'],'drive/visits.xlsx')
    def test_drivey_does_not_download_unmaskable_documents(self):
        entries={'report.pdf':{'id':'synthetic-pdf','kind':'PDF','title':'Report'}}
        with patch.object(drivestubs,'refresh',return_value=entries),patch('lib.drivefetch.fetch',side_effect=AssertionError('Must not download unmaskable files')):
            result=tools.t_drive_fetch(['Drive/report.pdf'],'What is in this report?')
        self.assertEqual(result['files'],[]);self.assertEqual(result['unsupported'],['Report'])
        self.assertFalse((self.data/'drive/report.pdf').exists())
    def test_review_toggles_and_done_target_idempotent(self):
        r=tools.t_privacy_review_open(FILES,'Asha Sample in Garden?')
        qs=urllib.parse.parse_qs(urllib.parse.urlparse(r['url']).query);ident=qs['id'][0]
        self.assertEqual(qs['a'],['left-one']);self.assertEqual(qs['embed'],['1'])
        before=journey.review_data(self.data,ident);self.assertNotIn('Asha Sample',before['masked_question'])
        columns=before['reviews'][0]['tabs'][0]['columns'];columns['ward']=False
        after=journey.review_change(self.data,ident,'drive/visits.xlsx',columns)
        self.assertIn('Garden',after['masked_question'])
        journey.review_done(self.data,ident);journey.review_done(self.data,ident)
        self.assertEqual([c for c in self.calls() if c[0]=='send'],[['send','--no-wait','left-one','Privacy checked']])
        with self.assertRaises(ValueError):journey.review_change(self.data,ident,'drive/visits.xlsx',columns)
    def test_stale_review_does_not_notify(self):
        a=tools.t_privacy_review_open(FILES,'First?');b=tools.t_privacy_review_open(FILES,'Second?')
        ident=urllib.parse.parse_qs(urllib.parse.urlparse(a['url']).query)['id'][0]
        with self.assertRaisesRegex(ValueError,'newer review'):journey.review_done(self.data,ident)
        self.assertFalse(self.calls())
    def test_handoff_exact_line_enter_focus_and_workspace(self):
        tools.t_claude_handoff(FILES,'How many visits?')
        sends=[c for c in self.calls() if c[:2]==['terminal','send-keys']]
        self.assertEqual(sends,[['terminal','send-keys','-l','term-one','Files (masked by Idli): drive/visits.xlsx. How many visits?'],
                               ['terminal','send-keys','-l','term-one','\r']])
        uiswitch.show_terminal.assert_called_once_with('ws-one','term-one','right')
        with self.assertRaises(ValueError):home.send(self.data,FILES,'Question','wrong-workspace')
    def test_show_opens_right_never_left(self):
        with patch.object(uiswitch,'open_url',return_value={'ok':True}) as op:
            r=idli_mcp.idli_show('Visits',SPEC,str(self.work/'chart.csv'),['drive/visits.xlsx'],str(self.work/'analysis.py'))
        self.assertTrue(r['shown']);op.assert_called_once_with('ws-one',r['url'],side='right',focus=True)
        self.assertFalse(any(c[0]=='send' for c in self.calls()))
    def test_insert_no_enter_only_own_terminal(self):
        home.claude_insert(self.data,'ws-one','About this chart: ward = Garden ')
        self.assertEqual([c for c in self.calls() if c[:2]==['terminal','send-keys']],
                         [['terminal','send-keys','-l','term-one','About this chart: ward = Garden ']])
    def test_draft_pins_local_save_not_public_until_saved(self):
        self.make_view(pinned=True);self.make_view('other','ws-two',True);self.make_view('not-pinned')
        ident=self.make_draft();d=journey.draft_data(self.data,ident)
        self.assertEqual([v['id'] for v in d['charts']],['chart-one']);self.assertEqual(home.minis(self.data),[])
        edits=self.edits(ident);edits.update(name='A better title',goal='Our new story',charts=[])
        edits['questions']=edits['questions'][:1]
        result=journey.save_draft(self.data,ident,edits)
        self.assertEqual(len(home.minis(self.data)),1)
        saved=home.read(home.object_path(self.data,'minis',result['id']))
        self.assertEqual(saved['goal'],'Our new story');self.assertEqual(saved['charts'],[])
        self.assertEqual(home.run_mini(self.data,result['id'],saved['questions'][0]['id'],{})['text'],'Visits: 12')
        self.assertEqual(journey.save_draft(self.data,ident,edits),result)
    def test_add_to_mini_preserves_old_questions_and_limits(self):
        first=self.make_draft(1);saved=journey.save_draft(self.data,first,self.edits(first))
        state=home.read(self.data/'.idli/home.json');state['workspace_minis']={'ws-one':saved['id']};home.write(self.data/'.idli/home.json',state)
        second=self.make_draft(1);self.assertEqual(journey.draft_data(self.data,second)['source_name'],'A week of visits')
        journey.save_draft(self.data,second,self.edits(second),'add')
        m=home.read(home.object_path(self.data,'minis',saved['id']));self.assertEqual(len(m['questions']),2)
        self.assertEqual(len({q['id'] for q in m['questions']}),2)
        third=self.make_draft(7)
        with self.assertRaisesRegex(ValueError,'more than eight'):journey.save_draft(self.data,third,self.edits(third),'add')
        self.assertEqual(len(home.read(home.object_path(self.data,'minis',saved['id']))['questions']),2)
    def test_mini_open_story_questions_charts_and_context(self):
        self.make_view(pinned=True);ident=self.make_draft(1);r=journey.save_draft(self.data,ident,self.edits(ident))
        m=tools.t_mini_open(r['id']);self.assertIn('A simple view',m['reply']);self.assertIn('ward: Garden or all',m['reply']);self.assertIn('embed=1',m['reply']);self.assertIn('ws=ws-one',m['reply']);self.assertEqual(m['files'],FILES)
        answer=tools.t_mini_ask(r['id'],'total-0',{'ward':'Garden'});self.assertIn('Answered with:',answer['reply']);self.assertIn('views/',answer['reply'])
    def test_draft_tool_and_bad_script_fail_before_editor(self):
        with patch.object(uiswitch,'open_url',return_value={'ok':True}):
            r=idli_mcp.idli_draft_mini('Visits','Story',[QUESTION],'Scripts');self.assertTrue(r['opened'])
        (self.work/'analysis.py').write_text('raise RuntimeError("private internal detail")')
        with self.assertRaisesRegex(ValueError,'Ask Claude'):self.make_draft(1)
    def test_bad_edits_and_paths(self):
        ident=self.make_draft(1);edits=self.edits(ident);edits['questions'][0]['id']='alien'
        with self.assertRaises(ValueError):journey.save_draft(self.data,ident,edits)
        with self.assertRaises(ValueError):journey.pin(self.data,'../outside',True)
        with self.assertRaises(ValueError):home.claude_insert(self.data,'ws-one','one\ntwo')
    def test_open_url_bridge_exact_arguments(self):
        with patch.object(uiswitch,'_targets',return_value=[{'type':'page','url':'paseo://app','webSocketDebuggerUrl':'fake'}]),patch.object(uiswitch,'_ws_eval',return_value=True) as evaluate:
            self.assertTrue(uiswitch.open_url('ws-one','http://dashboard.localhost:8797/view?id=test',focus=False)['ok'])
        expression=evaluate.call_args.args[1]
        self.assertIn('window.__idliOpenTab',expression);self.assertIn('"side": "right"',expression);self.assertIn('"focus": false',expression)
    def test_end_to_end_review_to_handoff(self):
        t=Transcript();t.said('Visits for Asha Sample? @Drive/visits.xlsx')
        with patch.object(drivestubs,'fetch',return_value={'files':FILES}):
            t.result(tools.t_drive_fetch(**t.tool()['input']))
        self.assertFalse(any(c[0]=='send' or c[:2]==['terminal','send-keys'] for c in self.calls()))
        t.choose('Check each file');review=tools.t_privacy_review_open(**t.tool()['input']);t.result(review)
        ident=urllib.parse.parse_qs(urllib.parse.urlparse(review['url']).query)['id'][0]
        journey.review_done(self.data,ident)
        t.said('Privacy checked');t.result(tools.t_privacy_review_open(**t.tool()['input']))
        question=t.tool()['input']['questions'][0]['question'];self.assertNotIn('Asha Sample',question);self.assertIn('NAME_',question)
        t.choose('Switch to Claude');t.result(tools.t_claude_handoff(**t.tool()['input']))
        self.assertEqual(t.text(),'Sent to Claude on the right.')
        self.assertEqual([c for c in self.calls() if c[0]=='send'],[['send','--no-wait','left-one','Privacy checked']])
        self.assertEqual([c for c in self.calls() if c[:2]==['terminal','send-keys']][-1][-1],'\r')
    def test_mini_handoff_context_and_no_preview_send(self):
        first=self.make_draft(1);saved=journey.save_draft(self.data,first,self.edits(first))
        r=tools.t_privacy_review_open(FILES,'Asha Sample?',preview_only=True,mini_id=saved['id'])
        self.assertNotIn('url',r);self.assertFalse(self.calls());self.assertNotIn('Asha Sample',r['masked_question'])
        tools.t_claude_handoff(FILES,'Asha Sample?',mini_id=saved['id'])
        line=next(c[-1] for c in self.calls() if c[:2]==['terminal','send-keys'])
        self.assertIn('Mini context: A week of visits.',line)
        self.assertEqual(home.read(self.data/'.idli/home.json')['workspace_minis']['ws-one'],saved['id'])
    def test_stale_review_after_starting_new_files(self):
        r=tools.t_privacy_review_open(FILES,'First?');ident=urllib.parse.parse_qs(urllib.parse.urlparse(r['url']).query)['id'][0]
        with patch.object(drivestubs,'fetch',return_value={'files':FILES}):tools.t_drive_fetch(['Drive/visits.xlsx'],'Second?')
        with self.assertRaisesRegex(ValueError,'newer review'):journey.review_done(self.data,ident)
    def test_stdio_offers_draft_instead_of_direct_publish(self):
        request=json.dumps({'jsonrpc':'2.0','id':1,'method':'tools/list'})+'\n'
        result=subprocess.run([sys.executable,'-I',str(ROOT/'lib/idli_mcp.py')],input=request,text=True,capture_output=True,check=True)
        offered={t['name'] for t in json.loads(result.stdout)['result']['tools']}
        self.assertEqual(offered,{'idli_show','idli_draft_mini','unmask','lookup'})
    def test_launcher_installs_command(self):
        self.assertIn('.claude/commands/mini.md',(ROOT/'desktop/claude-masked.sh').read_text())
        self.assertIn('idli_draft_mini',(ROOT/'idli/claude-commands/mini.md').read_text())
    def test_bootstrap_exact_toolset(self):
        import ast
        tree=ast.parse((ROOT/'desktop/idli-bootstrap.py').read_text())
        value=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='TOOLSETS' for t in n.targets))
        self.assertEqual(set(value['Drivey']),modes.DRIVEY_TOOLS)


if __name__=='__main__':unittest.main()
