/* Contextual vocabulary help. Local data only; never reads the expected answer. */
(() => {
  'use strict';
  const originalWords = v5WordHtml, originalMeaning = v5Meaning;
  const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const norm = s => String(s ?? '').toLowerCase().replace(/’/g,"'").replace(/\s+/g,' ').trim();
  const escapeRE = s => s.replace(/[.*+?^${}()|[\]\\]/g,'\\$&');
  let entries = new Map(), aliases = new Map(), patterns = [], tooltip, dialog, tooltipAnchor, tooltipPinned=false, hideTimer;
  const current = () => typeof v6Session !== 'undefined' ? v6Session?.items?.[v6Session.index] : null;
  const baseSense = e => ({id:'general', meaning:e.meaning, context:e.context || '', frenchExample:e.translation || ''});

  function refresh() {
    entries = new Map(); aliases = new Map(); patterns = [];
    for (const [term,meaning] of Object.entries(window.__toeicBasePhrases || {}))
      entries.set(norm(term), {term, senses:[{id:'general',meaning}], sources:[]});
    for (const e of window.TOEIC_EXPRESSION_ENTRIES || []) entries.set(norm(e.term), e);
    for (const e of window.__toeicPhotoV23?.items || []) {
      if (!entries.has(norm(e.term))) entries.set(norm(e.term), {...e,senses:e.senses?.length?e.senses:[baseSense(e)]});
    }
    // Personal meanings remain first. Adding the dictionary never rewrites an existing word.
    for (const e of window.__toeicVocabBridge?.list() || []) {
      const k=norm(e.term), prior=entries.get(k), own=e.senses?.length?e.senses:[baseSense(e)];
      const seen=new Set(own.map(s=>norm(s.meaning)));
      entries.set(k,{...prior,...e,senses:[...own,...(prior?.senses||[]).filter(s=>!seen.has(norm(s.meaning)))]});
    }
    for (const e of entries.values()) {
      e.senses=(e.senses||[]).filter(s=>s.meaning);
      if (!e.senses.length) continue;
      for (const f of [e.term,...(e.forms||[])]) {
        aliases.set(norm(f),norm(e.term));
        patterns.push({entry:e,re:new RegExp('\\b'+norm(f).split(' ').map(escapeRE).join('\\s+')+'\\b','gi')});
      }
      if (e.separable && norm(e.term).split(' ').length===2) {
        const forms=[...new Set([e.term,...(e.forms||[])].map(f=>norm(f).split(' ')[0]))];
        const particle=escapeRE(norm(e.term).split(' ')[1]);
        const determiner='(?:the|a|an|my|your|his|her|our|their|this|that|these|those|one|two|three|four|five|some|any|[0-9]+)';
        const object='(?:(?:it|them|me|you|him|her|us)\\s+|'+determiner+'\\s+(?:[a-z]+\\s+){0,3})';
        patterns.push({entry:e,re:new RegExp('\\b(?:'+forms.map(escapeRE).join('|')+')\\s+'+object+particle+'\\b','gi')});
      }
    }
  }

  function entryFor(term, fallback='') {
    const k=aliases.get(norm(term)) || norm(term), e=entries.get(k);
    if (e) return e;
    const meaning=fallback || originalMeaning(term);
    if (!meaning || ['—','sens non renseigné','traduction non renseignée'].includes(meaning)) return null;
    return {term,senses:[{id:'general',meaning}],sources:[],limited:true};
  }

  function contextual(entry, sentence='') {
    // Evaluate this expression as a candidate for the gap, without consulting the answer key.
    sentence=String(sentence).replace(/_{2,}|\[GAP\]/,entry.term);
    // Look only near the expression/gap; a word elsewhere in a long text is weak evidence.
    let at=sentence.search(/_{2,}|\[GAP\]/);
    if(at<0)at=norm(sentence).indexOf(norm(entry.term));
    const local=at<0?sentence:sentence.slice(Math.max(0,at-85),at+135);
    const matches=entry.senses.filter(s=>{
      if (!s.cues) return false;
      try {return new RegExp(s.cues,'i').test(local);} catch {return false;}
    });
    return matches.length===1?matches[0]:null;
  }

  function span(display, entry, focusable, info) {
    const suggested=contextual(entry,info.sentence), gloss=suggested?.meaning || entry.senses.map(s=>s.meaning).join(' ; ');
    return `<span class="v5-word tl-lexeme" ${focusable?'tabindex="0" role="button"':''} data-tl-term="${esc(entry.term)}" data-gloss="${esc(gloss)}" data-tl-sentence="${esc(info.sentence||'')}" data-tl-choice="${info.choice?'1':'0'}" aria-label="Comprendre ${esc(display)}">${esc(display)}</span>`;
  }

  function render(text, focusable=true, info={}) {
    text=String(text); const matches=[];
    for (const p of patterns) {
      p.re.lastIndex=0;
      for(const m of text.matchAll(p.re))matches.push({start:m.index,end:m.index+m[0].length,display:m[0],entry:p.entry});
    }
    matches.sort((a,b)=>a.start-b.start || b.end-a.end);
    let end=0,html='';
    for(const m of matches){if(m.start<end)continue;html+=originalWords(text.slice(end,m.start),focusable)+span(m.display,m.entry,focusable,info);end=m.end;}
    html+=originalWords(text.slice(end),focusable);
    const template=document.createElement('template');template.innerHTML=html;
    for(const el of template.content.querySelectorAll('.v5-word:not([data-tl-term])')){
      const e=entryFor(el.textContent,el.dataset.gloss);if(!e)continue;
      el.outerHTML=span(el.textContent,e,focusable,info);
    }
    return template.innerHTML;
  }

  v5WordHtml=function(text,focusable=true){const q=current();return render(text,focusable,{sentence:q?.text||'',choice:!!q?.options?.includes(String(text))});};
  v5Meaning=function(term){const e=entryFor(term);if(!e)return originalMeaning(term);const s=contextual(e,current()?.text||'');return s?.meaning || e.senses.map(x=>x.meaning).join(' ; ');};

  function markHelp(){if(typeof v6Session!=='undefined'&&v6Session&&!v6Session.v14Helped){v6Session.v14Helped=true;v7Save();}}
  function cancelHide(){clearTimeout(hideTimer);}
  function removeTooltip(){cancelHide();tooltipAnchor?.removeAttribute('aria-describedby');tooltip?.remove();tooltip=null;tooltipAnchor=null;tooltipPinned=false;}
  function deferHide(){cancelHide();if(!tooltipPinned)hideTimer=setTimeout(removeTooltip,tooltip?.classList.contains('has-senses')?180:0);}
  function infoFor(el){return {sentence:el.dataset.tlSentence||'',choice:el.dataset.tlChoice==='1'};}
  function summary(e,info){const s=contextual(e,info.sentence);return s?`<small>Sens suggéré dans cette phrase</small><strong>${esc(s.meaning)}</strong>`:e.senses.length>1?`<small>${e.senses.length} sens possibles</small><strong>Le sens dépend du contexte</strong>`:`<small>Sens courant</small><strong>${esc(e.senses[0].meaning)}</strong>`;}
  function showTooltip(el,pinned=false){
    if(dialog?.open)return;
    cancelHide();
    if(tooltip&&tooltipAnchor===el){tooltipPinned=tooltipPinned||pinned;return;}
    const e=entryFor(el.dataset.tlTerm,el.dataset.gloss);if(!e)return;
    removeTooltip();tooltipAnchor=el;tooltipPinned=pinned;markHelp();
    const info=infoFor(el),suggested=contextual(e,info.sentence);
    const meaning=suggested?.meaning || (e.senses.length===1?e.senses[0].meaning:e.senses.slice(0,3).map(s=>s.meaning).join(' / '));
    const multiple=e.senses.length>1;
    tooltip=document.createElement('div');tooltip.id='tlTooltip';tooltip.className='tl-tooltip'+(multiple?' has-senses':'');tooltip.setAttribute('role',multiple?'dialog':'tooltip');tooltip.setAttribute('aria-label','Traduction de '+e.term);
    tooltip.innerHTML=`<p class="tl-context-gloss">${esc(meaning)}</p>${multiple?`<button type="button" class="tl-sense-count" aria-label="Voir les ${e.senses.length} sens de ${esc(e.term)}" title="Tous les sens">${e.senses.length}</button>`:''}`;
    const count=tooltip.querySelector('.tl-sense-count');
    if(count)count.onclick=event=>{event.preventDefault();event.stopPropagation();showEntry(e,info);};
    el.setAttribute('aria-describedby','tlTooltip');
    tooltip.addEventListener('pointerenter',cancelHide);tooltip.addEventListener('pointerleave',deferHide);
    document.body.appendChild(tooltip);
    const r=el.getBoundingClientRect(), w=tooltip.getBoundingClientRect();
    tooltip.style.left=Math.max(12,Math.min(r.left,innerWidth-w.width-12))+'px';
    tooltip.style.top=(r.top-w.height-7>=8?r.top-w.height-7:Math.min(r.bottom+7,innerHeight-w.height-8))+'px';
  }

  function makeDialog(title){
    removeTooltip();const previous=dialog;previous?.close();previous?.remove();const restoreFocus=document.activeElement;
    const d=document.createElement('dialog');d.className='tl-dialog';d.setAttribute('aria-label',title);document.body.appendChild(d);dialog=d;
    d.addEventListener('close',()=>{d.remove();if(dialog===d){dialog=null;if(restoreFocus?.isConnected)restoreFocus.focus();}});
    d.addEventListener('click',e=>{if(e.target===d){const r=d.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)d.close();}});
    return d;
  }
  function sourceLinks(e){return [...new Set(e.sources||[])].flatMap(s=>{try{const u=new URL(s);return u.protocol==='https:'?[`<a href="${esc(u.href)}" target="_blank" rel="noopener noreferrer">${esc(u.hostname.replace('www.',''))}</a>`]:[];}catch{return [];}}).join(' · ');}
  function showEntry(e,info={}){
    const d=makeDialog('Sens de '+e.term), suggested=contextual(e,info.sentence);
    // Preserve the real gap: filling it with a distractor would invent a faulty example.
    const example=info.sentence;
    d.innerHTML=`<div class="tl-dialog-body"><header><div><small>COMPRENDRE LE VOCABULAIRE</small><h2>${esc(e.term)}</h2></div><button type="button" data-tl-close aria-label="Fermer l’aide vocabulaire">×</button></header><div class="tl-context">${summary(e,info)}${example?`<p>Phrase de l’exercice : <q>${esc(example)}</q></p>`:''}${info.choice?'<p class="tl-note">Cette aide explique le vocabulaire ; elle ne valide pas ton choix de réponse.</p>':''}${!suggested&&e.senses.length>1?'<p>Le contexte ne permet pas de choisir un sens avec certitude. Compare les emplois ci-dessous.</p>':''}</div><h3>${e.senses.length>1?'Les sens à connaître':'Un emploi à connaître'}</h3><div class="tl-senses">${e.senses.map((s,i)=>`<article ${suggested===s?'class="tl-suggested"':''}><div>${e.senses.length>1?`<span>${i+1}</span>`:''}<h4>${esc(s.meaning)}</h4>${s.type?`<small>${esc(s.type)}</small>`:''}</div>${s.note?`<p>${esc(s.note)}</p>`:''}${s.context?`<blockquote lang="en">${esc(s.context)}</blockquote>`:''}${s.frenchExample?`<p class="tl-french">${esc(s.frenchExample)}</p>`:''}</article>`).join('')}</div><p class="tl-note">${e.limited?'Définition du lexique existant. Tous les emplois ne sont pas encore détaillés.':'Sens courants du lexique local, sans garantie d’exhaustivité. Le sens suggéré est une aide à confirmer avec la phrase.'}</p>${sourceLinks(e)?`<p class="tl-sources">Dictionnaires : ${sourceLinks(e)}</p>`:''}<footer><p data-tl-status role="status"></p><button type="button" data-tl-save>Ajouter à Mes mots</button></footer></div>`;
    d.querySelector('[data-tl-close]').onclick=()=>d.close();
    d.querySelector('[data-tl-save]').onclick=()=>{
      const bridge=window.__toeicVocabBridge;if(!bridge)return;
      const prior=bridge.list().find(x=>norm(x.term)===norm(e.term));
      const own=prior?(prior.senses?.length?prior.senses:[baseSense(prior)]):[];
      const seen=new Set(own.map(s=>norm(s.meaning)));
      const additions=e.senses.filter(s=>!seen.has(norm(s.meaning))).map((s,i)=>({...s,id:'lex-'+norm(e.term).replace(/[^a-z0-9]/g,'-')+'-'+(s.id||i),context:s.context||'',frenchExample:s.frenchExample||''}));
      const senses=[...own,...additions];
      const result=bridge.upsert({...prior,term:prior?.term||e.term,meaning:prior?.meaning||suggested?.meaning||e.senses[0].meaning,context:prior?.context||example||e.senses[0].context||'',senses},prior?.term);
      d.querySelector('[data-tl-status]').textContent=result.ok?(prior?'Sens ajoutés ; tes définitions et révisions existantes sont conservées.':'Ajouté à Mes mots avec ses différents sens.'):result.error;
      if(result.ok){refresh();d.querySelector('[data-tl-save]').disabled=true;}
    };
    d.showModal();markHelp();
  }

  function showQuestionVocabulary(){
    const lexemes=[...document.querySelectorAll('.v7-answer-text [data-tl-term],.v7-question-title [data-tl-term]')];
    const unique=[...new Map(lexemes.map(el=>[norm(el.dataset.tlTerm),el])).values()];
    if(!unique.length)return;
    const d=makeDialog('Vocabulaire de la question');
    d.innerHTML=`<div class="tl-dialog-body"><header><h2>Vocabulaire de la question</h2><button type="button" data-tl-close aria-label="Fermer l’aide vocabulaire">×</button></header><p>Choisis un mot ou une expression pour consulter ses sens.</p><div class="tl-term-list">${unique.map((el,i)=>`<button type="button" data-tl-pick="${i}">${esc(el.dataset.tlTerm)}</button>`).join('')}</div></div>`;
    d.querySelector('[data-tl-close]').onclick=()=>d.close();
    d.querySelectorAll('[data-tl-pick]').forEach(b=>b.onclick=()=>{const el=unique[Number(b.dataset.tlPick)];showEntry(entryFor(el.dataset.tlTerm,el.dataset.gloss),infoFor(el));});d.showModal();
  }

  document.addEventListener('pointerover',e=>{const el=e.target.closest?.('[data-tl-term]');if(el&&!el.contains(e.relatedTarget))showTooltip(el);});
  document.addEventListener('pointerout',e=>{if(e.target.closest?.('[data-tl-term]')&&!tooltip?.contains(e.relatedTarget))deferHide();});
  document.addEventListener('focusin',e=>{const el=e.target.closest?.('[data-tl-term]');if(el)showTooltip(el);});
  document.addEventListener('focusout',e=>{if(!tooltip?.contains(e.relatedTarget))deferHide();});
  document.addEventListener('scroll',e=>{if(e.target===document||e.target?.contains?.(tooltipAnchor))removeTooltip();},true);
  window.addEventListener('resize',removeTooltip);
  document.addEventListener('click',e=>{
    const el=e.target.closest?.('[data-tl-term]');if(!el){if(!tooltip?.contains(e.target))removeTooltip();return;}
    e.preventDefault();e.stopImmediatePropagation();
    const entry=entryFor(el.dataset.tlTerm,el.dataset.gloss);
    if(entry)showEntry(entry,infoFor(el));
  },true);
  document.addEventListener('keydown',e=>{
    if(e.key==='Escape'){removeTooltip();return;}
    const el=e.target.closest?.('[data-tl-term]');
    if(el&&el.tabIndex===0&&(e.key==='Enter'||e.key===' ')){e.preventDefault();e.stopImmediatePropagation();const entry=entryFor(el.dataset.tlTerm,el.dataset.gloss);if(entry)showEntry(entry,infoFor(el));}
  },true);

  const originalRender=v6Render;
  v6Render=function(){refresh();removeTooltip();originalRender();
    // Keep answered choices read-only while their vocabulary remains interactive.
    document.querySelectorAll('.v7-answers > button:disabled').forEach(button=>{
      const card=document.createElement('div');card.className=button.className+' tl-answered-choice';card.dataset.v7Answer=button.dataset.v7Answer;
      card.setAttribute('role','group');card.setAttribute('aria-label','Choix '+(button.querySelector('.v7-letter')?.textContent||''));card.innerHTML=button.innerHTML;
      card.querySelectorAll('[data-tl-term]').forEach(word=>{word.tabIndex=0;word.setAttribute('role','button');});button.replaceWith(card);
    });
  };
  window.ToeicLexicon={lookup:(term,info={})=>{const e=entryFor(term);return e?{...e,suggested:contextual(e,info.sentence)}:null;},render,refresh};
  // V21/V23 questions register after the old draft restorers. Retry only when
  // every saved item is now known; keep the saved option order and answers.
  if(!v6Session){
    const draft=v5Read(V6_DRAFT_KEY,null);
    if(draft&&Array.isArray(draft.items)&&draft.items.length&&Number.isInteger(draft.index)&&draft.index>=0&&draft.index<draft.items.length&&draft.items.every(q=>V6_BYKEY.has(q.key)&&Array.isArray(q.options)&&q.options.length===4)){
      v6Session=draft;v6Page='practice';v7View='workspace';
    }
  }
  refresh();v6Render();
})();
