/* Focus and form semantics for the existing learning interface. No learning state is written. */
(() => {
  'use strict';
  if (window.ToeicInterfaceAccessibility) return;
  const customSelector = '#v16Modal,#v8CatalogLayer,#v8BasicPop,#grammarDialog.open,#relativeDialog.open,#gsDialog.open';
  const watchedSelector = '#v16Modal,#v8CatalogLayer,#v8BasicPop,#grammarDialog,#relativeDialog,#gsDialog,dialog';
  const controls = 'button,a[href],input:not([type="hidden"]),select,textarea,summary,[tabindex]:not([tabindex="-1"])';
  let intent = null, lastOutsideFocus = null, managed = null, renderedState = null, labelSequence = 0, syncing = false;
  const inertOwned = new Map(), openers = new WeakMap();

  const visible = element => !!element?.isConnected && !element.hidden && element.getClientRects().length > 0 && getComputedStyle(element).visibility !== 'hidden';
  const nativeModal = () => [...document.querySelectorAll('dialog[open]')].reverse().find(visible);
  const customModal = () => [...document.querySelectorAll(customSelector)].reverse().find(element => visible(element) && !element.classList.contains('v92-suspended') && element.getAttribute('aria-hidden') !== 'true');
  const main = () => document.querySelector('main.v7-main');
  const focus = element => {
    if (!visible(element) || element.closest('[inert]') || element.disabled) return false;
    if (!element.matches(controls) && element.tabIndex < 0) element.tabIndex = -1;
    element.focus({preventScroll:true});
    return document.activeElement === element;
  };
  function describe(element) {
    if (!(element instanceof Element) || element === document.body) return null;
    const control = element.closest('button,input,select,textarea,summary,a[href],[tabindex]') || element;
    if (control.id) return {id:control.id};
    const attrs = [...control.attributes].filter(attribute => attribute.name.startsWith('data-') && attribute.name !== 'data-tone').map(attribute => [attribute.name,attribute.value]);
    if (attrs.length) return {tag:control.tagName.toLowerCase(),attrs,role:control.getAttribute('role')};
    return null;
  }
  function equivalent(description) {
    if (!description) return null;
    if (description.id) return document.getElementById(description.id);
    const selector = description.tag + description.attrs.map(([name,value]) => '['+name+'="'+CSS.escape(value)+'"]').join('') + (description.role?'[role="'+CSS.escape(description.role)+'"]':'');
    return [...document.querySelectorAll(selector)].find(visible) || null;
  }
  function pageState() {
    const root = main();
    const session = typeof v6Session === 'undefined' ? null : v6Session;
    const view = typeof v7View === 'undefined' ? '' : v7View;
    const section = typeof v7State === 'undefined' ? '' : v7State.section;
    const screen = root?.querySelector('.tm-exam')?'mock':root?.querySelector('.tm-library')?'library':root?.classList.contains('v20-homepage')?'home':view;
    return {route:screen+'|'+section+'|'+!!session,question:session ? String(session.start)+'|'+String(session.items?.[session.index]?.key || session.index) : ''};
  }
  document.addEventListener('click', event => {
    const element = event.target instanceof Element ? event.target.closest(controls) : null;
    if (element) intent = {element,description:describe(element),at:performance.now(),modal:!!element.closest('dialog,[role="dialog"]')};
  }, true);
  document.addEventListener('focusin', event => {
    if (event.target instanceof Element && !event.target.closest('dialog,[role="dialog"]')) lastOutsideFocus = {element:event.target,description:describe(event.target)};
  }, true);

  function beforeRender() {
    const active = document.activeElement;
    const action = intent && performance.now()-intent.at < 1500 ? intent : null;
    intent = null;
    return {...(renderedState || pageState()),active,description:action?.description || describe(active),action:action?.element || active,
      interacted:!!action || (active !== document.body && !!active?.closest('#v6App')),
      skip:!!nativeModal() || !!customModal() || !!action?.modal};
  }
  function pageHeading() {
    const root = main();
    return root?.querySelector('.tm-paper h2,.v7-question-title') || [...root?.querySelectorAll('h1,h2') || []].find(visible) || root;
  }
  function afterRender(saved) {
    enhanceForms(main());
    enhanceSemantics();
    syncDialogs();
    const now = pageState();
    renderedState = now;
    if (!saved?.interacted || saved.skip || nativeModal() || customModal()) return;
    if (saved.route !== now.route || saved.question !== now.question) { focus(pageHeading()); return; }
    const action = saved.action;
    if (action?.matches?.('[data-v7-answer],.tl-answered-choice')) {
      focus(main()?.querySelector('.v7-correction') || document.getElementById('v7Next'));
      return;
    }
    if (focus(equivalent(saved.description))) return;
    if (action?.matches?.('[data-v16-reveal]')) {
      focus(main()?.querySelector('[data-v16-rate]'));
    } else if (action?.matches?.('[data-v16-rate],[data-v16-undo]')) {
      focus(main()?.querySelector('[data-v16-reveal]') || main()?.querySelector('.v16-hero h2'));
    } else if (!saved.active?.isConnected) {
      focus(pageHeading());
    }
  }

  function enhanceForms(root) {
    if (!root) return;
    const search = root.querySelector('#v16Search');
    if (search) search.setAttribute('aria-label','Rechercher dans mes mots');
    root.querySelectorAll('.v16-field').forEach(field => {
      const label = field.querySelector(':scope > label'), input = field.querySelector(':scope > input,:scope > textarea,:scope > select');
      if (!label || !input || label.contains(input)) return;
      if (!input.id) input.id = 'ui-field-'+(++labelSequence);
      label.htmlFor = input.id;
    });
    [['v19SvgFile','Importer un schéma SVG'],['v16EditImageFile','Importer une image']].forEach(([id,label]) => root.querySelector('#'+id)?.setAttribute('aria-label',label));
    root.querySelector('#v16EditTerm')?.setAttribute('aria-required','true');
    root.querySelectorAll('[data-v8-cat]').forEach(button => button.setAttribute('aria-pressed',String(button.classList.contains('selected'))));
  }
  function enhanceSemantics() {
    const root = main();
    if (!root) return;
    const title = root.querySelector('.v7-question-title');
    if (title && !/^H[1-6]$/.test(title.tagName)) { title.setAttribute('role','heading'); title.setAttribute('aria-level','1'); }
    root.querySelector('.v7-answers')?.setAttribute('role','group');
    root.querySelector('.v7-answers')?.setAttribute('aria-label','Choix de réponse');
    root.querySelectorAll('[data-tm-start]').forEach(button => {
      const title = button.closest('.tm-test-card')?.querySelector('h2')?.textContent?.trim() || button.dataset.tmStart;
      const verb = button.textContent.includes('Reprendre')?'Reprendre':button.textContent.includes('Refaire')?'Refaire':'Commencer';
      const number = button.closest('.tm-test-card')?.querySelector('.tm-test-number')?.textContent?.trim() || '';
      button.setAttribute('aria-label',verb+' '+title+(number && !title.includes(number)?' '+number:'' )+', Partie 5');
    });
    const session = typeof v6Session === 'undefined' ? null : v6Session;
    if (session) {
      const mock = !!session.toeicMock, bar = root.querySelector(mock?'.tm-progress':'.v7-quiz-bar');
      const maximum = mock?30:Number(session.count || session.items.length);
      const value = mock ? session.items.filter(q => Number.isInteger(session.answers?.[q.key]) && session.answers[q.key] >= 0).length : Number(session.index)+1;
      if (bar && Number.isFinite(maximum) && maximum > 0 && session.count !== null) {
        bar.removeAttribute('aria-hidden');
        bar.setAttribute('role','progressbar'); bar.setAttribute('aria-label',mock?'Réponses choisies':'Avancement de la séance');
        bar.setAttribute('aria-valuemin','0'); bar.setAttribute('aria-valuemax',String(maximum)); bar.setAttribute('aria-valuenow',String(Math.min(maximum,value)));
      }
    }
    root.querySelectorAll('.v16-tabbar [role="tab"]').forEach(tab => { tab.tabIndex = tab.getAttribute('aria-selected') === 'true' ? 0 : -1; });
    root.querySelector('.v16-tabbar')?.setAttribute('aria-label','Mes mots');
  }

  function restoreInert() {
    for (const [element,value] of inertOwned) if (element.inert) element.inert = value;
    inertOwned.clear();
  }
  function inertSiblings(layer) {
    let branch = layer;
    while (branch?.parentElement && branch !== document.body) {
      for (const sibling of branch.parentElement.children) {
        if (sibling === branch || !(sibling instanceof HTMLElement) || sibling.inert || !visible(sibling)) continue;
        inertOwned.set(sibling,false); sibling.inert = true;
      }
      branch = branch.parentElement;
    }
  }
  function focusables(layer) {
    return [...layer.querySelectorAll(controls)].filter(element => visible(element) && !element.disabled && element.tabIndex >= 0 && !element.closest('[inert]'));
  }
  function syncDialogs() {
    if (syncing) return;
    syncing = true;
    const previous = managed;
    restoreInert();
    const native = nativeModal();
    managed = native ? null : customModal();
    if (managed) {
      if (!openers.has(managed)) openers.set(managed,intent && !intent.modal ? {element:intent.element,description:intent.description} : lastOutsideFocus);
      enhanceForms(managed);
      inertSiblings(managed);
      if (!managed.contains(document.activeElement)) focus(focusables(managed)[0] || managed.querySelector('[role="dialog"]') || managed);
    } else if (!native && previous && (!previous.isConnected || !visible(previous))) {
      const opener = openers.get(previous);
      if (document.activeElement === document.body || !document.activeElement?.isConnected) focus(opener?.element?.isConnected ? opener.element : equivalent(opener?.description));
    }
    syncing = false;
  }
  document.addEventListener('keydown', event => {
    if (event.defaultPrevented || nativeModal()) return;
    const layer = customModal();
    if (layer && event.key === 'Escape' && layer.id === 'v16Modal') {
      const cancel = layer.querySelector('[data-v16-cancel]');
      if (cancel) { event.preventDefault(); event.stopImmediatePropagation(); cancel.click(); syncDialogs(); }
      return;
    }
    if (layer && event.key === 'Tab') {
      syncDialogs();
      const items = focusables(layer), first = items[0], last = items.at(-1);
      if (!items.length) { event.preventDefault(); focus(layer.querySelector('[role="dialog"]') || layer); }
      else if (!layer.contains(document.activeElement) || (event.shiftKey && document.activeElement === first)) { event.preventDefault(); focus(event.shiftKey?last:first); }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); focus(first); }
      return;
    }
    if (event.altKey || event.ctrlKey || event.metaKey) return;
    const tab = event.target instanceof Element ? event.target.closest('.v16-tabbar [role="tab"]') : null;
    if (!tab || !['ArrowLeft','ArrowRight','Home','End'].includes(event.key)) return;
    const tabs = [...tab.parentElement.querySelectorAll('[role="tab"]')], current = tabs.indexOf(tab);
    const index = event.key === 'Home'?0:event.key === 'End'?tabs.length-1:(current+(event.key === 'ArrowRight'?1:-1)+tabs.length)%tabs.length;
    event.preventDefault(); tabs[index].click();
  }, true);
  const observer = new MutationObserver(records => {
    const relevant = records.some(record => {
      if (record.type === 'attributes') return record.target.matches?.(watchedSelector);
      if (record.target.closest?.('#v16Modal,#v8CatalogLayer')) return true;
      return [...record.addedNodes,...record.removedNodes].some(node => node instanceof Element && (node.matches(watchedSelector) || node.querySelector(watchedSelector)));
    });
    if (relevant) syncDialogs();
  });
  observer.observe(document.body,{childList:true,subtree:true,attributes:true,attributeFilter:['class','open','aria-hidden']});
  document.addEventListener('close',syncDialogs,true);
  renderedState = pageState();
  window.ToeicInterfaceAccessibility = Object.freeze({beforeRender,afterRender});
})();
