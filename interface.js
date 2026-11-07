/* Presentation only. Learning, answers, scheduling and portable data stay with the application. */
(() => {
  'use strict';
  const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const render = v6Render;
  let libraryFilter = 'all', progressFilter = 'all';
  const foldState = new Map();
  const skip=document.createElement('a');skip.className='ui-skip';skip.href='#toeicMain';skip.textContent='Aller au contenu';
  skip.addEventListener('click',event=>{event.preventDefault();const target=document.getElementById('toeicMain');target?.focus();});
  document.body.prepend(skip);
  function button(label, action, className = 'ui-button') {
    const el = document.createElement('button');
    el.type = 'button'; el.className = className; el.textContent = label; el.onclick = action;
    return el;
  }
  function fold(parent, key, label, elements) {
    const content = elements.filter(Boolean);
    if (!content.length) return null;
    const detail = document.createElement('details'); detail.className = 'ui-disclosure';
    detail.open = foldState.get(key) || false;
    const summary = document.createElement('summary'); summary.textContent = label;
    detail.append(summary, ...content); parent.append(detail);
    detail.addEventListener('toggle', () => foldState.set(key, detail.open));
    return detail;
  }
  function home(main) {
    const area = main.querySelector('.v20-home'); if (!area) return;
    const rows = v5History || [], vocab = window.__toeicFlashcards?.metrics?.() || {};
    const header = document.createElement('header'); header.className = 'ui-home-heading';
    header.innerHTML = '<div><p class="ui-eyebrow">TON ESPACE D’ANGLAIS</p><h1>On travaille quoi aujourd’hui ?</h1><p>Une série ciblée, un test blanc ou quelques mots à revoir.</p></div>';
    if (rows.length) {
      const last = rows.at(-1);
      const activity = button('', () => ToeicNavigation.go('progress'), 'ui-activity');
      activity.innerHTML = '<span>Dernière séance</span><strong>'+Number(last.correct)+' <small>/ '+Number(last.total)+'</small></strong><span>Voir ma progression <span aria-hidden="true">↗</span></span>';
      header.append(activity);
    }
    area.querySelector('.v20-homehero')?.replaceWith(header);
    const headings = [...area.querySelectorAll(':scope > .v20-sectionheading')];
    headings[0]?.remove(); headings[1]?.remove();
    const paths = area.querySelector('.v20-paths');
    if (paths) {
      const h = document.createElement('h2'); h.className = 'ui-section-title'; h.textContent = 'Travailler une notion'; paths.before(h);
      for (const card of paths.querySelectorAll('.v20-path')) {
        card.querySelector('em')?.remove(); card.querySelector('.v20-arrow')?.setAttribute('aria-hidden','true');
      }
    }
    const target = area.querySelector('.tm-toeic-paths [data-v20-section="toeic"]');
    if (target) {
      target.querySelector('strong').textContent = 'TOEIC ciblé';
      target.querySelector('small').textContent = 'Des séries adaptées aux notions à renforcer.';
      target.querySelector('em').textContent = '10, 20 ou 40 questions →';
      target.setAttribute('aria-label','TOEIC ciblé, Partie 5 : configurer une série');
    }
    const mock = area.querySelector('[data-tm-library]');
    if (mock) {
      mock.querySelector('small').textContent = '10 tests de 30 questions. Correction à la fin.';
      mock.querySelector('em').textContent = 'Choisir un test →';
      mock.setAttribute('aria-label','TOEIC blanc, Partie 5 : choisir parmi dix tests');
    }
    const quickWords = area.querySelector('.v20-quick [data-v20-nav="vocab"] small');
    if (quickWords) {
      const due = (vocab.due || 0) + Math.min(vocab.newCards || 0, vocab.quota?.newLeft || 0);
      quickWords.textContent = due ? due+' cartes pour aujourd’hui' : vocab.words ? 'Ouvrir ma collection' : 'Ajouter mes premiers mots';
    }
    const paused = area.querySelector('.v20-h-paused');
    if (paused) { header.after(paused); paused.querySelector('h3').textContent = 'Reprendre une séance'; }
  }
  function setup(main) {
    if (!main.classList.contains('v20-context')) return;
    const heading = main.querySelector('.v20-subhead');
    heading?.querySelector('.v20-overline')?.remove();
    if (v7State.section === 'toeic') {const title=heading?.querySelector('h1');if(title)title.textContent='TOEIC ciblé · Partie 5';const crumb=heading?.querySelector('.v20-breadcrumb span:last-child');if(crumb)crumb.textContent='TOEIC ciblé · Partie 5';}
    const paragraph = heading?.querySelector('p');
    if (paragraph && v7State.section === 'toeic') paragraph.textContent = 'Travaille les notions à renforcer avec des questions inédites en priorité.';
    const actions = heading?.querySelector('.v20-subactions');
    actions?.querySelector('[data-v20-nav="courses"]')?.remove();
    const card = main.querySelector('.v18-setup');
    if (card) {
      const h = card.querySelector('h2'); if (h) h.textContent = 'Ta prochaine série';
      card.querySelector('.v18-label')?.remove();
      const hint = card.querySelector(':scope > .v18-hint');
      if (hint && v7State.section === 'toeic') hint.remove();
      const settings = card.querySelector('.v18-settings');
      if (settings) settings.setAttribute('aria-label','Réglages de la série');
    }
  }
  function switcher(options, current, callback, label) {
    const group = document.createElement('div'); group.className = 'ui-switcher'; group.setAttribute('role','group'); group.setAttribute('aria-label',label);
    for (const [id, title] of options) {
      const control = button(title, () => callback(id)); control.dataset.uiFilter = id;
      control.setAttribute('aria-pressed', String(id === current)); group.append(control);
    }
    return group;
  }
  function library(main) {
    const page = main.querySelector('.tm-library'); if (!page) return;
    const head = page.querySelector('.tm-library-heading');
    head.querySelector('p').textContent = '10 tests fixes de 30 questions, avec correction à la fin.';
    const cards = [...page.querySelectorAll('.tm-test-card')];
    for (const card of cards) {
      card.querySelector('.tm-test-number').setAttribute('aria-hidden','true');
      card.querySelector('h2').textContent = 'Test blanc';
      card.querySelector('p')?.remove();
      const detail = card.querySelector(':scope > small');
      if (detail.textContent === 'Énoncés et ordre fixes') detail.textContent = '30 questions';
      const start = card.querySelector('[data-tm-start]');
      start.setAttribute('aria-label',start.textContent.replace('→','').trim()+' le test blanc '+card.querySelector('.tm-test-number').textContent+', Partie 5');
      card.dataset.uiStatus = card.classList.contains('is-paused') ? 'paused' : card.classList.contains('is-complete') ? 'done' : 'todo';
    }
    const status = document.createElement('p'); status.className = 'ui-sr-only'; status.setAttribute('role','status');
    const empty = document.createElement('div'); empty.className = 'ui-empty'; empty.hidden = true;
    empty.innerHTML = '<h2>Aucun test dans cette catégorie</h2><p>Retrouve les autres tests pour continuer.</p>';
    const filters = switcher([['all','Tous'],['todo','À faire'],['paused','En pause'],['done','Terminés']], libraryFilter, id => { libraryFilter=id; update(); }, 'Filtrer les tests blancs');
    empty.append(button('Voir tous les tests', () => { libraryFilter='all'; update(); filters.querySelector('button').focus(); }));
    function update() {
      let count = 0;
      for (const card of cards) { card.hidden=libraryFilter!=='all' && card.dataset.uiStatus!==libraryFilter; if (!card.hidden) count++; }
      filters.querySelectorAll('button').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.uiFilter===libraryFilter)));
      status.textContent=count+' tests affichés'; empty.hidden=count>0;
    }
    head.after(filters); page.append(empty,status); update();
  }
  function words(main) {
    const page = main.querySelector('.v16-page'); if (!page) return;
    const sub = page.querySelector('.v16-head .v16-muted'); if (sub) sub.textContent='Ton vocabulaire, à retrouver et à réviser.';
    page.querySelector('.v16-eyebrow')?.remove();
    const pack = page.querySelector('.v21-vocab-suggest'), notes = page.querySelector('.v23-notes-pack');
    if (pack) { pack.querySelector('b').textContent='Vocabulaire TOEIC · 30 mots'; pack.querySelector('p').textContent='Des mots usuels, leurs sens et leurs exemples.'; }
    if (notes) { notes.querySelector('strong').textContent='Expressions professionnelles · 56 mots'; notes.querySelector('p').textContent='Plusieurs sens et des exemples. Seuls les mots absents sont ajoutés.'; }
    const enrichment = [pack,notes];
    if (page.classList.contains('v16-view-collection')) {
      page.querySelector(':scope > .v16-hero')?.remove();
      const toolbar=page.querySelector('.v16-toolbar');
      const description=toolbar?.nextElementSibling?.matches('p.v16-muted') ? toolbar.nextElementSibling : null;
      const files=document.createElement('div'); files.className='ui-file-actions';
      for (const node of toolbar?.querySelectorAll('[data-v16-exportcsv],[data-v16-importcsv],#v16CsvFile') || []) files.append(node);
      enrichment.unshift(files,description,page.querySelector(':scope > .v16-help'));
      const empty=page.querySelector('.v16-empty');
      if (empty && !(window.__toeicVocabBridge?.list?.() || []).length) empty.textContent='Ta collection est vide. Ajoute un mot avec le bouton ci-dessus, ou découvre les lexiques ci-dessous.';
    }
    const hero=page.querySelector(':scope > .v16-hero');
    if (hero && !(window.__toeicVocabBridge?.list?.() || []).length) {
      hero.querySelector('h2').textContent='Ajoute ton premier mot';
      hero.querySelector('p').textContent='Enregistre un mot depuis un exercice ou ajoute-le à ta collection.';
      const action=hero.querySelector('[data-v16-tab="collection"]'); if (action) action.textContent='Ouvrir ma collection';
    }
    fold(page, 'words-tools', page.classList.contains('v16-view-collection')?'Importer, exporter et enrichir':'Enrichir ma collection', enrichment);
  }
  const isTarget = row => !row.mockTestId && (row.v7Section==='toeic' || /TOEIC.*ciblé/i.test(row.level || ''));
  function progress(main) {
    const page=main.querySelector('.v7-progress-page'); if (!page) return;
    page.querySelector(':scope > h1').textContent='Ma progression';
    page.querySelector(':scope > p').textContent='Tes résultats, tes notions à renforcer et ton historique.';
    const backup=page.querySelector('.v18-account')?.closest('details');
    const legacy=[...page.querySelectorAll(':scope > details.v20-fold')].find(d=>d.querySelector('#v6Backup'));
    if (legacy && backup) {
      const tools=legacy.querySelector('.v6-panel');
      const detail=fold(backup,'compatible-backup','Autres formats de sauvegarde',[tools]);
      if (detail) legacy.remove();
    }
    const panels=[...page.querySelectorAll(':scope > .v6-panel')];
    const trend=panels.find(p=>p.querySelector('svg') || p.querySelector('.v5-empty'));
    const history=panels.find(p=>p.querySelector('.v6-old-session') || p.querySelector('h2')?.textContent.includes('Historique'));
    if (!trend || !history) return;
    const all=(v5History || []).slice().sort((a,b)=>Date.parse(a.date)-Date.parse(b.date));
    const records=[...history.querySelectorAll('.v6-old-session')];
    const tiles=page.querySelector('.v6-stats-cards');
    const filteredEmpty=document.createElement('p'); filteredEmpty.className='ui-history-empty'; filteredEmpty.textContent='Aucune séance terminée dans cette catégorie.'; history.append(filteredEmpty);
    const filters=switcher([['all','Tout'],['target','TOEIC ciblé · Partie 5'],['mock','TOEIC blanc · Partie 5'],['other','Autres exercices']],progressFilter,id=>{progressFilter=id;update();},'Filtrer la progression');
    tiles.before(filters);
    const matches=row=>progressFilter==='all' || (progressFilter==='mock'?!!row.mockTestId:progressFilter==='target'?isTarget(row):!row.mockTestId&&!isTarget(row));
    function update() {
      const rows=all.filter(matches), total=rows.reduce((n,r)=>n+(Number(r.total)||0),0), good=rows.reduce((n,r)=>n+(Number(r.correct)||0),0);
      tiles.innerHTML='<div><strong>'+rows.length+'</strong><small>séances terminées</small></div><div><strong>'+total+'</strong><small>questions corrigées</small></div><div><strong>'+(total?Math.round(good/total*100)+'<span> %</span>':'<span>À venir</span>')+'</strong><small>réussite sur ces séances</small></div>';
      trend.innerHTML='<h2>Évolution des résultats</h2>'+(rows.length?v5TrendSVG(rows.slice(-60).map(r=>({date:r.date,percent:r.total?Math.round(100*r.correct/r.total):0}))):'<div class="ui-empty"><h3>Ta progression commence ici</h3><p>Termine une séance pour retrouver son résultat et suivre ton évolution.</p></div>');
      if (!rows.length) trend.querySelector('.ui-empty').append(button('Choisir une séance →',()=>ToeicNavigation.go('home'),'ui-button primary'));
      const displayed=(v5History || []).slice().reverse().slice(0,60);
      records.forEach((el,i)=>{el.hidden=!matches(displayed[i]);});
      filteredEmpty.hidden=rows.length>0;
      if (all.length===0) history.hidden=true;
      filters.querySelectorAll('button').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.uiFilter===progressFilter)));
      const subtitle=trend.querySelector('h2'); subtitle.insertAdjacentHTML('afterend','<p class="ui-chart-note">Pourcentage de bonnes réponses par séance, sans conversion en score TOEIC.</p>');
    }
    update();
  }
  function enhance() {
    const main=document.querySelector('#v6App main.v7-main'); if (!main) return;
    main.id='toeicMain';main.tabIndex=-1;
    home(main); setup(main); library(main); words(main); progress(main);
    if (v6Session || v7View==='results') {
      document.querySelectorAll('.v20-nav .active').forEach(b=>{b.classList.remove('active');b.removeAttribute('aria-current');});
    }
    const pause=main.querySelector('#v18Pause');
    if (pause) { pause.textContent='Pause'; pause.setAttribute('aria-label','Mettre la séance en pause'); }
    const correction=main.querySelector('.v25-correction');
    if (correction) { correction.setAttribute('role','status'); correction.setAttribute('aria-live','polite'); }
    const question=main.querySelector('.v7-question-title');
    if (question) { question.setAttribute('role','heading');question.setAttribute('aria-level','1');question.lang='en'; }
  }
  v6Render=function() {
    const saved=window.ToeicInterfaceAccessibility?.beforeRender();
    render(); enhance();
    window.ToeicInterfaceAccessibility?.afterRender(saved);
  };
  enhance(); window.ToeicInterfaceAccessibility?.afterRender(null);
})();
