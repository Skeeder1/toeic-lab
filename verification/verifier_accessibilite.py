"""Exercise the shipped interface directly on a disposable origin/profile.

No script injection and no test wrapper: all application modules load normally.
Set TOEIC_TEST_URL for the deployed edition, or TOEIC_APP_DIR for a local copy.
"""
import functools
import http.server
import json
import os
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'accessibilite-integree.json'
APP = Path(os.environ.get('TOEIC_APP_DIR', ROOT.parent if (ROOT.parent/'TOEIC_Lab.html').exists() else ROOT.parents[1]/'TOEIC_Lab_V23_Complet_Ubuntu'))
report = {'checks': [], 'javascript_errors': [], 'unexpected_dialogs': [], 'status': 'running'}


class Handler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        if self.path.split('?')[0] == '/favicon.ico':
            self.send_response(204)
            self.end_headers()
            return
        super().do_GET()


def check(label):
    report['checks'].append(label)
    print(label, flush=True)


def snapshot(page):
    return page.evaluate('''() => {
      const s=v6Session;
      return {start:s.start,index:s.index,answers:s.answers,mock:s.toeicMock?.id||null,
        items:s.items.map(q=>({key:q.key,options:q.options})),queue:(s.v14Queue||[]).map(q=>q.key)};
    }''')


def paused_snapshot(page, start):
    return page.evaluate('''start => {
      const s=__toeicV18.getPaused().find(s=>s.start===start);
      return s?{start:s.start,index:s.index,answers:s.answers,mock:s.toeicMock?.id||null,
        items:s.items.map(q=>({key:q.key,options:q.options})),queue:(s.v14Queue||[]).map(q=>q.key)}:null;
    }''', start)


server = None
url = os.environ.get('TOEIC_TEST_URL')
if not url:
    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(Handler, directory=str(APP)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    url = f'http://127.0.0.1:{server.server_port}/TOEIC_Lab.html'
report['url'] = url

try:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path='/usr/bin/brave-browser', headless=True)
        context = browser.new_context(viewport={'width': 390, 'height': 844})
        page = context.new_page()
        page.set_default_timeout(6000)
        page.on('pageerror', lambda error: report['javascript_errors'].append(str(error)))

        def unexpected_dialog(dialog):
            report['unexpected_dialogs'].append(dialog.message)
            dialog.dismiss()

        page.on('dialog', unexpected_dialog)
        page.goto(url)
        assert page.evaluate('!!window.ToeicInterfaceAccessibility')
        assert page.get_by_role('main').count() == 1
        assert page.locator('#tvPanel').is_visible()
        assert page.evaluate('document.activeElement.closest("#tvPanel") !== null')
        page.locator('[data-tv-temporary]').click()
        check('Chargement natif des modules, un seul main et consentement sans vol de focus')

        page.locator('[data-v20-section="toeic"]').first.click()
        assert page.locator('main.v7-main h1').first.evaluate('e=>e===document.activeElement')
        page.locator('#v7Start').click()
        assert page.locator('.v7-question-title').evaluate('e=>e===document.activeElement')
        assert page.locator('.v7-question-title').get_attribute('aria-level') == '1'
        assert page.locator('.v7-quiz-bar').get_attribute('role') == 'progressbar'
        page.locator('[data-v7-answer="0"] .v7-letter').click()
        assert page.locator('.v7-correction').evaluate('e=>e===document.activeElement')
        page.locator('#v7Next').focus()
        page.keyboard.press('Enter')
        assert page.locator('.v7-question-title').evaluate('e=>e===document.activeElement')
        page.locator('#v7Translate').focus()
        page.keyboard.press('Enter')
        assert page.locator('#v7Translate').evaluate('e=>e===document.activeElement')
        check('Ciblé : titres, correction, question suivante et traduction accessibles au clavier')

        expected = snapshot(page)
        page.locator('.v20-nav [data-v20-nav="home"]').click()
        assert page.locator('.v20-home').is_visible()
        assert page.evaluate('v6Session===null')
        assert paused_snapshot(page, expected['start']) == expected
        assert not report['unexpected_dialogs']
        page.locator(f'[data-v20-resume="{expected["start"]}"]').click()
        assert snapshot(page) == expected
        page.locator('.v20-nav [data-v20-nav="vocab"]').click()
        assert page.locator('.v16-page').is_visible()
        assert page.evaluate('v6Session===null')
        assert paused_snapshot(page, expected['start']) == expected
        assert not report['unexpected_dialogs']
        check('Accueil et Mes mots depuis une question : pause sans confirmation, questions/ordre/réponses conservés')

        page.locator('.v16-tabbar [data-v16-tab="collection"]').click()
        assert page.locator('.v16-tabbar [data-v16-tab="collection"]').evaluate('e=>e===document.activeElement')
        assert page.locator('#v16Search').get_attribute('aria-label') == 'Rechercher dans mes mots'
        page.keyboard.press('ArrowLeft')
        assert page.locator('.v16-tabbar [data-v16-tab="review"]').evaluate('e=>e===document.activeElement')
        page.keyboard.press('End')
        assert page.locator('.v16-tabbar [data-v16-tab="stats"]').evaluate('e=>e===document.activeElement')
        page.locator('.v16-tabbar [data-v16-tab="collection"]').click()
        tools = page.locator('.ui-disclosure').filter(has=page.locator('.v23-notes-pack'))
        assert tools.count() == 1
        assert not tools.get_attribute('open')
        assert not tools.locator('.v21-vocab-suggest').is_visible()
        assert not tools.locator('.v23-notes-pack').is_visible()
        tools.locator('summary').focus()
        page.keyboard.press('Enter')
        assert tools.locator('.v21-vocab-suggest').is_visible()
        assert tools.locator('.v23-notes-pack').is_visible()
        assert tools.locator('[data-v16-importcsv]').is_visible()
        assert tools.locator('[data-v16-exportcsv]').is_visible()
        assert tools.locator('.v23-notes-pack button').is_visible()
        check('Mots : onglets clavier, recherche nommée et packs/imports repliés mais accessibles')

        page.locator('[data-v16-add]').first.click()
        page.wait_for_function('() => !!document.querySelector("#v16Modal [data-v19-meaning]").labels.length')
        assert page.locator('#v16Modal [data-v19-meaning]').evaluate('e=>e.labels[0].textContent.includes("Traduction française")')
        assert page.locator('#v16Modal [data-v19-context]').evaluate('e=>e.labels.length===1')
        assert page.locator('#v16Modal [data-v19-note]').evaluate('e=>e.labels.length===1')
        assert page.locator('#v6App').evaluate('e=>!!e.closest("[inert]")')
        page.locator('[data-v16-confirm]').focus()
        page.keyboard.press('Tab')
        assert page.locator('#v16EditTerm').evaluate('e=>e===document.activeElement')
        page.keyboard.press('Shift+Tab')
        assert page.locator('[data-v16-confirm]').evaluate('e=>e===document.activeElement')
        page.keyboard.press('Escape')
        assert page.locator('#v16Modal').count() == 0
        assert page.locator('[data-v16-add]').first.evaluate('e=>e===document.activeElement')
        assert not page.locator('#v6App').evaluate('e=>!!e.closest("[inert]")')
        page.locator('[data-v16-add]').first.click()
        page.locator('#v16EditTerm').fill('inspection')
        page.locator('[data-v19-meaning]').fill('inspection')
        page.locator('[data-v16-confirm]').click()
        assert page.locator('#v16Modal').count() == 0
        assert page.locator('#v16List').inner_text().lower().count('inspection') >= 1
        check('Éditeur intégré : labels, Tab/Shift+Tab, Échap, retour au bouton, réouverture et enregistrement')

        page.locator('#tvSettings').click()
        page.locator('[data-tv-profile-action="progress"]').click()
        previous = page.locator('main.v7-main').inner_text()
        page.locator('.v20-nav [data-v20-nav="courses"]').click()
        page.wait_for_selector('#v8CatalogLayer')
        assert page.evaluate('v7View') == 'progress'
        page.locator('#v8CatalogClose').focus()
        page.keyboard.press('Shift+Tab')
        assert page.locator('#v8CatalogLayer').evaluate('e=>e.contains(document.activeElement)')
        page.locator('[data-v8-cat="tense"]').click()
        page.locator('#v8CatalogGrid [data-v8-lesson]').first.click()
        page.wait_for_function('() => !!document.querySelector("#grammarDialog.open,#relativeDialog.open,#gsDialog.open,#v8BasicPop")')
        assert page.evaluate('''() => {const sheet=document.querySelector('#grammarDialog.open,#relativeDialog.open,#gsDialog.open,#v8BasicPop');return sheet.contains(document.activeElement)&&!sheet.closest('[inert]')}''')
        page.keyboard.press('Escape')
        assert page.locator('#v8CatalogLayer').is_visible()
        assert page.locator('#v8CatalogLayer').evaluate('e=>e.contains(document.activeElement)&&!e.inert')
        page.keyboard.press('Escape')
        assert page.locator('#v8CatalogLayer').count() == 0
        assert not page.locator('#v6App').evaluate('e=>!!e.closest("[inert]")')
        assert page.evaluate('v7View') == 'progress'
        assert page.locator('main.v7-main').inner_text() == previous
        check('Fiches depuis Progression : fond conservé, fiche imbriquée et retours Échap cohérents')

        page.evaluate('v5OpenFiche("tense:ps")')
        page.wait_for_function('() => !!document.querySelector("#grammarDialog.open")')
        page.keyboard.press('Escape')
        page.wait_for_function('() => !document.querySelector("#grammarDialog.open") && !document.querySelector("#v6App").closest("[inert]")')
        check('Fiche ouverte directement : fermeture libérant le fond')

        page.locator('.v20-nav [data-v20-nav="vocab"]').click()
        page.evaluate('''() => { const sentinel=document.createElement('aside');sentinel.id='test-inert-existing';sentinel.inert=true;sentinel.textContent='Repère de test';document.body.append(sentinel)}''')
        page.locator('[data-v16-add]').first.click()
        page.keyboard.press('Escape')
        assert page.locator('#test-inert-existing').evaluate('e=>e.inert')
        page.evaluate('document.getElementById("test-inert-existing").remove()')
        check('État inert préexistant conservé après un dialogue')

        page.locator('.v20-nav [data-v20-nav="home"]').click()
        page.locator('[data-tm-library]').click()
        assert '01' in page.locator('[data-tm-start="part5-01"]').get_attribute('aria-label')
        before_events = page.evaluate('v6Events.length')
        page.locator('[data-tm-start="part5-01"]').click()
        assert page.locator('.tm-paper h2').evaluate('e=>e===document.activeElement')
        page.locator('[data-tm-answer="0"]').click()
        assert page.locator('[data-tm-answer="0"]').evaluate('e=>e===document.activeElement')
        assert page.locator('[data-tm-answer="0"]').get_attribute('aria-pressed') == 'true'
        assert page.locator('.tm-progress').get_attribute('aria-valuenow') == '1'
        page.locator('[data-tm-next]').focus()
        page.keyboard.press('Enter')
        assert page.locator('.tm-paper h2').evaluate('e=>e===document.activeElement')
        mock_expected = snapshot(page)
        page.locator('.v20-nav [data-v20-nav="courses"]').click()
        page.wait_for_selector('#v8CatalogLayer')
        assert page.evaluate('v6Session===null')
        assert paused_snapshot(page, mock_expected['start']) == mock_expected
        assert page.evaluate('v6Events.length') == before_events
        page.keyboard.press('Escape')
        page.locator('[data-tm-start="part5-01"]').click()
        assert snapshot(page) == mock_expected
        assert not report['unexpected_dialogs']
        check('Fiches depuis un blanc : pause sans notation, choix/questions conservés et reprise exacte')

        page.locator('[data-tm-finish]').click()
        assert page.locator('#tmSubmit').is_visible()
        assert page.locator('#tmSubmit').evaluate('e=>e.contains(document.activeElement)')
        page.keyboard.press('Escape')
        page.locator('#tmSubmit').wait_for(state='detached')
        assert page.evaluate('v6Events.length') == before_events
        check('Confirmation native du blanc : focus respecté, Échap sans correction ni nouvel événement')
        assert not report['javascript_errors'], report['javascript_errors']
        assert not report['unexpected_dialogs'], report['unexpected_dialogs']
        report['status'] = 'passed'
        browser.close()
except Exception as error:
    report['status'] = 'failed'
    report['failure'] = str(error)
    raise
finally:
    if server:
        server.shutdown()
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2))
