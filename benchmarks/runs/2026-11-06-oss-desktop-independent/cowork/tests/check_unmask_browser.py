"""Headless synthetic consent and newsroom checks. Run with the journey test Python."""
import csv
import json
from pathlib import Path
import re
import sys
import threading
import unittest
import urllib.error
import urllib.parse
import urllib.request
from http.server import ThreadingHTTPServer
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parent))
from test_journey import Fixture, home, privacy, formserver, uiswitch, idli_mcp
from lib import reveals, ccproxy
from playwright.sync_api import sync_playwright, expect

ARTIFACTS=Path(__file__).resolve().parents[5]/'benchmarks/runs/2026-11-14-unmask-visuals'
SHOTS=ARTIFACTS/'shots'
TEMPLATES=Path(__file__).resolve().parents[1]/'idli/claude-skills/newsroom-charts/templates'


def rows_for(name):
    basic=[{'group':'Garden','count':48,'low':35,'high':60},
           {'group':'River','count':24,'low':20,'high':28},
           {'group':'Lake','count':16,'low':13,'high':19}]
    if name=='slope':
        return [{'group':g,'period':p,'count':v} for g,b,a in [('Garden',20,48),('River',18,24),('Lake',15,16)] for p,v in [('Before',b),('After',a)]]
    if name in ('heat-table','small-multiples'):
        return [{'group':r['group'],'month':m,'count':int(r['count']*factor)} for r in basic for m,factor in [('Jan',.5),('Feb',.7),('Mar',1)]]
    if name=='gps-points':
        return [{'group':'Garden','count':12,'lat':18.52,'lon':73.85},{'group':'River','count':8,'lat':18.58,'lon':73.92},{'group':'Lake','count':6,'lat':18.62,'lon':73.80}]
    if name=='district-map':
        return [{'district':' Pune district ','state':'Maharashtra','count':48},
                {'district':'nashikk','state':'Maharashtra','count':24},
                {'district':'Thane','state':'Maharashtra','count':16},
                {'district':'Imaginary district','state':'Maharashtra','count':5}]
    return basic


class UnmaskBrowserTests(Fixture):
    def setUp(self):
        super().setUp()
        self.server=ThreadingHTTPServer(('127.0.0.1',0),formserver.make_handler(formserver.Files(self.data),'synthetic-local-token'))
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
        self.port=self.server.server_port
        self.ensure.return_value=(self.port,'synthetic-local-token')
        self.runtime=sync_playwright().start();self.browser=self.runtime.chromium.launch(headless=True)
        self.errors=[];SHOTS.mkdir(parents=True,exist_ok=True)
        privacy.set(self.data,'drive/visits.xlsx',mode='mask',columns={'name':True,'ward':True})
    def tearDown(self):
        self.browser.close();self.runtime.stop();self.server.shutdown();self.server.server_close();self.thread.join();super().tearDown()
    def page(self,scheme):
        p=self.browser.new_page(viewport={'width':360,'height':900},color_scheme=scheme)
        p.on('pageerror',lambda e:self.errors.append(str(e)))
        p.on('request',lambda r:self.errors.append('External chart request') if not r.url.startswith(f'http://127.0.0.1:{self.port}/') else None)
        return p
    def url(self,route,**query):return f'http://127.0.0.1:{self.port}/{route}?'+urllib.parse.urlencode({'t':'synthetic-local-token',**query})
    def check(self,p):
        self.assertTrue(p.evaluate('document.documentElement.scrollWidth<=innerWidth+1'))
        self.assertFalse(re.search('[\u2190-\u21ff\u27f0-\u27ff·]',p.locator('body').inner_text()))
        self.assertEqual(self.errors,[])
    def shot(self,p,name):p.screenshot(path=str(SHOTS/(name+'.png')),animations='disabled')
    def click_mark(self,p,mark,name,button='left'):
        if name=='district-map':
            # Find a visible point inside the actual polygon away from its direct label.
            point=mark.evaluate("""el=>{const r=el.getBoundingClientRect();for(let y=.1;y<1;y+=.1)for(let x=.1;x<1;x+=.1){const px=r.x+r.width*x,py=r.y+r.height*y;if(document.elementFromPoint(px,py)===el)return {x:px,y:py};}return null;}""")
            self.assertIsNotNone(point);p.mouse.click(point['x'],point['y'],button=button)
        else:mark.click(button=button,**({'position':{'x':4,'y':4}} if name=='heat-table' else {}))
    def test_consent_real_tool_approve_deny_timeout_and_lookup(self):
        code=privacy.session_vault(self.data).forward['garden']
        for scheme in ['light','dark']:
            for choice in ['approve','deny','timeout','lookup','lookup-deny','lookup-timeout']:
                opened=threading.Event();seen={};result={}
                def open_page(workspace,url,**kwargs):
                    seen.update(workspace=workspace,url=url,**kwargs);opened.set();return {'ok':True}
                def run():
                    try:
                        result['out']=idli_mcp.lookup(code,'Services in {value}','Check services') if choice.startswith('lookup') else idli_mcp.unmask(code,'Match the published table')
                    except Exception as e:result['error']=type(e).__name__
                with patch.object(uiswitch,'open_url',side_effect=open_page),patch.object(reveals,'search',return_value=[{'title':'Garden service','url':'https://example.test/Garden','snippet':'Asha Sample in Garden'}]) as search:
                    worker=threading.Thread(target=run,daemon=True);worker.start();self.assertTrue(opened.wait(5))
                    self.assertEqual((seen['workspace'],seen['side'],seen['focus']),('ws-one','right',True))
                    ident=urllib.parse.parse_qs(urllib.parse.urlparse(seen['url']).query)['id'][0]
                    if choice.endswith('timeout'):
                        path=self.data/f'.idli/consents/{ident}.json'
                        with privacy.session_lock(self.data):
                            record=home.read(path);record['expires']=0;home.write(path,record)
                    p=self.page(scheme);p.goto(self.url('consent',id=ident,ws='ws-one'))
                    expect(p.locator('#request')).to_be_visible();expect(p.locator('#details')).to_contain_text('Garden')
                    if choice.endswith('timeout'):expect(p.locator('#status')).to_contain_text('expired')
                    else:
                        if choice.startswith('lookup'):
                            expect(p.locator('#intro')).to_contain_text('Claude will not see the value')
                            expect(p.locator('#search')).to_have_text('Search: Services in Garden')
                        self.shot(p,f'consent-{choice}-{scheme}-360')
                        p.locator('#deny' if choice.endswith('deny') else '#approve').click()
                        expect(p.locator('#status')).to_have_text('Kept hidden.' if choice.endswith('deny') else 'Allowed.')
                    worker.join(5);self.assertFalse(worker.is_alive());self.assertNotIn('error',result)
                    if choice=='approve':self.assertEqual(result['out'],{'code':code,'value':'Garden'})
                    elif choice=='lookup':
                        self.assertEqual(result['out']['code'],code)
                        self.assertNotIn('Garden',json.dumps(result['out']))
                        self.assertNotIn('Asha Sample',json.dumps(result['out']))
                    else:self.assertIn('refused',result['out'])
                    if choice!='lookup':search.assert_not_called()
                    self.check(p);self.shot(p,f'consent-{choice}-done-{scheme}-360');p.close()
            # Two reveals after two theme runs remain within the initial budget.
        self.assertEqual(reveals.remaining(self.data,'ws-one'),1)
    def test_reveals_hide_budget_and_no_unauthenticated_mutation(self):
        code=privacy.session_vault(self.data).forward['garden']
        for scheme in ['light','dark']:
            ident=reveals.create(self.data,code,'Match a public table','ws-one')['id'];reveals.decide(self.data,ident,True)
            lookup=reveals.create(self.data,code,'Check services','ws-one','lookup','Services {value}')['id'];reveals.decide(self.data,lookup,True)
            p=self.page(scheme);p.goto(self.url('reveals',ws='ws-one'))
            expect(p.locator('#items')).to_contain_text('Garden');expect(p.locator('#items')).to_contain_text('Search allowed')
            self.check(p);self.shot(p,f'reveals-{scheme}-360')
            before=reveals.remaining(self.data,'ws-one');p.get_by_role('button',name='Allow 3 more',exact=True).click()
            expect(p.locator('#budget')).to_have_text(str(before+3)+' reveals left in this workspace.')
            transform=ccproxy.Transformer(self.data);self.assertFalse(transform.leaks({'messages':[{'content':'Garden'}]}))
            p.locator('[data-kind=unmask]').get_by_role('button',name='Hide again',exact=True).last.click()
            expect(p.locator('[data-kind=unmask]')).to_have_count(0)
            transform.refresh();self.assertTrue(transform.leaks({'messages':[{'content':'Garden'}]}))
            self.check(p);p.close()
        for route in ['consent?id='+ident,'reveals','api/consent?id='+ident,'api/reveals']:
            with self.assertRaises(urllib.error.HTTPError) as error:urllib.request.urlopen(f'http://127.0.0.1:{self.port}/'+route)
            self.assertEqual(error.exception.code,403)
        req=urllib.request.Request(f'http://127.0.0.1:{self.port}/api/reveals/more',b'{"workspace":"ws-one"}',{'Content-Type':'application/json'})
        with self.assertRaises(urllib.error.HTTPError) as error:urllib.request.urlopen(req)
        self.assertEqual(error.exception.code,403)
    def test_every_template_render_sources_and_copy_light_dark_360(self):
        report=[]
        for template in sorted(TEMPLATES.glob('*.json')):
            name=template.name.removesuffix('.vl.json');spec=json.loads(template.read_text());rows=rows_for(name)
            path=self.work/(name+'.csv')
            with path.open('w',newline='') as f:
                writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
            with patch.object(uiswitch,'open_url',return_value={'ok':True}):
                out=idli_mcp.idli_show(spec['title']['subtitle'],spec,str(path),['drive/visits.xlsx'],str(self.work/'analysis.py'))
            self.assertTrue(out['shown'])
            ident=urllib.parse.parse_qs(urllib.parse.urlparse(out['url']).query)['id'][0]
            for scheme in ['light','dark']:
                p=self.page(scheme);p.goto(self.url('view',id=ident));expect(p.locator('#viz svg')).to_be_visible()
                expect(p.locator('#pin')).to_be_enabled();self.check(p);self.shot(p,f'{name}-{scheme}-360')
                if name=='district-map':
                    expect(p.locator('#description')).to_contain_text('Unmatched districts: Imaginary district')
                    mark=p.locator('#viz .mark-shape.role-mark path').last
                elif name in ('gps-points','comparison-dots','annotated-outlier','ranged-dots','slope','small-multiples'):
                    mark=p.locator('#viz .mark-symbol.role-mark path').first
                else:mark=p.locator('#viz .mark-rect.role-mark path').first
                self.click_mark(p,mark,name)
                p.get_by_role('button',name='Where did this come from?',exact=True).click()
                expect(p.locator('#pop')).to_contain_text('drive/visits.xlsx')
                expect(p.locator('#pop')).to_contain_text('This part of the chart')
                self.check(p);self.shot(p,f'{name}-source-{scheme}-360');p.keyboard.press('Escape')
                self.click_mark(p,mark,name,button='right')
                expect(p.get_by_role('menuitem',name='Copy to Claude',exact=True)).to_be_visible()
                self.shot(p,f'{name}-menu-{scheme}-360');p.get_by_role('menuitem',name='Copy to Claude',exact=True).click()
                expect(p.locator('#pop')).to_be_hidden()
                sent=[c for c in self.calls() if c[:2]==['terminal','send-keys']][-1]
                self.assertEqual(sent[3],'term-one');self.assertIn('redacted(drive/visits.xlsx)',sent[-1])
                self.assertIn('analysis.py',sent[-1]);self.assertNotEqual(sent[-1],'\r')
                self.assertIn('district =' if name=='district-map' else 'group =',sent[-1])
                self.check(p);p.close();report.append({'template':name,'theme':scheme,'width':360,'render':True,'source':True,'copy':True})
        for name in ['india-states.topo.json','india-districts.topo.json']:
            with urllib.request.urlopen(f'http://127.0.0.1:{self.port}/geo/'+name) as r:self.assertEqual(json.load(r)['type'],'Topology')
        (ARTIFACTS/'browser-validation.json').write_text(json.dumps(report,indent=2)+'\n')

if __name__=='__main__':unittest.main(verbosity=2)
