"""Regression checks in a temporary browser profile; no personal data is used."""
import functools
import os
import shutil
import http.server
import json
import tempfile
import threading
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parent
APP=ROOT.parent
CHROMIUM_EXECUTABLE = os.environ.get("CHROMIUM_EXECUTABLE") or shutil.which("brave-browser") or shutil.which("chromium") or shutil.which("chromium-browser")
(ROOT / "publication").mkdir(exist_ok=True)
ASSETS='<link rel="stylesheet" href="aide-vocabulaire.css"><script src="lexique-toeic.js"></script><script src="aide-vocabulaire.js"></script>'

class Handler(http.server.SimpleHTTPRequestHandler):
    def log_message(self,*args): pass
    def do_GET(self):
        if self.path.split('?')[0]=='/TOEIC_Lab.html':
            source=(APP/'TOEIC_Lab.html').read_text()
            if 'src="aide-vocabulaire.js"' not in source:
                source=source.replace('</body>',ASSETS+'</body>')
            data=source.encode()
            self.send_response(200);self.send_header('Content-Type','text/html; charset=utf-8');self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)
        else: super().do_GET()

def run():
    server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Handler,directory=str(APP)))
    threading.Thread(target=server.serve_forever,daemon=True).start()
    url=f'http://127.0.0.1:{server.server_port}/TOEIC_Lab.html'
    checks=[];errors=[]
    with tempfile.TemporaryDirectory(prefix='toeic-lexique-') as tmp,sync_playwright() as p:
        def launch():
            ctx=p.chromium.launch_persistent_context(str(Path(tmp)/'profile'),executable_path=CHROMIUM_EXECUTABLE,headless=True,viewport={'width':1440,'height':1000},accept_downloads=True)
            pg=ctx.pages[0];pg.set_default_timeout(7000);pg.on('pageerror',lambda e:errors.append(str(e)));pg.goto(url)
            if pg.locator('[data-tv-accept]').is_visible(): pg.locator('[data-tv-accept]').click()
            return ctx,pg
        ctx,page=launch()
        coverage=page.evaluate('''() => {
          const options=[...new Set(V6_ALL.filter(q=>q.group==='syntax:phrasal-verbs').flatMap(q=>q.options))];
          return {total:options.length,missing:options.filter(o=>!window.TOEIC_EXPRESSION_ENTRIES.some(e=>e.term===o)),split:options.filter(o=>{const t=document.createElement('div');t.innerHTML=ToeicLexicon.render(o,false);return t.querySelectorAll('[data-tl-term]').length!==1||t.firstElementChild.textContent!==o;})};
        }''')
        assert coverage['total']==57 and not coverage['missing'] and not coverage['split'],coverage
        checks.append('Les 57 expressions des choix phrasal verbs sont des unités complètes')
        for text,term in [('TAKE OFF','take off'),('took off','take off'),('taking off','take off'),('take your coat off','take off'),('handed the form in','hand in'),('put them away','put away'),('look down on','look down on')]:
            result=page.evaluate('''([text,term])=>{const t=document.createElement('div');t.innerHTML=ToeicLexicon.render(text);return [...t.querySelectorAll('[data-tl-term]')].some(x=>x.dataset.tlTerm===term&&x.textContent===text)}''',[text,term])
            assert result,(text,term)
        checks.append('Reconnaissance de la casse, des formes fléchies et des expressions séparables')
        for sentence,fragment in [('Our flight will take off at noon.','décoll'),('Please take off your jacket.','retir'),('Sales took off after the campaign.','essor')]:
            suggested=page.evaluate('(sentence)=>ToeicLexicon.lookup("take off",{sentence}).suggested',sentence)
            assert suggested and fragment in suggested['meaning'].lower(),(sentence,suggested)
        assert page.evaluate('ToeicLexicon.lookup("take off",{sentence:"Please ____ soon."}).suggested') is None
        for term,fragment in [('take off','retirer'),('hand in','remettre'),('get through','terminer'),('put away','ranger')]:
            sense=page.evaluate('(term)=>ToeicLexicon.lookup(term,{sentence:"Please ____ the completed access form to the security office before your first shift."}).suggested',term)
            assert sense and fragment in sense['meaning'],(term,sense)
        checks.append('Sens suggéré selon le contexte ; incertitude affichée lorsque la phrase ne suffit pas')
        page.locator('[data-v20-section="tense"]').first.click();page.locator('#v7Length').select_option('10');page.locator('#v7Start').click()
        page.evaluate('''()=>{const q=V6_BYKEY.get('v21:diagnostic:014');v6Session={...v6Session,section:'toeic',items:[q],count:1,index:0,answers:{},v14Queue:[],v14Unique:true,feedback:'learn'};v7View='workspace';v6Page='practice';v7Save();v6Render()}''')
        choice=page.locator('.v7-answer-text [data-tl-term="take off"]')
        assert choice.count()==1
        choice.hover();assert page.locator('#tlTooltip').is_visible()
        answers=page.evaluate('JSON.stringify(v6Session.answers)')
        card=page.get_by_role('dialog',name='Traduction de take off',exact=True)
        assert 'enlever, retirer' in card.inner_text() and card.locator('button').inner_text()=='8'
        assert 'Le sens dépend du contexte' not in card.inner_text()
        badge=card.get_by_role('button',name='Voir les 8 sens de take off',exact=True)
        badge.hover();page.wait_for_timeout(350);assert card.is_visible()
        cb,bb=card.bounding_box(),badge.bounding_box()
        assert 8<=cb['x']+cb['width']-bb['x']-bb['width']<=18
        assert 8<=cb['y']+cb['height']-bb['y']-bb['height']<=18
        page.screenshot(path=str(ROOT/'publication/bulle-vocabulaire-compacte.png'))
        badge.click();modal=page.get_by_role('dialog',name='Sens de take off',exact=True)
        assert modal.is_visible() and modal.locator('.tl-senses article').count()>=7
        assert page.evaluate('JSON.stringify(v6Session.answers)')==answers
        assert '____ the completed access form' in modal.locator('.tl-context').inner_text()
        assert 'enlever, retirer' in modal.locator('.tl-context').inner_text()
        assert not modal.locator('#v10Term').count()
        checks.append('Bulle compacte : expression, sens contextuel et case 8 en bas à droite ; le clic sur 8 ouvre les sens sans répondre')
        modal.locator('[data-tl-save]').click()
        saved=page.evaluate('window.__toeicVocabBridge.list().find(x=>x.term==="take off")')
        assert len(saved['senses'])>=7 and saved['term']=='take off'
        units=page.evaluate('window.__toeicFlashcards.units().filter(x=>x.word.term==="take off").length')
        assert units==2*len(saved['senses']),units
        modal.locator('[data-tl-close]').click()
        # Existing personal definitions and ids must remain intact when new senses are merged.
        page.evaluate('''()=>{window.__toeicVocabBridge.upsert({term:'get through',meaning:'ma définition conservée',context:'mon exemple',senses:[{id:'mon-id-stable',meaning:'ma définition conservée',context:'mon exemple'}]});ToeicLexicon.refresh()}''')
        page.locator('.v7-answer-text [data-tl-term="get through"]').click()
        page.locator('#tlTooltip button').click()
        page.locator('dialog [data-tl-save]').click()
        merged=page.evaluate('window.__toeicVocabBridge.list().find(x=>x.term==="get through")')
        assert merged['meaning']=='ma définition conservée' and merged['senses'][0]['id']=='mon-id-stable' and len(merged['senses'])>=7
        page.locator('dialog [data-tl-close]').click()
        checks.append('Ajout de tous les sens aux flashcards ; définitions et identifiants personnels conservés')
        page.locator('.v7-question-title [data-tl-term]').first.press('Enter')
        # Closing a scrolled modal can emit a delayed scroll event. It must not
        # dismiss the fresh tooltip anchored to a different part of the page.
        page.evaluate('''()=>{const closed=document.createElement('dialog');document.body.append(closed);closed.dispatchEvent(new Event('scroll'));closed.remove()}''')
        assert page.locator('#tlTooltip button').evaluate('(e)=>e===document.activeElement')
        page.locator('#tlTooltip button').press('Enter')
        assert page.locator('dialog.tl-dialog[open]').count()==1
        page.locator('dialog [data-tl-close]').click()
        page.locator('[data-tl-question]').click()
        page.locator('dialog [data-tl-pick]').filter(has_text='hand in').click()
        assert page.get_by_role('dialog',name='Sens de hand in').is_visible()
        page.locator('dialog [data-tl-close]').click()
        ctx.close();ctx,page=launch()
        persisted=page.evaluate('window.__toeicVocabBridge.list().find(x=>x.term==="take off")')
        assert persisted['senses']==saved['senses']
        assert page.evaluate('Object.keys(v6Session.answers).length')==0
        page.locator('[data-tl-question]').click();page.locator('dialog [data-tl-pick]').filter(has_text='take off').click()
        page.set_viewport_size({'width':390,'height':844})
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+2')
        assert page.locator('dialog').bounding_box()['width']<=390
        page.screenshot(path=str(ROOT/'publication/aide-vocabulaire-mobile.png'))
        page.set_viewport_size({'width':1440,'height':1000});page.screenshot(path=str(ROOT/'publication/aide-vocabulaire-desktop.png'))
        page.locator('dialog [data-tl-close]').click()
        page.set_viewport_size({'width':390,'height':844})
        page.locator('.v7-answer-text [data-tl-term="take off"]').click()
        mobile_card=page.locator('#tlTooltip').bounding_box()
        assert mobile_card['x']>=0 and mobile_card['x']+mobile_card['width']<=390
        page.screenshot(path=str(ROOT/'publication/bulle-vocabulaire-mobile.png'))
        page.locator('#tlTooltip button').click();page.locator('dialog [data-tl-close]').click()
        page.set_viewport_size({'width':1440,'height':1000})
        page.locator('[data-v7-answer="0"] .v7-letter').click()
        assert page.evaluate('Object.keys(v6Session.answers).length')==1
        checks.append('Reprise après fermeture, affichage mobile et sélection de réponse par sa lettre vérifiés')
        page.locator('#v7Next').click();page.locator('[data-v20-nav="progress"]').first.click()
        with page.expect_download() as download:page.locator('[data-v18-backup]').click()
        dest=Path(tmp)/'backup.json';download.value.save_as(dest);backup=json.loads(dest.read_text())
        assert any(w['term']=='take off' and len(w['senses'])>=7 for w in backup['v10Vocabulary'])
        checks.append('Sauvegarde JSON : expression et ensemble de ses sens conservés')
        ctx.close()
    server.shutdown()
    report={'checks':checks,'coverage':coverage,'javascript_errors':errors}
    (ROOT/'publication/resultats-aide-vocabulaire.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report,ensure_ascii=False,indent=2));assert not errors,errors

if __name__=='__main__':run()
