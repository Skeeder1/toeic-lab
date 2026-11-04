"""Exercise consent and persistence in disposable browser profiles, never the user's profile."""
import functools
import os
import shutil
import http.server
import json
import tempfile
import threading
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent
APP = ROOT.parent
CHROMIUM_EXECUTABLE = os.environ.get("CHROMIUM_EXECUTABLE") or shutil.which("brave-browser") or shutil.which("chromium") or shutil.which("chromium-browser")
(ROOT / "publication").mkdir(exist_ok=True)

class Handler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        if self.path.split('?')[0] == '/TOEIC_Lab.html':
            source = (APP / 'TOEIC_Lab.html').read_text()
            if 'src="session-visiteur.js"' not in source:
                source = source.replace('<head>', '<head><link rel="stylesheet" href="session-visiteur.css"><script src="session-visiteur.js"></script>', 1)
            data = source.encode()
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        else:
            super().do_GET()

def run():
    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(Handler, directory=str(APP)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    url = f'http://127.0.0.1:{server.server_port}/TOEIC_Lab.html'
    checks, errors = [], []
    with tempfile.TemporaryDirectory(prefix='toeic-visitor-') as tmp, sync_playwright() as p:
        def launch(name, seed=None):
            context = p.chromium.launch_persistent_context(str(Path(tmp) / name), executable_path=CHROMIUM_EXECUTABLE, headless=True, viewport={'width':390, 'height':844}, accept_downloads=True)
            context.add_init_script('window.__testNativeStorage = window.localStorage;')
            if seed:
                context.add_init_script(f'if (!window.localStorage.getItem("__testSeeded")) {{ for (const [k,v] of Object.entries({json.dumps(seed)})) window.localStorage.setItem(k,v); window.localStorage.setItem("__testSeeded","yes"); }}')
            page = context.pages[0]
            page.set_default_timeout(7000)
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.goto(url)
            page.wait_for_selector('#tvSettings')
            return context, page

        context, page = launch('accept')
        assert page.locator('#tvPanel').is_visible()
        assert page.evaluate('Object.keys(__testNativeStorage).filter(k=>k.startsWith("toeiclab.")).length') == 0
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 2')
        box = page.locator('#tvPanel').bounding_box()
        assert box['x'] >= 0 and box['x'] + box['width'] <= 390 and box['y'] >= 0
        page.screenshot(path=str(ROOT/'publication/session-mobile.png'))
        checks.append('Avant choix : aucune nouvelle donnée permanente ; panneau utilisable à 390 px')
        for width, height in [(320,640),(844,390)]:
            page.set_viewport_size({'width':width,'height':height})
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 2')
            for selector in ['[data-tv-accept]','[data-tv-temporary]']:
                button = page.locator(selector).bounding_box()
                assert button['y'] >= 0 and button['y']+button['height'] <= height, (width,height,selector,button)
            page.screenshot(path=str(ROOT/f'publication/session-{width}x{height}.png'))
        page.set_viewport_size({'width':390,'height':844})
        checks.append('320×640 et 844×390 : deux actions visibles ensemble, texte défilant et aucun débordement')
        result = page.evaluate('''() => {
          localStorage.setItem('toeiclab.test.one','one');localStorage['toeiclab.test.two']='two';
          const keys=Array.from({length:localStorage.length},(_,i)=>localStorage.key(i));
          const entries=Object.fromEntries(Object.entries(localStorage));
          delete localStorage['toeiclab.test.two'];
          localStorage.removeItem('toeiclab.test.one');
          return entries['toeiclab.test.one']==='one' && entries['toeiclab.test.two']==='two' && keys.includes('toeiclab.test.two') && localStorage.getItem('toeiclab.test.two')===null;
        }''')
        assert result
        checks.append('Façade Storage : getItem/setItem/removeItem/key/length, propriétés et Object.entries')
        page.locator('[data-tv-accept]').click()
        assert page.evaluate('ToeicVisitor.mode') == 'persistent'
        visitor_id = page.evaluate('ToeicVisitor.id')
        assert len(visitor_id) >= 32
        page.locator('[data-v20-section="tense"]').first.click()
        page.locator('#v7Length').select_option('10')
        page.locator('#v7Start').click()
        page.locator('[data-v7-answer="0"] .v7-letter').click()
        draft = page.evaluate('JSON.parse(localStorage.getItem("toeiclab.v6.draft"))')
        assert len(draft['answers']) == 1
        page.evaluate('window.__toeicVocabBridge.upsert({term:"visitor persistence",meaning:"test de conservation",context:"A saved session."})')
        context.close()
        context, page = launch('accept')
        assert page.evaluate('ToeicVisitor.id') == visitor_id
        assert not page.locator('#tvPanel').is_visible()
        assert page.evaluate('JSON.parse(localStorage.getItem("toeiclab.v6.draft"))') == draft
        assert page.evaluate('window.__toeicVocabBridge.list().some(x=>x.term==="visitor persistence")')
        checks.append('Accord : identifiant, réponse, séance et vocabulaire conservés après fermeture complète et réouverture')
        page.locator('[data-v20-nav="progress"]').first.click()
        with page.expect_download() as download:
            page.evaluate('window.__toeicV18.exportBackup()')
        dest = Path(tmp)/'backup.json'
        download.value.save_as(dest)
        payload = json.loads(dest.read_text())
        assert any(x['term'] == 'visitor persistence' for x in payload['v10Vocabulary'])
        assert payload['v6Session']['answers'] == draft['answers']
        checks.append('Export JSON : vocabulaire et réponses de la séance présents')
        peer = context.new_page()
        peer.goto(url)
        peer.wait_for_selector('#tvSettings')
        assert peer.evaluate('ToeicVisitor.mode') == 'persistent'
        page.locator('#tvSettings').click()
        page.locator('[data-tv-temporary]').click()
        peer.wait_for_function('ToeicVisitor.mode === "temporary"')
        peer.evaluate('localStorage.setItem("toeiclab.test.after-revocation","memory")')
        assert peer.evaluate('__testNativeStorage.getItem("toeiclab.test.after-revocation")') is None
        checks.append('Refus propagé aux autres onglets : arrêt des écritures permanentes confirmé')
        context.close()

        context, page = launch('temporary')
        page.locator('[data-tv-temporary]').click()
        page.evaluate('localStorage.setItem("toeiclab.test.temporary","ephemeral")')
        assert page.evaluate('localStorage.getItem("toeiclab.test.temporary")') == 'ephemeral'
        assert page.evaluate('__testNativeStorage.getItem("toeiclab.test.temporary")') is None
        page.reload()
        assert page.evaluate('localStorage.getItem("toeiclab.test.temporary")') is None
        assert page.evaluate('ToeicVisitor.id') is None
        context.close()
        context, page = launch('temporary')
        assert page.evaluate('localStorage.getItem("toeiclab.test.temporary")') is None
        assert page.locator('#tvPanel').is_visible()
        checks.append('Refus : aucune nouvelle progression sur disque, rechargement et fermeture non mémorisés, aucun identifiant permanent')
        context.close()

        seed = {'toeiclab.history.v5': '[{"id":"old-history","date":"2026-11-01T12:00:00Z","questions":[]}]', 'toeiclab.test.old': 'original'}
        context, page = launch('legacy', seed)
        assert page.evaluate('localStorage.getItem("toeiclab.test.old")') == 'original'
        page.locator('[data-tv-temporary]').click()
        page.evaluate('localStorage.setItem("toeiclab.test.old","temporary-change")')
        assert page.evaluate('__testNativeStorage.getItem("toeiclab.test.old")') == 'original'
        assert 'old-history' in page.evaluate('__testNativeStorage.getItem("toeiclab.history.v5")')
        page.locator('#tvSettings').click()
        page.locator('[data-tv-accept]').click()
        assert page.evaluate('__testNativeStorage.getItem("toeiclab.test.old")') == 'temporary-change'
        assert 'old-history' in page.evaluate('__testNativeStorage.getItem("toeiclab.history.v5")')
        page.locator('#tvSettings').click()
        page.locator('[data-tv-temporary]').click()
        assert page.evaluate('__testNativeStorage.getItem("toeiclab.test.old")') == 'temporary-change'
        assert page.evaluate('__testNativeStorage.getItem("toeiclab.visitor.v1")') is None
        checks.append('Historique existant préservé au refus et à l’accord ; changement de choix disponible sans suppression de la progression')
        page.evaluate('localStorage.setItem("toeiclab.test.old","my new answer"); __testNativeStorage.setItem("toeiclab.test.old","other tab")')
        page.locator('#tvSettings').click()
        page.locator('[data-tv-accept]').click()
        assert 'autre onglet' in page.locator('[data-tv-status]').inner_text()
        assert page.evaluate('__testNativeStorage.getItem("toeiclab.test.old")') == 'other tab'
        assert page.evaluate('localStorage.getItem("toeiclab.test.old")') == 'my new answer'
        checks.append('Conflit entre onglets : aucune donnée permanente écrasée, séance temporaire toujours exportable')
        context.close()
        blocked = p.chromium.launch_persistent_context(str(Path(tmp)/'blocked'), executable_path=CHROMIUM_EXECUTABLE, headless=True)
        blocked.add_init_script("Object.defineProperty(window,'localStorage',{configurable:true,get:()=>{throw new DOMException('Blocked','SecurityError')}})")
        blocked_page = blocked.pages[0]
        blocked_page.on('pageerror', lambda error: errors.append(str(error)))
        blocked_page.goto(url)
        blocked_page.wait_for_selector('#tvSettings')
        assert blocked_page.evaluate('ToeicVisitor.mode') == 'temporary'
        assert blocked_page.evaluate("localStorage.setItem('toeiclab.test.blocked','memory'); Object.fromEntries(Object.entries(localStorage))['toeiclab.test.blocked']") == 'memory'
        blocked_page.locator('[data-tv-accept]').click()
        assert 'refuse la mémorisation' in blocked_page.locator('[data-tv-status]').inner_text()
        assert blocked_page.evaluate('ToeicVisitor.id') is None
        checks.append('Stockage bloqué : application utilisable en mémoire, absence de faux accord, erreur claire')
        blocked.close()
    server.shutdown()
    report = {'checks': checks, 'javascript_errors': errors}
    (ROOT/'publication/resultats-session-visiteur.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps(report, ensure_ascii=False, indent=2))
    assert not errors, errors

if __name__ == '__main__':
    run()
