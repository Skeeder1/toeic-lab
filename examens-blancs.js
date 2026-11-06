/* Fixed TOEIC Part 5 practice tests. Tentative answers are graded only on submission. */
(() => {
  'use strict';
  if (window.ToeicMocks) return;
  const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const copy = value => JSON.parse(JSON.stringify(value));
  const originalRender = v6Render, originalAnswer = v6Answer, originalAdvance = v6Advance, originalFinish = v6Finish;
  let grading = false, submitDialog = null, lastStart = 0;
  const submitted = new Set();
  const isMock = session => !!session?.toeicMock?.id;
  const tests = () => {
    const bank = window.ToeicMockBank;
    if (bank?.version !== 1 || bank.part !== 5 || !Array.isArray(bank.tests)) return [];
    return bank.tests.filter(test => typeof test.id === 'string' && Array.isArray(test.questions) && test.questions.length === 30 && test.questions.every(q => q && typeof q.key === 'string' && typeof q.text === 'string' && Array.isArray(q.options) && q.options.length === 4 && Number.isInteger(q.correct) && q.correct >= 0 && q.correct < 4)).slice().sort((a,b) => a.number-b.number);
  };
  function registerBank() {
    for (const test of tests()) for (const item of test.questions) {
      if (V6_ALL.some(q => q.key === item.key)) throw new Error('A mock test key overlaps the training bank.');
      const q = {...item, id:item.id || item.key, source:'toeic', mockTestId:test.id};
      V6_BYKEY.set(q.key, q);
    }
  }
  const pauses = () => {
    const rows = window.__toeicV18?.getPaused?.() || v5Read('toeiclab.sessions.paused.v1', []);
    return Array.isArray(rows) ? rows : [];
  };
  const latestResult = id => (v5History || []).filter(row => row.mockTestId === id).sort((a,b) => Date.parse(b.date)-Date.parse(a.date))[0];
  const pausedTest = id => pauses().filter(row => row.toeicMock?.id === id).sort((a,b) => b.start-a.start)[0];
  const answeredCount = session => session.items.filter(q => Number.isInteger(session.answers?.[q.key]) && session.answers[q.key] >= 0 && session.answers[q.key] < 4).length;

  function pauseActive() {
    if (!v6Session) return true;
    const button = document.querySelector('#v18Pause');
    if (!button) return false;
    button.click();
    return !v6Session;
  }
  function openLibrary() {
    if (!pauseActive()) return false;
    v7View = 'mock-library'; v6Page = 'practice';
    v6Render(); window.scrollTo(0,0);
    const h = document.querySelector('.tm-library h1');
    if (h) { h.tabIndex = -1; h.focus({preventScroll:true}); }
    return true;
  }
  function resume(session) {
    if (window.__toeicV18?.resumePaused) {
      window.__toeicV18.resumePaused(String(session.start));
      return true;
    }
    window.ToeicNavigation?.go('workspace');
    const button = document.querySelector('[data-v18-resume="'+CSS.escape(String(session.start))+'"]');
    if (!button) return false;
    button.click();
    return true;
  }
  function startTest(id) {
    if (!pauseActive()) return false;
    registerBank();
    const test = tests().find(row => row.id === id);
    if (!test) return false;
    const pending = pausedTest(id);
    if (pending) return resume(pending);
    const items = test.questions.map(item => copy(V6_BYKEY.get(item.key)));
    lastStart = Math.max(Date.now(), lastStart+1);
    v7State.section = 'toeic';
    v6Session = {section:'toeic', mode:'exam', feedback:'exam', start:lastStart, count:30, index:0,
      items, v14Queue:[], v14Unique:true, v18Managed:true, answers:{}, answerTimes:{},
      settings:{mode:'exam',level:'toeic',length:'30',feedback:'exam',topics:[...new Set(items.map(q => q.group))]},
      toeicMock:{id:test.id,title:test.title || 'Test blanc '+String(test.number).padStart(2,'0'),number:test.number,part:5,mapOpen:false}};
    v6Page='practice'; v7View='workspace'; v6ShowTranslation=false; v6ShowChoices=false;
    v7Save(); v6Render(); window.scrollTo(0,0);
    return true;
  }

  function libraryMarkup() {
    const rows = tests();
    return `<section class="tm-library v20-container"><div class="tm-breadcrumb"><button type="button" data-tm-home>Accueil</button><span>›</span><span>TOEIC blanc</span></div><header class="tm-library-heading"><span class="tm-kicker">PARTIE 5 UNIQUEMENT</span><h1>TOEIC blanc</h1><p>Choisis un test de 30 questions. La correction apparaît après validation.</p></header>${rows.length ? `<div class="tm-test-grid">${rows.map(test => {
      const pending=pausedTest(test.id), result=latestResult(test.id);
      const status=pending?'En pause':result?'Terminé':'À faire';
      return `<article class="tm-test-card ${pending?'is-paused':result?'is-complete':''}"><header><span class="tm-test-number">${String(test.number).padStart(2,'0')}</span><span class="tm-test-status">${status}</span></header><h2>${esc(test.title || 'Test blanc '+String(test.number).padStart(2,'0'))}</h2><p>Partie 5 <span>·</span> 30 questions</p>${pending?`<small>${answeredCount(pending)} réponses conservées</small>`:result?`<small>Dernier résultat : ${Number(result.correct)||0} / 30</small>`:'<small>Énoncés et ordre fixes</small>'}<button type="button" data-tm-start="${esc(test.id)}">${pending?'Reprendre':result?'Refaire le test':'Commencer'} <span aria-hidden="true">→</span></button></article>`;
    }).join('')}</div>`:'<p class="tm-empty">Les tests blancs sont en préparation.</p>'}</section>`;
  }
  function renderLibrary(main) {
    main.classList.remove('v20-context','v20-quiz','v20-words','v20-progress','v20-homepage');
    main.classList.add('tm-library-page'); main.innerHTML=libraryMarkup();
    document.querySelectorAll('.v20-nav [aria-current],.v20-nav .active').forEach(button => { button.removeAttribute('aria-current'); button.classList.remove('active'); });
    main.querySelector('[data-tm-home]').onclick=() => window.ToeicNavigation?.go('home');
    main.querySelectorAll('[data-tm-start]').forEach(button => button.onclick=() => startTest(button.dataset.tmStart));
  }
  function mountHomeEntry(main) {
    const grid=main.querySelector('.v20-home .v20-paths');
    if (!grid || main.querySelector('.tm-toeic-paths')) return;
    const button=document.createElement('button'); button.type='button'; button.className='v20-path tm-home-entry'; button.dataset.tmLibrary='';
    button.innerHTML='<span class="v20-path-top"><span class="v20-path-icon" aria-hidden="true">▤</span><span class="v20-arrow" aria-hidden="true">↗</span></span><strong>TOEIC blanc</strong><small>Partie 5 uniquement. Dix tests fixes de 30 questions, avec correction à la fin.</small><em>10 TESTS · PARTIE 5</em>';
    button.onclick=openLibrary;
    const targeted=grid.querySelector('[data-v20-section="toeic"]');
    const section=document.createElement('section'); section.className='tm-toeic-section'; section.setAttribute('aria-labelledby','tmPathsTitle');
    section.innerHTML='<h2 id="tmPathsTitle">TOEIC · Partie 5</h2><div class="tm-toeic-paths"></div>';
    const paths=section.querySelector('.tm-toeic-paths');
    if (targeted) paths.append(targeted);
    paths.append(button); grid.before(section);
  }

  function goQuestion(index) {
    const session=v6Session;
    if (!isMock(session) || grading || !Number.isInteger(index) || index<0 || index>=session.items.length) return;
    session.index=index; session.toeicMock.mapOpen=false;
    v7Save(); v6Render();
    document.querySelector('.tm-paper')?.scrollIntoView({block:'nearest'});
  }
  function examMarkup(session) {
    const q=session.items[session.index], choice=session.answers[q.key], count=answeredCount(session), last=session.index===29;
    return `<section class="tm-exam" aria-label="TOEIC blanc Partie 5"><div class="tm-exam-top"><div><span class="tm-kicker">TOEIC BLANC · PARTIE 5</span><h1>${esc(session.toeicMock.title)}</h1></div><div class="tm-exam-actions"><button type="button" id="v18Pause">Mettre en pause</button><button type="button" data-tm-finish>Terminer</button></div></div><div class="tm-step"><strong>Question ${101+session.index}<span> / 130</span></strong><span>${count} / 30 réponses</span></div><div class="tm-progress" aria-hidden="true"><span style="width:${count/30*100}%"></span></div><div class="v7-question-paper tm-paper"><h2 lang="en">${esc(q.text).replace(/_{2,}/g,'<span class="tm-gap">____</span>')}</h2><div class="tm-answers" role="group" aria-label="Choix de réponse">${q.options.map((option,i) => `<button type="button" data-tm-answer="${i}" aria-pressed="${choice===i}" class="${choice===i?'is-chosen':''}"><span class="tm-letter">${'ABCD'[i]}</span><span lang="en">${esc(option)}</span></button>`).join('')}</div><div class="tm-question-navigation"><button type="button" data-tm-previous ${session.index===0?'disabled':''}>← Précédente</button><button type="button" class="tm-primary" data-tm-next>${last?'Relire et terminer':'Suivante →'}</button></div></div><details class="tm-question-map" ${session.toeicMock.mapOpen?'open':''}><summary>Voir les 30 questions</summary><p>Tu peux passer une question et y revenir avant de terminer.</p><div>${session.items.map((item,i) => `<button type="button" data-tm-question="${i}" class="${i===session.index?'is-current ':''}${Number.isInteger(session.answers[item.key])&&session.answers[item.key]>=0?'is-answered':''}" ${i===session.index?'aria-current="step"':''} aria-label="Question ${101+i}${Number.isInteger(session.answers[item.key])&&session.answers[item.key]>=0?', réponse choisie':''}">${101+i}</button>`).join('')}</div></details></section>`;
  }
  function renderExam(main) {
    const session=v6Session;
    const inheritedPause=main.querySelector('#v18Pause')?.onclick;
    main.classList.add('tm-exam-page'); main.innerHTML=examMarkup(session);
    main.querySelector('#v18Pause').onclick=() => {
      if (inheritedPause) inheritedPause();
      if (!v6Session) openLibrary();
    };
    main.querySelector('[data-tm-finish]').onclick=requestSubmission;
    main.querySelectorAll('[data-tm-answer]').forEach(button => button.onclick=() => v6Answer(Number(button.dataset.tmAnswer)));
    main.querySelector('[data-tm-previous]').onclick=() => goQuestion(session.index-1);
    main.querySelector('[data-tm-next]').onclick=() => session.index===29?requestSubmission():goQuestion(session.index+1);
    main.querySelectorAll('[data-tm-question]').forEach(button => button.onclick=() => goQuestion(Number(button.dataset.tmQuestion)));
    main.querySelector('.tm-question-map').addEventListener('toggle',event => {
      if (v6Session===session) { session.toeicMock.mapOpen=event.currentTarget.open; v7Save(); }
    });
  }

  function requestSubmission() {
    const session=v6Session;
    if (!isMock(session) || grading || submitted.has(String(session.start))) return;
    if (submitDialog?.open) return;
    const count=answeredCount(session), missing=30-count;
    submitDialog=document.createElement('dialog'); submitDialog.className='tm-submit-dialog'; submitDialog.id='tmSubmit';
    submitDialog.setAttribute('aria-labelledby','tmSubmitTitle');
    submitDialog.innerHTML=`<h2 id="tmSubmitTitle">Terminer le test ?</h2><p>${count} / 30 réponses choisies.${missing?` Les ${missing} ${missing===1?'question sans réponse sera comptée fausse':'questions sans réponse seront comptées fausses'}.`:''}</p><div><button type="button" data-tm-continue>Continuer le test</button><button type="button" class="tm-primary" data-tm-submit>Confirmer et corriger</button></div>`;
    document.body.append(submitDialog);
    submitDialog.querySelector('[data-tm-continue]').onclick=() => submitDialog.close();
    submitDialog.querySelector('[data-tm-submit]').onclick=() => {
      if (v6Session!==session || grading) return;
      submitDialog.querySelector('[data-tm-submit]').disabled=true;
      submitDialog.close(); gradeSession(session);
    };
    const dialog=submitDialog;
    dialog.addEventListener('close',() => { dialog.remove(); if (submitDialog===dialog) submitDialog=null; });
    submitDialog.showModal(); submitDialog.querySelector('[data-tm-continue]').focus();
  }
  function gradeSession(session) {
    const token=String(session.start);
    if (grading || submitted.has(token) || v6Session!==session) return;
    grading=true; submitted.add(token);
    const selections={...session.answers}, originalIndex=session.index;
    session.answers={}; session.toeicMock.submittedAt=new Date().toISOString();
    try {
      // Reuse the application's answer event, observation and skill update chain once.
      for (let i=0;i<session.items.length;i++) {
        session.index=i;
        const choice=selections[session.items[i].key];
        originalAnswer(Number.isInteger(choice)&&choice>=0&&choice<4?choice:-1);
      }
      session.index=originalIndex;
      grading=false;
      originalFinish();
      const result=v6ResultCache?.r;
      if (result) {
        result.mockTestId=session.toeicMock.id;
        result.mockPart=5; result.mockTitle=session.toeicMock.title; result.mockQuestionCount=30;
        result.level='TOEIC blanc · Partie 5 · '+session.toeicMock.title;
        result.answered=Object.values(selections).filter(value => Number.isInteger(value)&&value>=0&&value<4).length;
        for (const item of result.questions||[]) if (item.chosen===-1) item.chosen=null;
        v5Write(V5_KEY,v5History);
      }
      v6Render(); window.scrollTo(0,0);
      const score=document.querySelector('.v24-result-head h1');
      if (score) { score.tabIndex=-1; score.focus({preventScroll:true}); }
    } finally { grading=false; }
  }
  function enhanceResults(main) {
    const result=v6ResultCache?.r;
    if (!result?.mockTestId) return;
    const header=main.querySelector('.v24-result-head');
    if (header) {
      const title=document.createElement('p'); title.className='tm-result-title'; title.textContent='TOEIC blanc · Partie 5 · '+result.mockTitle;
      header.prepend(title);
    }
    main.querySelectorAll('.v24-question-number').forEach(number => { number.textContent=String(100+Number(number.textContent)); });
    const again=main.querySelector('[data-v7-again]');
    if (again) { again.textContent='Autres tests blancs →'; again.onclick=openLibrary; }
  }

  v6Answer=function(index) {
    const session=v6Session;
    if (!isMock(session)) return originalAnswer(index);
    if (grading || !Number.isInteger(index) || index<0 || index>3) return;
    session.answers[session.items[session.index].key]=index;
    v7Save(); v6Render();
  };
  v6Advance=function() {
    if (!isMock(v6Session)) return originalAdvance();
    if (v6Session.index===29) requestSubmission(); else goQuestion(v6Session.index+1);
  };
  v6Finish=function() {
    if (!isMock(v6Session)) return originalFinish();
    requestSubmission();
  };
  v6Render=function() {
    if (grading) return;
    originalRender();
    const main=document.querySelector('#v6App main.v7-main'); if (!main) return;
    main.classList.remove('tm-library-page','tm-exam-page');
    if (isMock(v6Session)&&v7View==='workspace') renderExam(main);
    else if (v7View==='mock-library') renderLibrary(main);
    else if (v7View==='results') enhanceResults(main);
    else mountHomeEntry(main);
  };

  registerBank();
  if (!v6Session) {
    const draft=v5Read(V6_DRAFT_KEY,null);
    if (isMock(draft)&&Array.isArray(draft.items)&&draft.items.length===30&&draft.items.every(q => V6_BYKEY.has(q.key))&&Number.isInteger(draft.index)&&draft.index>=0&&draft.index<30) {
      v6Session=draft; v7State.section='toeic'; v7View='workspace'; v6Page='practice';
    }
  }
  window.ToeicMocks=Object.freeze({open:openLibrary,start:startTest,registerBank});
  v6Render();
})();
