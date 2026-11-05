"""Session result regression checks in disposable profiles only."""
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
OUT = ROOT/'publication'/'ergonomie'
CHROMIUM_EXECUTABLE = os.environ.get('CHROMIUM_EXECUTABLE') or shutil.which('brave-browser') or shutil.which('chromium') or shutil.which('chromium-browser')
class Handler(http.server.SimpleHTTPRequestHandler):
    def log_message(self,*args): pass

def run():
    OUT.mkdir(parents=True,exist_ok=True)
    server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Handler,directory=str(APP)))
    threading.Thread(target=server.serve_forever,daemon=True).start()
    url=f'http://127.0.0.1:{server.server_port}/TOEIC_Lab.html'
    checks=[];errors=[];reports=[]
    with tempfile.TemporaryDirectory(prefix='toeic-results-') as tmp,sync_playwright() as p:
        context=p.chromium.launch_persistent_context(tmp,executable_path=CHROMIUM_EXECUTABLE,headless=True,viewport={'width':1440,'height':1050},accept_downloads=True)
        page=context.pages[0];page.set_default_timeout(6000)
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.goto(url);page.locator('[data-tv-accept]').click()
        bank=page.evaluate('JSON.stringify(V6_ALL)')
        history=page.evaluate('JSON.stringify(v5History)')
        for section,wanted in [('toeic',0),('toeic',9),('toeic',10),('tense',9),('tense',10)]:
            old_events=page.evaluate('v6Events.length')
            old_observations=page.evaluate('window.__toeicV18.getProfile().observations.length')
            old_history=page.evaluate('JSON.stringify(v5History)')
            page.evaluate('(section)=>{v7State.section=section;v7Cfg().length="10";v7Cfg().feedback="exam";v7Cfg().mode="auto";v6Start()}',section)
            expected=[]
            for i in range(10):
                q=page.evaluate('({key:v6Session.items[v6Session.index].key,correct:v6Session.items[v6Session.index].correct})')
                answer=q['correct'] if i<wanted else (q['correct']+1)%4
                expected.append({'key':q['key'],'chosen':answer,'expected':q['correct']})
                page.locator(f'[data-v7-answer="{answer}"] .v7-letter').click()
                page.locator('#v7Next').click()
            page.locator('.v24-results').wait_for()
            data=page.evaluate('({record:v6ResultCache.r,events:v6Events.length,observations:window.__toeicV18.getProfile().observations.length,report:window.__toeicV14.getState().lastReport})')
            rec=data['record']
            assert rec['correct']==wanted and rec['total']==10,(section,wanted,rec['correct'])
            assert data['events']==old_events+10
            assert data['observations']==old_observations+10
            for e in expected:
                archived=next(q for q in rec['questions'] if q['id']==e['key'])
                assert archived['chosen']==e['chosen'] and archived['expected']==e['expected']
            assert page.evaluate('(old)=>JSON.stringify(v5History.filter(r=>r.id!==v6ResultCache.r.id))===old',old_history)
            assert page.get_by_role('heading',name=f'{wanted} bonnes réponses sur 10').is_visible()
            assert 'Enregistrée dans ce navigateur' in page.locator('.v24-save-status').inner_text()
            assert page.locator('.v24-mistakes .v24-review').count()==10-wanted
            assert page.locator('.v24-mistakes .v24-review[open]').count()==(1 if wanted<10 else 0)
            assert not page.locator('.v24-good-answers').count() or not page.locator('.v24-good-answers').evaluate('(e)=>e.open')
            assert not page.locator('.v24-topic-details').evaluate('(e)=>e.open')
            assert '+0 pt' not in page.locator('.v24-results').inner_text()
            assert page.locator('.v24-results').locator(':scope > *').first.evaluate('(e)=>e.classList.contains("v24-result-head")')
            snapshot=page.evaluate('JSON.stringify(Object.entries(localStorage).sort())')
            page.evaluate('v6Render();v6Render()')
            assert page.evaluate('JSON.stringify(Object.entries(localStorage).sort())')==snapshot
            assert page.evaluate('JSON.stringify(V6_ALL)')==bank
            page.locator('.v24-topic-details>summary').click()
            topic_text=page.locator('.v24-topic-details').inner_text()
            comparison=any(x['after']['n']>x['before']['n'] for x in data['report']['changes'])
            if section=='toeic': assert 'Estimation cumulée' not in topic_text and 'Première estimation' not in topic_text
            if comparison: assert 'estimation' in topic_text.lower()
            page.locator('.v24-topic-details>summary').click()
            if wanted==9:
                for width,height in [(1440,1050),(390,844),(320,640),(844,390)]:
                    page.set_viewport_size({'width':width,'height':height})
                    page.evaluate('window.scrollTo(0,0)')
                    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+2'),(section,width)
                    page.screenshot(path=str(OUT/f'bilan-{section}-{wanted}-{width}x{height}.png'))
                page.set_viewport_size({'width':1440,'height':1050})
            reports.append({'section':section,'score':wanted,'n':10,'curriculum_comparable':comparison,'prior_estimate_compared':any(x['after']['n']>x['before']['n']>0 for x in data['report']['changes'])})
        assert any(r['prior_estimate_compared'] for r in reports)
        checks.append('Cinq vraies séances cliquées : TOEIC 0/10, 9/10, 10/10 ; Temps 9/10 et 10/10')
        checks.append('Chaque réponse archivée identique au choix ; 10 événements et observations supplémentaires par séance ; ancien historique intact')
        checks.append('Re-rendus sans mutation de stockage ; banque inchangée ; résultat et enregistrement avant les notions')
        checks.append('Erreurs seules prioritaires, une correction ouverte ; bonnes réponses et notions repliées ; aucun +0 pt')
        checks.append('Notions TOEIC sans faux indice ; estimation affichée uniquement pour compteur pédagogique réellement mis à jour')
        checks.append('Affichage vérifié à 1440×1050, 390×844, 320×640 et 844×390 sans débordement horizontal')
        with page.expect_download() as download:page.evaluate('window.__toeicV18.exportBackup()')
        exported=Path(tmp)/'backup.json';download.value.save_as(exported)
        payload=json.loads(exported.read_text())
        assert len(payload['history'])==len(page.evaluate('v5History'))
        checks.append('Export JSON complet toujours fonctionnel après les cinq séances')
        final_history=page.evaluate('JSON.stringify(v5History)')
        context.close()
        context=p.chromium.launch_persistent_context(tmp,executable_path=CHROMIUM_EXECUTABLE,headless=True)
        page=context.pages[0];page.goto(url)
        assert page.evaluate('JSON.stringify(v5History)')==final_history
        assert page.evaluate('v6Events.length')==50
        assert page.evaluate('window.__toeicV18.getProfile().observations.length')==50
        checks.append('Fermeture complète et réouverture : cinq séances, 50 réponses et 50 observations conservées')
        context.close()
    server.shutdown()
    result={'checks':checks,'sessions':reports,'javascript_errors':errors}
    (OUT/'resultats-bilan.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result,ensure_ascii=False,indent=2));assert not errors,errors
if __name__=='__main__':run()
