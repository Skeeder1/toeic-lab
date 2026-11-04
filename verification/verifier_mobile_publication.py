"""Touch-screen layout checks with isolated browser storage and synthetic questions."""
import functools
import os
import shutil
import http.server
import json
import threading
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent
APP = ROOT.parent
CHROMIUM_EXECUTABLE = os.environ.get("CHROMIUM_EXECUTABLE") or shutil.which("brave-browser") or shutil.which("chromium") or shutil.which("chromium-browser")
(ROOT / "publication").mkdir(exist_ok=True)
OUT = ROOT / 'publication'


class Handler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        if self.path.split('?')[0] == '/TOEIC_Lab.html':
            source = (APP / 'TOEIC_Lab.html').read_text()
            if 'href="mobile.css"' not in source:
                source = source.replace('</body>', '<link rel="stylesheet" href="mobile.css"></body>')
            data = source.encode()
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        else:
            super().do_GET()


BOUNDS = """() => [...document.querySelectorAll('body *')].filter(e => {
 const r=e.getBoundingClientRect(),s=getComputedStyle(e);
 return r.width>0 && r.height>0 && s.visibility!=='hidden'
  && (r.left < -2 || r.right > innerWidth+2)
  && !e.closest('[aria-hidden="true"]');
}).map(e=>({tag:e.tagName,cls:typeof e.className==='string'?e.className:'SVG',
 text:e.textContent.trim().slice(0,65),x:Math.round(e.getBoundingClientRect().x),
 width:Math.round(e.getBoundingClientRect().width)})).slice(0,35)"""


def run():
    OUT.mkdir(exist_ok=True)
    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(Handler, directory=str(APP)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    url = f'http://127.0.0.1:{server.server_port}/TOEIC_Lab.html'
    report = {'checks': [], 'overflow': [], 'errors': [], 'webkit': ''}
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=CHROMIUM_EXECUTABLE, headless=True)
        for width, height in [(320,640),(360,800),(390,844),(430,932),(768,1024),(844,390)]:
            context = browser.new_context(viewport={'width':width,'height':height},has_touch=True,is_mobile=True)
            page = context.new_page()
            page.set_default_timeout(5000)
            page.on('pageerror', lambda e:report['errors'].append(str(e)))

            def check(state, capture=False):
                page.wait_for_timeout(120)
                print(f'{width}x{height}: {state}', flush=True)
                overflow = page.evaluate(BOUNDS)
                if overflow:
                    report['overflow'].append({'width':width,'height':height,'state':state,'elements':overflow})
                report['checks'].append(f'{width}x{height}: {state}')
                if capture:
                    page.screenshot(path=str(OUT/f'mobile-{width}-{height}-{state}.png'), full_page=state not in ['bulle','sens','consentement'])

            page.goto(url)
            # A new anonymous context starts with no personal progress.
            consent = page.locator('[data-tv-accept]')
            if consent.count() and consent.first.is_visible():
                check('consentement', width == 320 or height == 390)
                assert consent.first.bounding_box()['height'] >= 44
                consent.first.tap()
            check('accueil', width in [320,390])
            nav = page.locator('.v20-nav button')
            assert nav.evaluate_all('(es)=>es.every(e=>e.getBoundingClientRect().height>=44)'), 'Navigation targets under 44px'
            page.locator('[data-v20-nav="courses"]').first.click()
            check('catalogue')
            page.locator('#v8CatalogLayer [data-v8-lesson="tense:pp"]').first.click()
            check('fiche', width == 390)
            page.locator('#gClose').click()
            page.locator('#v8CatalogClose').click()
            page.locator('[data-v20-nav="vocab"]').first.click()
            check('mots', width == 320)
            page.locator('[data-v20-nav="progress"]').first.click()
            check('progression')
            page.locator('[data-v20-nav="home"]').first.click()
            page.locator('[data-v20-section="toeic"]').first.click()
            check('configuration')
            page.locator('#v7Start').click()
            check('exercice')
            page.evaluate("""()=>{const q={...V6_BYKEY.get('v21:diagnostic:014')};
              v6Session={...v6Session,section:'toeic',items:[q],count:1,index:0,answers:{},v14Queue:[],v14Unique:true,feedback:'learn'};
              v7View='workspace';v6Page='practice';v7Save();v6Render()}""")
            expression=page.locator('.v7-answer-text [data-tl-term="take off"]')
            expression.scroll_into_view_if_needed()
            page.wait_for_timeout(250)
            expression.tap()
            check('bulle', width == 390)
            badge=page.locator('#tlTooltip button')
            assert badge.bounding_box()['width']>=44 and badge.bounding_box()['height']>=44
            assert page.evaluate('Object.keys(v6Session.answers).length')==0
            badge.tap()
            check('sens', width in [320,390])
            close=page.locator('dialog [data-tl-close]')
            close.tap()
            assert page.evaluate('Object.keys(v6Session.answers).length')==0
            page.locator('[data-v7-answer="0"] .v7-letter').tap()
            assert page.evaluate('Object.keys(v6Session.answers).length')==1
            check('correction')
            context.close()
        browser.close()
        try:
            webkit=p.webkit.launch(headless=True, timeout=5000)
            webkit.close()
            report['webkit']='Engine available; Chromium matrix completed separately.'
        except Exception as error:
            report['webkit']='Unavailable locally: '+str(error).splitlines()[0]
    server.shutdown()
    (OUT/'mobile-results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report,ensure_ascii=False,indent=2))
    assert not report['errors'], report['errors']
    assert not report['overflow'], report['overflow']


if __name__ == '__main__':
    run()
