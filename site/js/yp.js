/* The Green Thumb: the Garden's directory + a password locker that is encrypted ON THIS DEVICE.
   Listings come from the vault (agents keep them current) plus the ones CAK3D adds here.
   Passwords: AES-GCM with a key made from CAK3D's passphrase (PBKDF2-SHA256); the Garden only ever stores scrambled text. */
(function () {
  var $ = function (id) { return document.getElementById(id); };
  var listEl = $('yp-list'), msgEl = $('yp-msg'), q = $('yp-q');
  var entries = [], mine = [], key = null, vault = null, creds = {}, lockTimer = null;
  var HDR = { 'Content-Type': 'application/json', 'X-Double-Wide': '1' };
  var ITER = 600000;

  function esc(t) { var d = document.createElement('div'); d.textContent = t == null ? '' : String(t); return d.innerHTML; }
  function say(t) { msgEl.textContent = t || ''; }
  function b64(buf) { return btoa(String.fromCharCode.apply(null, new Uint8Array(buf))); }
  function unb64(s) { var r = atob(s), o = new Uint8Array(r.length); for (var i = 0; i < r.length; i++) o[i] = r.charCodeAt(i); return o; }
  function host(u) { try { return new URL(/^https?:/.test(u) ? u : 'https://' + u).hostname.replace(/^www\./, ''); } catch (e) { return ''; } }

  // ---------------- crypto (browser only)
  function derive(pass, salt) {
    return crypto.subtle.importKey('raw', new TextEncoder().encode(pass), 'PBKDF2', false, ['deriveKey']).then(function (k) {
      return crypto.subtle.deriveKey({ name: 'PBKDF2', salt: salt, iterations: ITER, hash: 'SHA-256' }, k, { name: 'AES-GCM', length: 256 }, false, ['encrypt', 'decrypt']);
    });
  }
  function seal() {
    var iv = crypto.getRandomValues(new Uint8Array(12));
    return crypto.subtle.encrypt({ name: 'AES-GCM', iv: iv }, key, new TextEncoder().encode(JSON.stringify({ creds: creds }))).then(function (ct) {
      vault = { v: 1, salt: vault.salt, iter: ITER, iv: b64(iv), ct: b64(ct) };
      return fetch('api/yp/vault', { method: 'PUT', headers: HDR, body: JSON.stringify(vault) }).then(function (r) { return r.json(); });
    }).then(function (r) { say(r.ok ? '🔒 Saved (scrambled) to the Garden.' : 'Could not save — try again.'); });
  }
  function touch() { clearTimeout(lockTimer); lockTimer = setTimeout(lock, 10 * 60 * 1000); }
  function lock() { key = null; creds = {}; $('yp-lock').textContent = '🔒 Unlock passwords'; render(); say('Locked.'); }

  // ---------------- small dialog
  function dialog(title, fields, ok) {
    var wrap = document.createElement('div'); wrap.className = 'modal';
    wrap.innerHTML = '<div class="modal-card"><button type="button" class="modal-x" aria-label="Close">×</button><h3>' + esc(title) + '</h3>' +
      fields.map(function (f) {
        return f.type === 'note' ? '<p class="small">' + f.text + '</p>' :
          f.type === 'file' ? '<label class="yp-field">' + esc(f.label) + '<input type="file" name="' + f.name + '" accept=".csv,.txt"></label>' :
          '<label class="yp-field">' + esc(f.label) + (f.type === 'area' ? '<textarea name="' + f.name + '" rows="5"></textarea>' :
          '<input name="' + f.name + '" type="' + (f.type || 'text') + '" value="' + esc(f.value || '') + '" autocomplete="' + (f.ac || 'off') + '">') + '</label>';
      }).join('') + '<div class="jm-actions"><button type="button" class="btn go">Save</button></div><p class="small dmsg"></p></div>';
    document.body.appendChild(wrap);
    var close = function () { wrap.remove(); };
    wrap.querySelector('.modal-x').onclick = close;
    wrap.addEventListener('click', function (e) { if (e.target === wrap) close(); });
    wrap.querySelector('.go').onclick = function () {
      var v = {}; Array.prototype.forEach.call(wrap.querySelectorAll('input,textarea'), function (i) { v[i.name] = i.type === 'file' ? i.files[0] : i.value; });
      var m = wrap.querySelector('.dmsg'); m.textContent = 'Working…';
      Promise.resolve(ok(v)).then(function (res) { if (res === true) close(); else m.textContent = res || ''; }).catch(function (e) { m.textContent = 'Something went wrong: ' + e; });
    };
    var first = wrap.querySelector('input,textarea'); if (first) first.focus();
  }

  function unlock() {
    if (key) { lock(); return; }
    if (!window.crypto || !crypto.subtle) { say('The locker needs the secure app address (open it from the Newsstand app).'); return; }
    var fresh = !vault || !vault.ct;
    dialog(fresh ? 'Make your locker passphrase' : 'Unlock The Green Thumb', fresh ? [
      { type: 'note', text: 'Pick a passphrase only you know (a few words is best). It scrambles your passwords on this device; the Garden never sees it. <b>If you forget it, the saved passwords can\'t be recovered.</b>' },
      { name: 'p1', label: 'Passphrase', type: 'password', ac: 'new-password' }, { name: 'p2', label: 'Type it again', type: 'password', ac: 'new-password' }] :
      [{ name: 'p1', label: 'Passphrase', type: 'password', ac: 'current-password' }], function (v) {
        if (fresh) {
          if ((v.p1 || '').length < 8) return 'Use at least 8 characters.';
          if (v.p1 !== v.p2) return 'The two don\'t match.';
          var salt = crypto.getRandomValues(new Uint8Array(16));
          return derive(v.p1, salt).then(function (k) { key = k; vault = { salt: b64(salt) }; creds = {}; return seal(); })
            .then(function () { opened(); return true; });
        }
        return derive(v.p1, unb64(vault.salt)).then(function (k) {
          return crypto.subtle.decrypt({ name: 'AES-GCM', iv: unb64(vault.iv) }, k, unb64(vault.ct)).then(function (pt) {
            key = k; creds = (JSON.parse(new TextDecoder().decode(pt)) || {}).creds || {}; opened(); return true;
          });
        }).catch(function () { return 'That passphrase didn\'t open it.'; });
      });
  }
  function opened() { $('yp-lock').textContent = '🔓 Lock'; touch(); render(); say('Unlocked for 10 minutes. Tap 👁 to see a password.'); addImport(); }

  function addImport() {
    if ($('yp-import')) return;
    var b = document.createElement('button'); b.type = 'button'; b.className = 'btn ghost'; b.id = 'yp-import'; b.textContent = '⬆ Import passwords';
    b.onclick = function () {
      dialog('Import passwords', [
        { type: 'note', text: 'Pick a password export from your password manager (Google Password Manager / Chrome: a .csv with name, url, username, password). It is read and scrambled right here on this device — the file is never uploaded. Delete the export file afterwards.' },
        { name: 'f', label: 'Export file (.csv)', type: 'file' }], function (v) {
          if (!v.f) return 'Pick a file first.';
          return v.f.text().then(function (txt) {
            var rows = parseCSV(txt), head = rows.shift() || [], col = function (n) { return head.map(function (h) { return h.toLowerCase().trim(); }).indexOf(n); };
            var iN = col('name'), iU = col('url'), iUser = col('username'), iP = col('password'), iNote = col('note');
            if (iP < 0) return 'That file has no "password" column.';
            var added = 0, newOnes = 0;
            rows.forEach(function (r) {
              if (!r[iP]) return;
              var h = host(r[iU] || ''), match = all().filter(function (x) { return h && (host(x.url) === h || x.ip === h); })[0];
              if (!match) {
                match = { id: 'u-' + Math.random().toString(36).slice(2, 10), name: r[iN] || h || 'Saved login', device: 'Online accounts', category: 'Login', url: r[iU] || '' };
                mine.push(match); newOnes++;
              }
              creds[match.id] = { user: r[iUser] || '', pass: r[iP], note: iNote >= 0 ? r[iNote] || '' : '' }; added++;
            });
            return seal().then(function () { return newOnes ? saveMine() : null; }).then(function () { render(); say('Imported ' + added + ' logins (' + newOnes + ' new listings).'); return true; });
          });
        });
    };
    $('yp-add').after(b);
  }
  function parseCSV(t) {
    var rows = [], row = [], cur = '', q = false;
    for (var i = 0; i < t.length; i++) {
      var c = t[i];
      if (q) { if (c === '"' && t[i + 1] === '"') { cur += '"'; i++; } else if (c === '"') q = false; else cur += c; }
      else if (c === '"') q = true; else if (c === ',') { row.push(cur); cur = ''; }
      else if (c === '\n' || c === '\r') { if (c === '\r' && t[i + 1] === '\n') i++; row.push(cur); rows.push(row); row = []; cur = ''; }
      else cur += c;
    }
    if (cur || row.length) { row.push(cur); rows.push(row); }
    return rows.filter(function (r) { return r.length > 1 || r[0]; });
  }

  function saveMine() { return fetch('api/yp/entries', { method: 'POST', headers: HDR, body: JSON.stringify({ entries: mine }) }).then(function (r) { return r.json(); }); }
  function all() { return entries.concat(mine); }

  function editLogin(x) {
    var c = creds[x.id] || {};
    dialog('Login for ' + x.name, [{ name: 'user', label: 'Username', value: c.user, ac: 'username' }, { name: 'pass', label: 'Password', type: 'password', value: c.pass, ac: 'new-password' },
      { name: 'note', label: 'Note (PIN hint, 2FA device…)', value: c.note }], function (v) {
        if (!v.user && !v.pass) delete creds[x.id]; else creds[x.id] = { user: v.user, pass: v.pass, note: v.note };
        touch(); return seal().then(function () { render(); return true; });
      });
  }

  function card(x) {
    var c = creds[x.id], rows = [];
    if (x.url) rows.push('<div class="yp-row"><span>Web</span><a href="' + esc(/^https?:/.test(x.url) ? x.url : 'http://' + x.url) + '" target="_blank" rel="noopener">' + esc(x.url) + '</a></div>');
    if (x.ip) rows.push('<div class="yp-row"><span>IP</span><code>' + esc(x.ip) + '</code></div>');
    if (x.tailscale) rows.push('<div class="yp-row"><span>Tailscale</span><code>' + esc(x.tailscale) + '</code></div>');
    if (x.ssh) rows.push('<div class="yp-row"><span>SSH</span><code>' + esc(x.ssh) + '</code><button type="button" class="yp-mini" data-copy="' + esc(x.ssh) + '">📋</button></div>');
    if (key && c) {
      if (c.user) rows.push('<div class="yp-row"><span>User</span><code>' + esc(c.user) + '</code><button type="button" class="yp-mini" data-copy="' + esc(c.user) + '">📋</button></div>');
      if (c.pass) rows.push('<div class="yp-row pw"><span>Password</span><code class="pw-mask" data-id="' + esc(x.id) + '">••••••••••</code>' +
        '<button type="button" class="yp-mini" data-show="' + esc(x.id) + '">👁 View</button><button type="button" class="yp-mini" data-copypw="' + esc(x.id) + '">📋</button></div>');
      if (c.note) rows.push('<div class="yp-row"><span>Note</span><em>' + esc(c.note) + '</em></div>');
    }
    if (key) rows.push('<div class="yp-row"><span></span><button type="button" class="yp-mini" data-edit="' + esc(x.id) + '">' + (c ? '✏ Edit login' : '＋ Add login') + '</button></div>');
    else if (x.has_login) rows.push('<div class="yp-row"><span>Password</span><code>🔒 ••••••••</code></div>');
    return '<div class="yp-card"><div class="yp-name"><b>' + esc(x.name) + '</b>' + (x.category ? '<span class="tag">' + esc(x.category) + '</span>' : '') + '</div>' +
      (x.notes ? '<div class="small">' + esc(x.notes) + '</div>' : '') + rows.join('') + '</div>';
  }

  function render() {
    var term = (q.value || '').toLowerCase(), groups = {};
    all().forEach(function (x) {
      var hay = [x.name, x.device, x.category, x.url, x.ip, x.ssh, x.tailscale, x.notes].join(' ').toLowerCase();
      if (term && hay.indexOf(term) < 0) return;
      (groups[x.device || 'Other'] = groups[x.device || 'Other'] || []).push(x);
    });
    var names = Object.keys(groups);
    listEl.innerHTML = names.map(function (g) {
      return '<section class="yp-sec"><h2 class="yp-letter">' + esc(g) + '</h2><div class="yp-grid">' + groups[g].map(card).join('') + '</div></section>';
    }).join('') || '<p class="small">Nothing matches.</p>';
  }

  listEl.addEventListener('click', function (e) {
    var t = e.target; if (!t.closest) return; touch();
    var s = t.closest('[data-show]'), cp = t.closest('[data-copy]'), cpw = t.closest('[data-copypw]'), ed = t.closest('[data-edit]');
    if (s) { var el = listEl.querySelector('.pw-mask[data-id="' + s.dataset.show + '"]'), c = creds[s.dataset.show] || {};
      var shown = el.dataset.shown === '1'; el.textContent = shown ? '••••••••••' : c.pass; el.dataset.shown = shown ? '' : '1'; s.textContent = shown ? '👁 View' : '🙈 Hide'; }
    if (cp) navigator.clipboard.writeText(cp.dataset.copy).then(function () { say('Copied.'); });
    if (cpw) navigator.clipboard.writeText((creds[cpw.dataset.copypw] || {}).pass || '').then(function () { say('Password copied — paste it where you need it.'); });
    if (ed) editLogin(all().filter(function (x) { return x.id === ed.dataset.edit; })[0]);
  });
  q.addEventListener('input', render);
  $('yp-lock').onclick = unlock;
  $('yp-add').onclick = function () {
    dialog('Add a listing', [{ name: 'name', label: 'Name (app, site, project…)' }, { name: 'device', label: 'Device it lives on (or "Online")' },
      { name: 'category', label: 'Kind (app, website, service, project…)' }, { name: 'url', label: 'URL' }, { name: 'ip', label: 'IP / port' },
      { name: 'ssh', label: 'SSH command' }, { name: 'tailscale', label: 'Tailscale name' }, { name: 'notes', label: 'Notes' }], function (v) {
        if (!v.name) return 'Give it a name.';
        v.id = 'u-' + Math.random().toString(36).slice(2, 10); mine.push(v);
        return saveMine().then(function (r) { render(); return r.ok ? true : 'Could not save.'; });
      });
  };

  Promise.all([
    fetch('data/green-thumb.json', { cache: 'no-store' }).then(function (r) { return r.json(); }).catch(function () { return { entries: [] }; }),
    fetch('api/yp/entries', { cache: 'no-store' }).then(function (r) { return r.json(); }).catch(function () { return { entries: [] }; }),
    fetch('api/yp/vault', { cache: 'no-store' }).then(function (r) { return r.json(); }).catch(function () { return {}; })
  ]).then(function (res) {
    entries = res[0].entries || []; mine = res[1].entries || []; vault = res[2] && res[2].ct ? res[2] : null;
    render(); say(vault ? 'Passwords are locked. Tap 🔒 Unlock to see them.' : 'No passwords saved yet — tap 🔒 Unlock to set up your locker.');
  });
})();
