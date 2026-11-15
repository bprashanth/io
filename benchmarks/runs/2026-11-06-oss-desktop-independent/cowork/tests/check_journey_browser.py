"""Headless Chromium checks against the real loopback server, using synthetic files and a fake Paseo.
Run with a Python containing pandas, duckdb, openpyxl, vl_convert and Playwright.
"""
import json
from pathlib import Path
import re
import sys
import threading
import unittest
import urllib.parse
import urllib.request
import urllib.error
from http.server import ThreadingHTTPServer
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parent))
from test_journey import Fixture, FILES, home, journey, formserver, uiswitch, privacy
from playwright.sync_api import sync_playwright, expect

# Fixed relative to the repo so this works in a clean checkout without the task file.
SHOTS=Path(__file__).resolve().parents[5]/'benchmarks/runs/2026-11-14-drivey-journey/page-shots'


class BrowserTests(Fixture):
    def setUp(self):
        super().setUp()
        self.server=ThreadingHTTPServer(('127.0.0.1',0),formserver.make_handler(formserver.Files(self.data),'synthetic-local-token'))
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
        self.port=self.server.server_port
        self.runtime=sync_playwright().start()
        self.browser=self.runtime.chromium.launch(headless=True)
        self.errors=[]
        SHOTS.mkdir(exist_ok=True)
    def tearDown(self):
        self.browser.close();self.runtime.stop();self.server.shutdown();self.server.server_close();self.thread.join();super().tearDown()
    def page(self, scheme='light',width=360):
        p=self.browser.new_page(viewport={'width':width,'height':820},color_scheme=scheme,device_scale_factor=1)
        p.on('pageerror',lambda e:self.errors.append(str(e)))
        return p
    def url(self, route, **query):
        return f'http://127.0.0.1:{self.port}/{route}?'+urllib.parse.urlencode({'t':'synthetic-local-token',**query})
    def check_layout(self,page):
        self.assertTrue(page.evaluate('document.documentElement.scrollWidth <= innerWidth+1'))
        self.assertFalse(re.search('[\u2190-\u21ff\u27f0-\u27ff·]',page.locator('body').inner_text()))
        self.assertEqual(self.errors,[])
    def shot(self,page,name):page.screenshot(path=str(SHOTS/name),full_page=False,animations='disabled')
    def review(self):
        result=journey.review_open(self.data,FILES,'How many visits for Asha Sample in Garden?', 'left-one','ws-one')
        return urllib.parse.parse_qs(urllib.parse.urlparse(result['url']).query)['id'][0]
    def test_review_switches_done_retry_and_height(self):
        for scheme in ['light','dark']:
            if scheme=='dark':
                columns=privacy.get(self.data,'drive/visits.xlsx')['columns'];columns['ward']=True
                privacy.set(self.data,'drive/visits.xlsx',columns=columns)
            ident=self.review();p=self.page(scheme)
            p.add_init_script('window.heights=[];addEventListener("message",e=>{if(e.data?.type==="idli-height")window.heights.push(e.data.px);});')
            p.goto(self.url('privacy-review',id=ident,embed=1,a='left-one'))
            expect(p.locator('#reviews')).to_have_attribute('aria-busy','false')
            p.locator('details.visible-group').evaluate_all('ds=>ds.forEach(d=>d.open=true)')
            expect(p.get_by_role('switch')).to_have_count(3)
            name=p.get_by_role('switch',name='Hide Name in Visits',exact=True)
            ward=p.get_by_role('switch',name='Hide Ward in Visits',exact=True)
            expect(name).to_be_checked();expect(ward).to_be_checked()
            self.assertNotIn('Asha Sample',p.locator('#masked').inner_text())
            ward.uncheck();expect(p.locator('#status')).to_have_text('Saved.');expect(p.locator('#masked')).to_contain_text('Garden')
            self.check_layout(p);self.shot(p,f'privacy-review-{scheme}-360.png')
            p.locator('#question-card').scroll_into_view_if_needed();self.shot(p,f'privacy-question-{scheme}-360.png')
            p.get_by_role('button',name='Done',exact=True).click();expect(p.locator('#status')).to_contain_text('Privacy checked')
            expect(p.get_by_role('button',name='Done',exact=True)).to_be_disabled()
            p.reload();expect(p.locator('#reviews')).to_have_attribute('aria-busy','false');expect(p.get_by_role('button',name='Done',exact=True)).to_be_disabled()
            self.assertTrue(p.evaluate('window.heights.some(h=>h>360)'))
            self.check_layout(p);p.close()
        sends=[c for c in self.calls() if c[0]=='send'];self.assertEqual(len(sends),2)
        self.assertTrue(all(c[-2:]==['left-one','Privacy checked'] for c in sends))
        # An unavailable page has a real retry action, and does not expose exceptions.
        p=self.page();p.goto(self.url('privacy-review',id='missing'))
        expect(p.get_by_role('button',name='Try again')).to_be_visible();self.assertNotIn('FileNotFoundError',p.locator('body').inner_text());self.check_layout(p)
    def test_chart_pin_zoom_popover_context_and_back(self):
        self.make_view()
        for scheme in ['light','dark']:
            p=self.page(scheme);p.goto(self.url('view',id='chart-one'))
            expect(p.locator('#viz svg')).to_be_visible()
            expect(p.get_by_role('button',name='Pin',exact=True)).to_be_enabled()
            p.get_by_role('button',name='Pin',exact=True).click();expect(p.get_by_role('button',name='Pinned',exact=True)).to_be_visible()
            self.assertTrue(home.read(self.data/'views/chart-one.json')['pinned'])
            before=p.locator('#viz svg').bounding_box()['width']
            p.get_by_role('button',name='Zoom: Fit',exact=True).click();expect(p.get_by_role('button',name='Zoom: Bigger')).to_be_visible()
            p.wait_for_function('document.querySelector("#viz svg").getAttribute("width") > '+str(before))
            p.get_by_role('button',name='Zoom: Bigger').click();expect(p.get_by_role('button',name='Zoom: Fit')).to_be_visible()
            mark=p.locator('#viz .mark-rect.role-mark path').first
            mark.click();expect(p.get_by_role('button',name='Where did this come from?',exact=True)).to_be_visible()
            p.get_by_role('button',name='Where did this come from?',exact=True).click()
            expect(p.locator('#pop')).to_contain_text('drive/visits.xlsx');expect(p.locator('#pop')).to_contain_text('Garden')
            self.shot(p,f'chart-source-{scheme}-360.png');p.get_by_role('button',name='Close',exact=True).click();expect(p.locator('#pop')).to_be_hidden()
            mark.click();expect(p.locator('#pop')).to_be_visible()
            box=p.locator('#viz svg').bounding_box();p.mouse.click(box['x']+3,box['y']+3);expect(p.locator('#pop')).to_be_hidden()
            mark.click();expect(p.locator('#pop')).to_be_visible();p.keyboard.press('Escape');expect(p.locator('#pop')).to_be_hidden()
            mark.click(button='right');expect(p.get_by_role('menuitem',name='Copy to Claude',exact=True)).to_be_visible()
            p.get_by_role('menuitem',name='Copy to Claude',exact=True).click();expect(p.locator('#pop')).to_be_hidden()
            context=[c for c in self.calls() if c[:2]==['terminal','send-keys']][-1]
            self.assertEqual(context[3],'term-one');self.assertIn('Garden',context[-1]);self.assertIn('analysis.py',context[-1]);self.assertNotEqual(context[-1],'\r')
            self.check_layout(p);self.shot(p,f'chart-{scheme}-360.png')
            p.get_by_role('button',name='Back to Claude',exact=True).click();expect(p.locator('#status')).to_contain_text('Claude is ready')
            p.get_by_role('button',name='Pinned',exact=True).click();expect(p.get_by_role('button',name='Pin',exact=True)).to_be_visible();p.close()
        p=self.page(width=900);p.goto(self.url('view',id='chart-one'));expect(p.locator('#viz svg')).to_be_visible();self.check_layout(p);self.shot(p,'chart-light-900.png')
        embedded=self.page();embedded.goto(self.url('view',id='chart-one',embed=1));expect(embedded.locator('#viz svg')).to_be_visible();expect(embedded.locator('#pin')).to_be_visible();self.check_layout(embedded)
        inmini=self.page();inmini.goto(self.url('view',id='chart-one',embed=1,pin=0));expect(inmini.locator('#viz svg')).to_be_visible();expect(inmini.locator('#pin')).to_be_hidden()
    def test_composite_chart_fits_and_zooms(self):
        self.make_view('facets')
        path=self.data/'views/facets.json';view=home.read(path)
        view['spec']={'facet':{'field':'ward','type':'nominal'},'spec':{'width':320,'height':240,'mark':'bar',
            'encoding':{'x':{'field':'ward','type':'nominal'},'y':{'field':'visits','type':'quantitative'}}}}
        home.write(path,view)
        p=self.page();p.goto(self.url('view',id='facets'));expect(p.locator('#viz svg')).to_be_visible()
        width=p.locator('#viz svg').bounding_box()['width'];self.assertLess(width,340)
        p.get_by_role('button',name='Zoom: Fit',exact=True).click()
        p.wait_for_function('document.querySelector("#viz svg").getAttribute("width") > '+str(width))
        p.get_by_role('button',name='Zoom: Bigger',exact=True).click()
        p.wait_for_function('document.querySelector("#viz svg").getAttribute("width") < 340')
        self.check_layout(p);self.shot(p,'chart-facets-light-360.png')
    def test_mini_page_edit_drag_save_and_open(self):
        """The draft in the chat is the Mini as colleagues will see it: edit text in place, drag, remove, save."""
        self.make_view(pinned=True)
        for scheme in ['light','dark']:
            ident=self.make_draft();p=self.page(scheme,width=460)
            p.add_init_script('window.heights=[];addEventListener("message",e=>{if(e.data?.type==="idli-height")window.heights.push(e.data.px);});')
            p.goto(self.url('mini-card',id=ident,embed=1,ws='ws-one'))
            expect(p.locator('#page')).to_have_attribute('aria-busy','false');expect(p.locator('#note')).to_be_visible()
            expect(p.locator('.blk')).to_have_count(2);expect(p.locator('.blk.chart iframe')).to_have_count(1)
            self.assertIn('pin=0',p.locator('.blk.chart iframe').get_attribute('src'))
            self.check_layout(p);self.shot(p,f'mini-card-draft-{scheme}-460.png')
            narrow=self.page(scheme,width=220);narrow.goto(self.url('mini-card',id=ident,embed=1))  # a squeezed left pane
            expect(narrow.locator('li.q')).to_have_count(2);narrow.locator('li.q').first.hover()
            self.assertLess(narrow.locator('li.q .words').first.bounding_box()['height'],120);self.check_layout(narrow);narrow.close()
            title=p.locator('#name');title.click();p.keyboard.press('Control+A');p.keyboard.type('Visits we can plan around');p.keyboard.press('Enter')
            p.locator('.blk.text .body').first.click();ta=p.locator('textarea.md');expect(ta).to_be_visible()
            ta.fill('Garden had the **most** visits.\n\n- Start with Garden\n- Then River');p.locator('h2').click()
            expect(p.locator('.blk.text li')).to_have_count(2);expect(p.locator('.blk.text b')).to_have_text('most')
            p.locator('li.q').nth(1).hover();p.get_by_role('button',name='Remove this question').nth(1).click()
            expect(p.locator('li.q')).to_have_count(1);expect(p.get_by_role('button',name='Undo')).to_be_visible()
            q=p.locator('li.q .words');q.click();p.keyboard.press('Control+A');p.keyboard.type('How many visits should we review?')
            p.locator('.blk.chart').hover();p.locator('.blk.chart [data-move]').drag_to(p.locator('.blk.text'),target_position={'x':20,'y':4})
            expect(p.locator('.blk').first).to_have_class(re.compile('chart'))
            p.locator('.blk.text').hover();p.locator('.blk.text [data-move]').focus();p.keyboard.press('ArrowUp')  # keys move it too
            expect(p.locator('.blk').first).to_have_class(re.compile('text'))
            p.get_by_role('button',name='Add text',exact=True).click();p.locator('textarea.md').fill('### Next step\nCheck River in June.');p.locator('h2').click()
            expect(p.locator('.blk.text h3')).to_have_text('Next step')
            self.assertGreater(p.evaluate('window.heights.at(-1)'),300)
            p.wait_for_timeout(800);kept=journey.card_data(self.data,draft=ident)  # kept as it changes (the enlarged copy reads this)
            self.assertEqual(kept['name'],'Visits we can plan around');self.assertEqual(len(kept['questions']),1)
            p.evaluate('scrollTo(0,0)');self.check_layout(p);self.shot(p,f'mini-card-edited-{scheme}-460.png')
            p.get_by_role('button',name='Save Mini',exact=True).click();expect(p.locator('#saved')).to_be_visible()
            expect(p.locator('#note')).to_be_hidden();expect(p.locator('.tools')).to_have_count(0)
            saved=journey.draft_data(self.data,ident)['saved_id'];m=home.read(home.object_path(self.data,'minis',saved))
            self.assertEqual(m['name'],'Visits we can plan around');self.assertEqual(len(m['questions']),1)
            self.assertEqual([b['type'] for b in m['blocks']],['text','chart','text']);self.assertEqual(m['questions'][0]['question'],'How many visits should we review?')
            with urllib.request.urlopen(f'http://127.0.0.1:{self.port}/api/minis-public') as r:cartridges=json.load(r)
            self.assertIn(saved,[c['id'] for c in cartridges]);self.check_layout(p);p.close()
            # A colleague clicks the cartridge: the same page, nothing to edit.
            o=self.page(scheme,width=460);o.goto(self.url('mini-card',mini=saved,embed=1,ws='ws-two'))
            expect(o.locator('#name')).to_have_text('Visits we can plan around');expect(o.locator('.blk')).to_have_count(3)
            expect(o.locator('#actions')).to_be_hidden();self.assertEqual(o.locator('#name').get_attribute('contenteditable'),'false')
            self.assertIn('ws=ws-two',o.locator('iframe').get_attribute('src'))
            o.wait_for_timeout(1200);self.check_layout(o);self.shot(o,f'mini-card-opened-{scheme}-460.png');o.close()
    def test_privacy_pages_and_writes_require_token(self):
        ident=self.review()
        paths=['/privacy-review?id='+ident,'/api/review?id='+ident,'/mini-editor?id=draft','/api/mini-draft?id=draft']
        for path in paths:
            with self.assertRaises(urllib.error.HTTPError) as err:
                urllib.request.urlopen(f'http://127.0.0.1:{self.port}'+path)
            self.assertEqual(err.exception.code,403)
        request=urllib.request.Request(f'http://127.0.0.1:{self.port}/api/review-done',json.dumps({'id':ident}).encode(),{'Content-Type':'application/json'})
        with self.assertRaises(urllib.error.HTTPError) as err:urllib.request.urlopen(request)
        self.assertEqual(err.exception.code,403);self.assertFalse(self.calls())
    def test_editor_add_and_new_from_mini(self):
        initial=self.make_draft(1);saved=journey.save_draft(self.data,initial,self.edits(initial))
        home.mini_open(self.data,saved['id'],'ws-one')
        self.make_view(pinned=True)
        for action in ['add','new']:
            ident=self.make_draft(1);p=self.page('dark');p.goto(self.url('mini-card',id=ident,embed=1))
            expect(p.get_by_role('button',name='Add to A week of visits',exact=True)).to_be_visible()
            expect(p.get_by_role('button',name='Save as a new Mini',exact=True)).to_be_visible()
            self.check_layout(p);self.shot(p,f'mini-editor-{action}-dark-360.png')
            p.get_by_role('button',name='Add to A week of visits' if action=='add' else 'Save as a new Mini',exact=True).click()
            expect(p.locator('#saved')).to_be_visible()
            result=journey.draft_data(self.data,ident)['saved_id']
            self.assertEqual(result==saved['id'],action=='add');p.close()
        self.assertEqual(len(home.read(home.object_path(self.data,'minis',saved['id']))['questions']),2)


if __name__=='__main__':unittest.main(verbosity=2)
