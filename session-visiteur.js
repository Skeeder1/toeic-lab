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
  const PROFILE = 'toeiclab.ui.profile.v1';
  const tones = ['indigo', 'blue', 'teal', 'rose'];
  const sanitizeProfile = value => {
    if (!value || typeof value !== 'object' || value.version !== 1) return null;
    return {version: 1, name: typeof value.name === 'string' ? value.name.trim().slice(0, 40) : '',
      avatar: tones.includes(value.avatar) ? value.avatar : 'indigo',
      photo: typeof value.photo === 'string' && value.photo.length <= 180000 && /^data:image\/(?:png|jpeg|webp);base64,[A-Za-z0-9+/=]+$/.test(value.photo) ? value.photo : ''};
  };
  const loadProfile = () => { try { return sanitizeProfile(JSON.parse(getItem(PROFILE) || 'null')) || {version: 1, name: '', avatar: 'indigo', photo: ''}; } catch (_) { return {version: 1, name: '', avatar: 'indigo', photo: ''}; } };
  let profile = loadProfile();
  let draftProfile;
  let panel, trigger, menu, editor;
  let photoRequest = 0;
  const avatarIcon = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true"><circle cx="12" cy="8" r="3.4"/><path d="M5.5 20v-1.5a6.5 6.5 0 0 1 13 0V20"/></svg>';
  const icons = {
    progress: '<path d="M4 18V6m0 12h16M8 14l4-5 4 3 4-7"/>',
    words: '<path d="M4 4h6a3 3 0 0 1 2 1 3 3 0 0 1 2-1h6v15h-6a3 3 0 0 0-2 1 3 3 0 0 0-2-1H4zM12 5v15"/>',
    edit: '<path d="m5 16-1 4 4-1L20 7l-3-3zM14 7l3 3"/>',
    data: '<path d="M12 3v12m-4-4 4 4 4-4M5 16v5h14v-5"/>'
  };
  const paintAvatar = (element, value) => {
    element.dataset.tone = value.avatar;
    element.replaceChildren();
    if (value.photo) { const img = document.createElement('img'); img.src = value.photo; img.alt = ''; element.append(img); }
    else element.innerHTML = avatarIcon;
  };
  const menuButtons = () => [...menu.querySelectorAll('[role="menuitem"]')];
  const closeMenu = (restore = true) => {
    if (!menu) return;
    menu.hidden = true; trigger.setAttribute('aria-expanded', 'false');
    if (restore && trigger.isConnected) trigger.focus({preventScroll: true});
  };
  const close = () => { if (panel.open) panel.close(); };
  const openPanel = () => {
    closeMenu(false);
    if (editor.open) editor.close();
    update();
    if (!panel.open) panel.showModal();
    panel.querySelector(persistent ? '[data-tv-export]' : '[data-tv-accept]').focus({preventScroll: true});
  };
  const placeTrigger = () => {
    const slot = document.querySelector('[data-tv-profile-slot]') || document.querySelector('.v7-header');
    if (slot && trigger.parentNode !== slot) { slot.append(trigger); closeMenu(false); }
  };
  const announce = () => window.dispatchEvent(new CustomEvent('toeic-visitor-change', {detail: {persistent, mode: persistent ? 'persistent' : 'temporary'}}));
  const update = () => {
    if (!panel) return;
    panel.querySelector('#tvTitle').textContent = persistent ? 'Mes données' : 'Garder ma progression';
    panel.querySelector('[data-tv-intro]').textContent = persistent ? 'Tes séances et tes mots restent disponibles sur ce navigateur.' : 'Retrouve tes séances et tes mots lors de ta prochaine visite.';
    panel.querySelector('[data-tv-status]').textContent = failure || (persistent ? 'Mémorisation activée.' : 'Sans mémorisation, les nouvelles réponses disparaissent en rechargeant ou fermant la page.');
    panel.querySelector('[data-tv-accept]').textContent = 'Mémoriser';
    panel.querySelector('[data-tv-accept]').hidden = persistent;
    panel.querySelector('[data-tv-temporary]').textContent = persistent ? 'Passer en mode temporaire' : 'Plus tard';
    panel.querySelector('[data-tv-backups]').hidden = !persistent;
    menu.querySelector('[data-tv-profile-name]').textContent = profile.name || 'Mon profil';
    menu.querySelector('[data-tv-profile-mode]').textContent = persistent ? 'Progression mémorisée' : 'Mode temporaire';
    paintAvatar(trigger, profile);
    paintAvatar(menu.querySelector('[data-tv-menu-avatar]'), profile);
  };
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
  const openEditor = () => {
    closeMenu(false);
    draftProfile = {...profile};
    editor.querySelector('[data-tv-name]').value = draftProfile.name;
    editor.querySelector('[data-tv-profile-status]').textContent = '';
    editor.querySelector('[data-tv-photo]').value = '';
    editor.querySelector('[data-tv-save-profile]').disabled = false;
    refreshEditor();
    editor.showModal();
  };
  const refreshEditor = () => {
    paintAvatar(editor.querySelector('[data-tv-preview]'), draftProfile);
    editor.querySelector('[data-tv-remove-photo]').hidden = !draftProfile.photo;
    editor.querySelectorAll('[data-tv-avatar]').forEach(button => button.setAttribute('aria-pressed', String(button.dataset.tvAvatar === draftProfile.avatar)));
  };
  const navigate = destination => {
    closeMenu(false);
    // Use the application's existing pause action before leaving an exercise.
    document.querySelector('#v18Pause')?.click();
    window.ToeicNavigation?.go(destination);
    placeTrigger();
    const title = document.querySelector('.v7-main h1');
    if (title) { title.tabIndex = -1; title.focus({preventScroll: true}); }
  };
  const mount = () => {
    trigger = document.createElement('button');
    trigger.type = 'button'; trigger.className = 'tv-settings'; trigger.id = 'tvSettings';
    trigger.setAttribute('aria-label', 'Mon profil');
    trigger.setAttribute('title', 'Mon profil');
    trigger.setAttribute('aria-controls', 'tvProfileMenu');
    trigger.setAttribute('aria-haspopup', 'menu');
    trigger.setAttribute('aria-expanded', 'false');
    menu = document.createElement('section');
    menu.id = 'tvProfileMenu'; menu.className = 'tv-profile-menu'; menu.hidden = true;
    menu.setAttribute('role', 'menu'); menu.setAttribute('aria-label', 'Mon profil');
    menu.innerHTML = '<div class="tv-menu-heading" role="presentation"><span class="tv-avatar" data-tv-menu-avatar></span><div><strong data-tv-profile-name></strong><small data-tv-profile-mode></small></div></div>' +
      [['progress','Ma progression'],['words','Mes mots'],['edit','Modifier mon profil'],['data','Mes données']].map(([action,label]) =>
        '<button type="button" role="menuitem" data-tv-profile-action="' + action + '"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true">' + icons[action] + '</svg><span>' + label + '</span></button>').join('');
    panel = document.createElement('dialog');
    panel.id = 'tvPanel'; panel.className = 'tv-panel'; panel.setAttribute('aria-labelledby', 'tvTitle');
    panel.innerHTML = '<header class="tv-dialog-heading"><h2 id="tvTitle"></h2><button type="button" data-tv-close aria-label="Fermer">×</button></header><div class="tv-copy"><p data-tv-intro></p><p class="tv-status" data-tv-status role="status"></p><div class="tv-backups" data-tv-backups><button type="button" data-tv-export>Exporter ma progression</button><button type="button" data-tv-import>Importer une sauvegarde</button><input type="file" data-tv-import-file accept=".json,application/json" hidden></div><details><summary>Confidentialité et sauvegardes</summary><p>Le profil est local, sans compte connecté ni suivi publicitaire. Les données ne sont pas envoyées au serveur. La mémorisation utilise le stockage de ce navigateur, sans cookie.</p><p>Exporte une sauvegarde JSON pour changer de navigateur ou d’appareil. Le mode temporaire conserve les anciennes données, mais ne garde pas les nouvelles réponses après fermeture ou rechargement.</p></details></div><div class="tv-actions"><button type="button" data-tv-accept></button><button type="button" data-tv-temporary></button></div>';
    editor = document.createElement('dialog');
    editor.id = 'tvProfileEditor'; editor.className = 'tv-panel tv-profile-editor'; editor.setAttribute('aria-labelledby', 'tvProfileTitle');
    editor.innerHTML = '<form><header class="tv-dialog-heading"><h2 id="tvProfileTitle">Mon profil</h2><button type="button" data-tv-close aria-label="Fermer">×</button></header><div class="tv-copy"><div class="tv-profile-photo"><span class="tv-avatar" data-tv-preview></span><div><label class="tv-photo-label">Choisir une photo<input type="file" data-tv-photo accept="image/png,image/jpeg,image/webp" hidden></label><button type="button" data-tv-remove-photo>Retirer la photo</button></div></div><label class="tv-name-label">Prénom ou pseudo<input type="text" data-tv-name maxlength="40" autocomplete="nickname" placeholder="Ton prénom"></label><fieldset><legend>Couleur de l’avatar</legend><div class="tv-avatar-colors">' +
      tones.map((tone,i) => '<button type="button" data-tv-avatar="' + tone + '" data-tone="' + tone + '" aria-label="' + ['Indigo','Bleu','Vert','Rose'][i] + '" aria-pressed="false">' + avatarIcon + '</button>').join('') +
      '</div></fieldset><p class="tv-profile-status" data-tv-profile-status role="status"></p><p class="tv-local-note">Ce profil reste dans ton navigateur.</p></div><div class="tv-actions"><button type="submit" data-tv-save-profile>Enregistrer</button></div></form>';
    document.body.append(trigger, menu, panel, editor);
    placeTrigger();
    new MutationObserver(placeTrigger).observe(document.getElementById('v6App') || document.body, {childList: true, subtree: true});
    trigger.addEventListener('click', () => {
      if (!menu.hidden) { closeMenu(); return; }
      update(); menu.hidden = false; trigger.setAttribute('aria-expanded', 'true');
      const box = trigger.getBoundingClientRect();
      menu.style.top = Math.max(10, Math.min(box.bottom + 10, innerHeight - menu.offsetHeight - 12)) + 'px';
      menuButtons()[0].focus({preventScroll: true});
    });
    trigger.addEventListener('keydown', event => {
      if (event.key === 'ArrowDown' || event.key === 'ArrowUp') { event.preventDefault(); if (menu.hidden) trigger.click(); (event.key === 'ArrowUp' ? menuButtons().at(-1) : menuButtons()[0]).focus(); }
    });
    menu.addEventListener('keydown', event => {
      const buttons = menuButtons(), index = buttons.indexOf(document.activeElement);
      if (event.key === 'Escape') { event.preventDefault(); closeMenu(); }
      else if (['ArrowDown','ArrowUp','Home','End'].includes(event.key)) {
        event.preventDefault();
        const next = event.key === 'Home' ? 0 : event.key === 'End' ? buttons.length - 1 : (index + (event.key === 'ArrowDown' ? 1 : -1) + buttons.length) % buttons.length;
        buttons[next].focus();
      } else if (event.key === 'Tab') closeMenu(false);
    });
    menu.addEventListener('click', event => {
      const action = event.target.closest('[data-tv-profile-action]')?.dataset.tvProfileAction;
      if (action === 'data') openPanel();
      else if (action === 'edit') openEditor();
      else if (action) navigate(action === 'words' ? 'vocab' : 'progress');
    });
    document.addEventListener('pointerdown', event => { if (!menu.hidden && !menu.contains(event.target) && !trigger.contains(event.target)) closeMenu(false); });
    window.addEventListener('resize', () => closeMenu(false));
    for (const dialog of [panel, editor]) {
      dialog.querySelector('[data-tv-close]').addEventListener('click', () => dialog.close());
      dialog.addEventListener('close', () => { if (dialog === editor) photoRequest++; if (trigger.isConnected) trigger.focus({preventScroll: true}); });
      dialog.addEventListener('click', event => {
        if (event.target !== dialog) return;
        const box = dialog.getBoundingClientRect();
        if (event.clientX < box.left || event.clientX > box.right || event.clientY < box.top || event.clientY > box.bottom) dialog.close();
      });
    }
    panel.querySelector('[data-tv-accept]').addEventListener('click', accept);
    panel.querySelector('[data-tv-temporary]').addEventListener('click', decline);
    panel.querySelector('[data-tv-export]').addEventListener('click', () => window.__toeicV18?.exportBackup());
    panel.querySelector('[data-tv-import]').addEventListener('click', () => panel.querySelector('[data-tv-import-file]').click());
    panel.querySelector('[data-tv-import-file]').addEventListener('change', event => window.__toeicV18?.importBackup(event.target.files?.[0]));
    editor.querySelectorAll('[data-tv-avatar]').forEach(button => button.addEventListener('click', () => { draftProfile.avatar = button.dataset.tvAvatar; refreshEditor(); }));
    editor.querySelector('[data-tv-remove-photo]').addEventListener('click', () => { photoRequest++; draftProfile.photo = ''; editor.querySelector('[data-tv-photo]').value = ''; editor.querySelector('[data-tv-save-profile]').disabled = false; refreshEditor(); });
    editor.querySelector('[data-tv-photo]').addEventListener('change', async event => {
      const file = event.target.files?.[0], request = ++photoRequest;
      const status = editor.querySelector('[data-tv-profile-status]');
      status.textContent = '';
      editor.querySelector('[data-tv-save-profile]').disabled = false;
      if (!file) return;
      if (!['image/jpeg','image/png','image/webp'].includes(file.type) || file.size > 10000000) { status.textContent = 'Choisis une image JPG, PNG ou WebP de moins de 10 Mo.'; return; }
      const save = editor.querySelector('[data-tv-save-profile]'); save.disabled = true;
      let bitmap;
      try {
        bitmap = await createImageBitmap(file);
        const canvas = document.createElement('canvas'); canvas.width = canvas.height = 192;
        const ctx = canvas.getContext('2d'), side = Math.min(bitmap.width, bitmap.height);
        ctx.drawImage(bitmap, (bitmap.width-side)/2, (bitmap.height-side)/2, side, side, 0, 0, 192, 192);
        if (request === photoRequest && editor.open) { draftProfile.photo = canvas.toDataURL('image/webp', .8); refreshEditor(); }
      } catch (_) { if (request === photoRequest) status.textContent = 'Cette image ne peut pas être lue. Choisis-en une autre.'; }
      finally { bitmap?.close(); if (request === photoRequest) save.disabled = false; }
    });
    editor.querySelector('form').addEventListener('submit', event => {
      event.preventDefault();
      const value = sanitizeProfile({...draftProfile, name: editor.querySelector('[data-tv-name]').value});
      try {
        setItem(PROFILE, JSON.stringify(value)); profile = value; update(); editor.close();
      } catch (_) { editor.querySelector('[data-tv-profile-status]').textContent = 'Le navigateur ne peut pas enregistrer le profil. Exporte tes données pour les conserver.'; }
    });
    update();
    if (!persistent && tempGet(CHOICE) !== 'temporary') openPanel();
  };
  window.ToeicVisitor = Object.freeze({get mode() {return persistent ? 'persistent' : 'temporary';}, get id() {return persistent ? preference.id : null;}, sanitizeProfile,
    open: () => {if (panel) openPanel();}});
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', mount, {once: true}); else mount();
})();
