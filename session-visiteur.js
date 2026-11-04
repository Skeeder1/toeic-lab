/* Local visitor preferences. Load before every application script. No network calls. */
(() => {
  'use strict';
  const PREF = 'toeiclab.visitor.v1';
  const TEMP = '__toeicVisitor.overlay:';
  const CHOICE = '__toeicVisitor.choice';
  let native;
  try { native = window.localStorage; } catch (_) {
    // Storage access itself can be blocked. Keep the application usable in memory.
    native = {length: 0, key: () => null, getItem: () => null,
      setItem: () => {throw new Error('Storage unavailable');},
      removeItem: () => {throw new Error('Storage unavailable');}};
  }
  const memory = new Map();
  const isLearning = key => String(key).startsWith('toeiclab.') && key !== PREF;
  const readPreference = () => { try { return JSON.parse(native.getItem(PREF) || 'null'); } catch (_) { return null; } };
  let preference = readPreference();
  let persistent = preference?.version === 1 && preference?.mode === 'persistent' && typeof preference?.id === 'string';
  let failure = '';
  // Memory only: Chromium may restore sessionStorage even after browser shutdown.
  const tempGet = key => memory.get(key) ?? null;
  const tempSet = (key, value) => { memory.set(key, value); };
  const tempRemove = key => { memory.delete(key); };
  const nativeKeys = () => Array.from({length: native.length}, (_, i) => native.key(i)).filter(key => key !== null);
  const overlayKeys = () => [...memory.keys()].filter(key => key.startsWith(TEMP)).map(key => key.slice(TEMP.length));
  const overlay = key => { try { return JSON.parse(tempGet(TEMP + key) || 'null'); } catch (_) { return null; } };
  const getItem = key => {
    key = String(key);
    if (!persistent && isLearning(key)) { const row = overlay(key); if (row) return row.value; }
    return native.getItem(key);
  };
  const stage = (key, value) => {
    const previous = overlay(key);
    tempSet(TEMP + key, JSON.stringify({base: previous ? previous.base : native.getItem(key), value}));
  };
  const setItem = (key, value) => {
    key = String(key); value = String(value);
    if (isLearning(key) && !persistent) stage(key, value); else native.setItem(key, value);
  };
  const removeItem = key => {
    key = String(key);
    if (isLearning(key) && !persistent) stage(key, null); else native.removeItem(key);
  };
  const keys = () => [...new Set([...nativeKeys(), ...(!persistent ? overlayKeys() : [])])].filter(key => getItem(key) !== null);
  const methods = {
    getItem, setItem, removeItem,
    key: index => keys()[Number(index) >>> 0] ?? null,
    clear: () => keys().forEach(removeItem)
  };
  const facade = new Proxy(native, {
    get: (target, property) => property === 'length' ? keys().length : Object.prototype.hasOwnProperty.call(methods, property) ? methods[property] : typeof property === 'string' && getItem(property) !== null ? getItem(property) : Reflect.get(target, property, target),
    set: (_, property, value) => { setItem(property, value); return true; },
    deleteProperty: (_, property) => { removeItem(property); return true; },
    ownKeys: () => keys(),
    getOwnPropertyDescriptor: (_, property) => typeof property === 'string' && getItem(property) !== null ? {configurable: true, enumerable: true, writable: true, value: getItem(property)} : undefined,
    defineProperty: (_, property, descriptor) => { if ('value' in descriptor) { setItem(property, descriptor.value); return true; } return false; }
  });
  Object.defineProperty(window, 'localStorage', {configurable: true, get: () => facade});

  const makeId = () => window.crypto.randomUUID ? window.crypto.randomUUID() : Array.from(window.crypto.getRandomValues(new Uint8Array(16)), b => b.toString(16).padStart(2, '0')).join('');
  let panel;
  let trigger;
  const announce = () => window.dispatchEvent(new CustomEvent('toeic-visitor-change', {detail: {persistent, mode: persistent ? 'persistent' : 'temporary'}}));
  const update = () => {
    if (!panel) return;
    panel.querySelector('[data-tv-status]').textContent = failure || (persistent ? 'Mémorisation activée sur ce navigateur.' : 'Mode temporaire : les nouvelles réponses seront perdues en rechargeant ou fermant cette page.');
    panel.querySelector('[data-tv-accept]').textContent = persistent ? 'Garder la mémorisation' : 'Mémoriser sur cet appareil';
    panel.querySelector('[data-tv-temporary]').textContent = persistent ? 'Passer en mode temporaire' : 'Continuer sans mémoriser';
    trigger.textContent = persistent ? 'Mémorisation activée' : 'Mémorisation';
  };
  const close = () => { panel.hidden = true; trigger.focus({preventScroll: true}); };
  const accept = () => {
    failure = '';
    const pending = overlayKeys().map(key => [key, overlay(key)]).filter(([, row]) => row);
    if (pending.some(([key, row]) => native.getItem(key) !== row.base)) {
      failure = 'La progression a changé dans un autre onglet. Exportez votre séance depuis Progression avant de recharger ; vos anciennes données sont conservées.';
      update(); return;
    }
    const before = new Map(pending.map(([key]) => [key, native.getItem(key)]));
    try {
      for (const [key, row] of pending) { if (row.value === null) native.removeItem(key); else native.setItem(key, row.value); }
      preference = {version: 1, mode: 'persistent', id: preference?.id || makeId(), acceptedAt: new Date().toISOString()};
      native.setItem(PREF, JSON.stringify(preference));
      persistent = true;
      pending.forEach(([key]) => tempRemove(TEMP + key));
      tempRemove(CHOICE);
      update(); announce(); close();
    } catch (_) {
      for (const [key, value] of before) { try { if (value === null) native.removeItem(key); else native.setItem(key, value); } catch (_) {} }
      failure = 'Le navigateur refuse la mémorisation. Exportez votre progression en JSON pour la conserver.';
      update();
    }
  };
  // A revocation in another tab must stop future permanent writes here as well.
  window.addEventListener('storage', event => {
    if (event.storageArea !== native || (event.key !== PREF && event.key !== null)) return;
    const current = readPreference();
    if (!current || current.mode !== 'persistent') {
      persistent = false;
      preference = current;
      update(); announce();
    } else if (!persistent) {
      preference = current;
    }
  });
  const decline = () => {
    failure = '';
    if (persistent) {
      try { native.removeItem(PREF); } catch (_) { failure = 'Impossible de modifier ce choix dans le navigateur.'; update(); return; }
      persistent = false;
    }
    tempSet(CHOICE, 'temporary');
    update(); announce(); close();
  };
  const mount = () => {
    trigger = document.createElement('button');
    trigger.type = 'button'; trigger.className = 'tv-settings'; trigger.id = 'tvSettings';
    trigger.setAttribute('aria-controls', 'tvPanel');
    panel = document.createElement('section');
    panel.id = 'tvPanel'; panel.className = 'tv-panel'; panel.setAttribute('role', 'region'); panel.setAttribute('aria-labelledby', 'tvTitle');
    panel.hidden = persistent || tempGet(CHOICE) === 'temporary';
    panel.innerHTML = '<div class="tv-copy"><h2 id="tvTitle">Retrouver votre progression</h2><p>Sans compte, votre progression et votre séance peuvent être gardées sur <strong>cet appareil et ce navigateur</strong>.</p><p>Aucun suivi publicitaire. Vos réponses restent dans votre navigateur et ne sont pas envoyées au serveur. La mémorisation utilise le stockage local, sans cookie.</p><p>Sans mémorisation, les nouvelles réponses seront perdues en rechargeant ou fermant cette page. Vos anciennes sauvegardes restent conservées. Exportez un JSON dans Progression pour changer d’appareil ou sauvegarder une copie.</p><p class="tv-status" data-tv-status role="status"></p></div><div class="tv-actions"><button type="button" data-tv-accept></button><button type="button" data-tv-temporary></button></div>';
    document.body.append(trigger, panel);
    trigger.addEventListener('click', () => { panel.hidden = !panel.hidden; if (!panel.hidden) panel.querySelector('button').focus({preventScroll: true}); });
    panel.querySelector('[data-tv-accept]').addEventListener('click', accept);
    panel.querySelector('[data-tv-temporary]').addEventListener('click', decline);
    panel.addEventListener('keydown', event => { if (event.key === 'Escape') close(); });
    update();
  };
  window.ToeicVisitor = Object.freeze({get mode() {return persistent ? 'persistent' : 'temporary';}, get id() {return persistent ? preference.id : null;}, open: () => {if (panel) {panel.hidden = false; panel.querySelector('button').focus();}}});
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', mount, {once: true}); else mount();
})();
