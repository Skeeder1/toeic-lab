"""Reproducible UI audit on the sanitised app, ephemeral storage and local origin."""
import functools,http.server,threading,json,os
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parent
APP=Path(os.environ.get('TOEIC_APP_DIR', ROOT.parent if (ROOT.parent/'TOEIC_Lab.html').exists() else ROOT.parents[1]/'TOEIC_Lab_V23_Complet_Ubuntu'))
class Handler(http.server.SimpleHTTPRequestHandler):
 def log_message(self,*args):pass
 def do_GET(self):
  if self.path=='/favicon.ico':self.send_response(204);self.end_headers();return
  super().do_GET()
server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Handler,directory=str(APP)))
threading.Thread(target=server.serve_forever,daemon=True).start()
report={'checks':[],'errors':[],'console':[],'overflow':[],'small_controls':[],'states':[]}
with sync_playwright() as p:
 browser=p.chromium.launch(headless=True,executable_path='/usr/bin/brave-browser')
 for width,height in [(390,844),(1440,1050)]:
  context=browser.new_context(viewport={'width':width,'height':height})
  page=context.new_page();page.set_default_timeout(7000)
  page.on('pageerror',lambda e:report['errors'].append(str(e)))
  page.on('console',lambda e:report['console'].append(e.text) if e.type=='error' else None)
  page.goto(os.environ.get('TOEIC_TEST_URL') or f'http://127.0.0.1:{server.server_port}/TOEIC_Lab.html');page.locator('[data-tv-temporary]').click()
  def snap(name):
   page.wait_for_timeout(100)
   page.screenshot(path=str(ROOT/f'controle-{name}-{width}.png'),full_page=True)
   scan=page.evaluate('''() => {
    const visible=e=>e.checkVisibility?.({checkVisibilityCSS:true})&&e.getBoundingClientRect().width>0&&e.getBoundingClientRect().height>0;
    const over=[...document.querySelectorAll('main.v7-main *,[role="dialog"] *')].filter(e=>{const r=e.getBoundingClientRect();return visible(e)&&(r.left < -2||r.right>innerWidth+2)}).map(e=>({tag:e.tagName,id:e.id,class:e.className,text:e.textContent.slice(0,60),rect:e.getBoundingClientRect().toJSON()}));
    const small=[...document.querySelectorAll('.v7-header button,main.v7-main button,main.v7-main summary,[role="dialog"] button')].filter(e=>{const r=e.getBoundingClientRect();return visible(e)&&(r.height<43.5||r.width<43.5)}).map(e=>({tag:e.tagName,id:e.id,class:e.className,text:e.textContent.slice(0,60),rect:e.getBoundingClientRect().toJSON()}));
    return {overflow:over,small:small,title:document.querySelector('main.v7-main h1')?.textContent,height:document.documentElement.scrollHeight};
   }''')
   report['overflow'] += [{'state':name,'width':width,**x} for x in scan['overflow']]
   report['small_controls'] += [{'state':name,'width':width,**x} for x in scan['small']]
   report['states'].append({'state':name,'width':width,'title':scan['title'],'height':scan['height']})
  snap('accueil')
  assert page.locator('.tm-toeic-paths > button').count()==2
  assert page.locator('.v20-paths > button').count()==5
  report['checks'].append(f'{width}: accueil 2 parcours TOEIC, 5 notions')
  page.locator('.tm-toeic-paths > [data-v20-section="toeic"]').click();snap('cible-reglages')
  assert page.locator('.v18-setup h2').inner_text()=='Ta prochaine série'
  page.locator('#v7Start').click();snap('cible-question')
  page.locator('[data-v7-answer]').first.click(position={'x':9,'y':9});snap('cible-correction')
  page.locator('#v18Pause').click()
  page.locator('[data-v20-nav="home"]').first.click()
  page.locator('[data-tm-library]').click();snap('blancs-tous')
  assert page.locator('.tm-test-card:visible').count()==10
  page.locator('.tm-library .ui-switcher [data-ui-filter="paused"]').click();snap('blancs-filtre-vide')
  assert page.locator('.tm-test-card:visible').count()==0
  page.get_by_role('button',name='Voir tous les tests',exact=True).click()
  assert page.locator('.tm-test-card:visible').count()==10
  page.locator('[data-tm-start="part5-01"]').click();snap('blanc-question')
  assert '1 / 30' in page.locator('.tm-step').inner_text()
  page.locator('#v18Pause').click()
  page.locator('[data-v20-nav="home"]').first.click()
  page.locator('.v20-nav [data-v20-nav="vocab"]').click();snap('mots-reviser')
  folds=page.locator('.v16-page > details.ui-disclosure')
  assert folds.count()==1 and not folds.get_attribute('open')
  assert folds.bounding_box()['y']>page.locator('.v16-tabbar').bounding_box()['y']
  page.locator('.v16-tab[data-v16-tab="collection"]').click();snap('mots-collection')
  assert page.locator('[data-v16-add]:visible').count()==1
  page.locator('.v16-page > details.ui-disclosure > summary').click();snap('mots-outils')
  page.locator('#tvSettings').click();page.locator('[data-tv-profile-action="progress"]').click();snap('progression-vide')
  assert page.get_by_role('button',name='Choisir une séance →',exact=True).is_visible()
  background=page.locator('main.v7-main').inner_text()
  page.locator('.v20-nav [data-v20-nav="courses"]').click();page.locator('#v8CatalogLayer').wait_for(state='visible');snap('fiches')
  page.locator('#v8CatalogLayer').get_by_role('button',name='Fermer',exact=False).click()
  assert page.locator('main.v7-main').inner_text()==background
  report['checks'].append(f'{width}: préparation, question/correction/pause, 10 blancs+filtre vide, compteur1/30, mots repliés, progression vide et Fiches restaurée')
  context.close()
 # Generate a genuine completed mock using real form controls, then inspect filters.
 context=browser.new_context(viewport={'width':390,'height':844});page=context.new_page();page.set_default_timeout(7000)
 page.on('pageerror',lambda e:report['errors'].append(str(e)))
 page.goto(f'http://127.0.0.1:{server.server_port}/TOEIC_Lab.html');page.locator('[data-tv-temporary]').click();page.locator('[data-tm-library]').click();page.locator('[data-tm-start="part5-01"]').click()
 for i in range(30):
  page.locator('[data-tm-answer="0"]').click()
  if i<29:page.locator('[data-tm-next]').click()
 page.locator('[data-tm-finish]').click();page.locator('[data-tm-submit]').click()
 page.locator('#tvSettings').click();page.locator('[data-tv-profile-action="progress"]').click()
 for width,height in [(390,844),(1440,1050)]:
  page.set_viewport_size({'width':width,'height':height});snap('progression-historique')
  page.locator('.v7-progress-page .ui-switcher [data-ui-filter="mock"]').click();snap('progression-filtre-blanc')
  assert page.locator('.v6-old-session:visible').count()==1
  page.locator('.v7-progress-page .ui-switcher [data-ui-filter="target"]').click();snap('progression-filtre-vide')
  assert page.locator('.v6-old-session:visible').count()==0
  page.locator('.v7-progress-page .ui-switcher [data-ui-filter="all"]').click()
 report['checks'].append('30 réponses réelles et confirmation du blanc, historique+filtrage mock/ciblé cohérents390/1440')
 context.close();browser.close()
server.shutdown()
(ROOT/'controle-visuel.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps(report,ensure_ascii=False,indent=2))
