/* ============================================================
   Arena pertarungan p=23.
   JavaScript hanya memanggil API dan merender. Seluruh kripto,
   pemetaan damage, dan perubahan HP dihitung di server Python.
   ============================================================ */

(function () {
  'use strict';

  const $ = function (selector, root) {
    return (root || document).querySelector(selector);
  };

  const state = {
    arena: null,
    textbook: null,
    busy: false,
    toastTimer: null
  };

  function esc(value) {
    return String(value)
      .replaceAll('&', '&amp;')
      .replaceAll('<', '&lt;')
      .replaceAll('>', '&gt;')
      .replaceAll('"', '&quot;')
      .replaceAll("'", '&#039;');
  }

  function setText(id, value) {
    const node = document.getElementById(id);
    if (node) node.textContent = value === null || value === undefined ? '—' : String(value);
  }

  function toast(message, kind) {
    const node = $('#toast');
    if (!node) return;
    node.textContent = message;
    node.classList.remove('is-error', 'is-success');
    if (kind === 'error') node.classList.add('is-error');
    else if (kind === 'success') node.classList.add('is-success');
    node.classList.add('is-visible');
    clearTimeout(state.toastTimer);
    state.toastTimer = setTimeout(function () {
      node.classList.remove('is-visible');
    }, 4200);
  }

  function sleep(ms) {
    return new Promise(function (resolve) {
      window.setTimeout(resolve, ms);
    });
  }

  async function api(path, options) {
    const opts = options || {};
    const init = {
      method: opts.method || 'GET',
      headers: { 'Accept': 'application/json', 'Content-Type': 'application/json' }
    };
    if (opts.body !== undefined) init.body = JSON.stringify(opts.body);
    const response = await fetch(path, init);
    let payload = null;
    try {
      payload = await response.json();
    } catch (_error) {
      throw new Error('Respons server tidak valid.');
    }
    if (!response.ok || payload.ok === false) {
      const error = new Error(payload.error || 'Permintaan gagal.');
      error.payload = payload;
      throw error;
    }
    return payload;
  }

  function clamp(value, min, max) {
    return Math.max(min, Math.min(max, value));
  }

  /* ── render arena ───────────────────────────────────────────── */

  function renderArena(arena) {
    if (!arena) return;
    state.arena = arena;
    renderGame(arena.game);
    renderLast(arena.last_encryption, arena.last_transaction);
    renderPipeline(arena.last_encryption, arena.last_transaction);
    renderLog(arena.logs || []);
    renderValidation(arena.validation || {});
    renderDemo(arena.keys || {});
    setText('arenaMessage', arena.game.message);
  }

  function setButtonsDisabled(disabled) {
    document.querySelectorAll('[data-arena-action]').forEach(function (button) {
      button.disabled = disabled;
    });
    const claim = $('#arenaClaim');
    if (claim) claim.disabled = disabled;
    const reset = $('#arenaReset');
    if (reset) reset.disabled = disabled;
  }

  function renderGame(game) {
    if (!game) return;
    const playerPct = clamp((game.player_hp / game.player_max_hp) * 100, 0, 100);
    const monsterPct = clamp((game.monster_hp / game.monster_max_hp) * 100, 0, 100);

    const playerBar = $('#arenaPlayerHpBar');
    const monsterBar = $('#arenaMonsterHpBar');
    if (playerBar) playerBar.style.width = playerPct + '%';
    if (monsterBar) monsterBar.style.width = monsterPct + '%';

    setText('arenaPlayerHpText', game.player_hp + ' / ' + game.player_max_hp);
    setText('arenaMonsterHpText', game.monster_hp + ' / ' + game.monster_max_hp);
    setText('arenaPlayerNote', game.player_hp >= game.player_max_hp ? 'HP penuh' : 'Terkena serangan balik');
    setText(
      'arenaMonsterNote',
      game.status === 'victory'
        ? 'Monster dikalahkan'
        : game.monster_hp < game.monster_max_hp
          ? 'Menerima damage'
          : 'Menunggu aksi'
    );
    setText('arenaMonsterTag', game.status === 'victory' ? 'K.O.' : game.monster_hp < game.monster_max_hp ? 'hurt' : 'alive');
    setText('arenaStatus', game.status === 'active' ? 'aktif' : game.status === 'victory' ? 'menang' : 'kalah');

    const status = $('#arenaStatus');
    if (status) status.classList.toggle('is-over', game.status !== 'active');
    const monsterCard = $('#arenaMonsterCard');
    if (monsterCard) monsterCard.classList.toggle('is-defeated', game.status === 'victory');
    const playerCard = $('#arenaPlayerCard');
    if (playerCard) playerCard.classList.toggle('is-defeated', game.status === 'defeat');

    renderHistory(game.history || []);
    setButtonsDisabled(state.busy || game.status !== 'active');
  }

  function renderHistory(history) {
    const body = $('#arenaHistoryBody');
    if (!body) return;
    const rows = history || [];
    setText('arenaHistoryCount', rows.length + ' aksi');
    if (!rows.length) {
      body.innerHTML = '<tr><td colspan="5">Belum ada aksi.</td></tr>';
      return;
    }
    body.innerHTML = rows
      .slice()
      .reverse()
      .map(function (item) {
        return '<tr>' +
          '<td>' + esc(item.turn) + '</td>' +
          '<td>' + esc(item.action_name) + '</td>' +
          '<td>' + esc(item.damage_dealt) + '</td>' +
          '<td>' + esc(item.monster_hp_after) + '</td>' +
          '<td>' + esc(item.player_hp_after) + '</td>' +
          '</tr>';
      })
      .join('');
  }

  function setStep(index, status, label) {
    const node = document.getElementById('arenaStep' + index);
    if (!node) return;
    node.classList.remove('is-done', 'is-active', 'is-error');
    if (status) node.classList.add('is-' + status);
    const small = node.querySelector('small');
    if (small && label !== undefined) small.textContent = label;
  }

  function renderPipeline(encryption, transaction) {
    if (transaction) {
      if (transaction.status === 'rejected') {
        setStep(1, 'done', transaction.claimed_action || 'dikirim');
        setStep(2, 'done', transaction.ciphertext ? 'C=(' + transaction.ciphertext.c1 + ',' + transaction.ciphertext.c2 + ')' : '—');
        setStep(3, 'done', 'diterima');
        setStep(4, 'error', 'ditolak');
        setStep(5, 'error', 'tidak berubah');
        return;
      }
      const result = transaction.result || {};
      setStep(1, 'done', transaction.original_action ? transaction.original_action.name : transaction.decrypted_action.name);
      setStep(2, 'done', 'C=(' + transaction.ciphertext.c1 + ',' + transaction.ciphertext.c2 + ')');
      setStep(3, 'done', 'terkirim');
      setStep(4, 'done', 'm′=' + transaction.decrypted_code);
      setStep(5, 'done', (result.monster_hp_before || 0) + ' → ' + (result.monster_hp_after || 0));
      return;
    }
    if (encryption) {
      setStep(1, 'done', encryption.plaintext ? encryption.plaintext.name : '—');
      setStep(2, 'done', 'C=(' + encryption.ciphertext.c1 + ',' + encryption.ciphertext.c2 + ')');
      setStep(3, 'active', 'mengirim…');
      setStep(4, null, '—');
      setStep(5, null, '—');
      return;
    }
    [1, 2, 3, 4, 5].forEach(function (index) {
      setStep(index, null, '—');
    });
  }

  function renderLast(encryption, transaction) {
    if (!encryption) {
      setText('arenaLastPlain', '—');
      setText('arenaLastK', '—');
      setText('arenaLastC1', '—');
      setText('arenaLastC2', '—');
      setText('arenaLastShared', '—');
      setText('arenaLastDecrypted', '—');
      setText('arenaLastCipher', 'C = (—, —)');
      setText('arenaLastMode', '—');
      const chip = $('#arenaLastMatch');
      if (chip) {
        chip.textContent = 'belum ada';
        chip.className = '';
      }
      return;
    }

    const enc = encryption.encryption || {};
    const plain = encryption.plaintext || {};
    setText('arenaLastPlain', (plain.name || '—') + ' (m=' + (plain.code === undefined ? '—' : plain.code) + ')');
    setText('arenaLastK', enc.k);
    setText('arenaLastC1', enc.c1);
    setText('arenaLastC2', enc.c2);
    setText('arenaLastShared', enc.yk);
    setText('arenaLastCipher', 'C = (' + encryption.ciphertext.c1 + ', ' + encryption.ciphertext.c2 + ')');
    setText('arenaLastMode', encryption.mode === 'deterministic' ? 'k deterministik' : 'k acak');

    const chip = $('#arenaLastMatch');
    if (transaction && transaction.status === 'accepted' &&
        transaction.ciphertext.c1 === encryption.ciphertext.c1 &&
        transaction.ciphertext.c2 === encryption.ciphertext.c2) {
      setText('arenaLastDecrypted', transaction.decrypted_code + ' · ' + transaction.decrypted_action.name);
      if (chip) {
        chip.textContent = transaction.message_match ? 'cocok' : 'tidak cocok';
        chip.className = transaction.message_match ? 'is-ok' : 'is-bad';
      }
    } else if (transaction && transaction.status === 'rejected') {
      setText('arenaLastDecrypted', 'ditolak');
      if (chip) {
        chip.textContent = 'ditolak';
        chip.className = 'is-bad';
      }
    } else {
      setText('arenaLastDecrypted', 'menunggu server');
      if (chip) {
        chip.textContent = 'siap dikirim';
        chip.className = '';
      }
    }
  }

  function setCheck(rowIndex, ok, text) {
    const list = $('#arenaChkDh');
    const rows = document.querySelectorAll('.arena-checks li');
    const row = rows[rowIndex];
    if (row) {
      row.classList.remove('is-ok', 'is-bad');
      if (ok === true) row.classList.add('is-ok');
      else if (ok === false) row.classList.add('is-bad');
      const icon = row.querySelector('.arena-check-icon');
      if (icon) icon.textContent = ok === true ? '✓' : ok === false ? '!' : '—';
      const value = row.querySelector('b');
      if (value) {
        value.textContent = text;
        value.classList.remove('is-ok', 'is-bad');
        if (ok === true) value.classList.add('is-ok');
        else if (ok === false) value.classList.add('is-bad');
      }
    }
    return list;
  }

  function renderValidation(validation) {
    setCheck(0, validation.dh_verified, validation.dh_verified ? 'OK · K=' + validation.dh_shared : 'GAGAL');
    const encryptionState = validation.encryption_ok
      ? true
      : validation.last_error
        ? false
        : null;
    const decryptionState = validation.decryption_ok
      ? true
      : validation.last_error
        ? false
        : null;
    setCheck(1, encryptionState, encryptionState === true ? 'OK' : encryptionState === false ? 'GAGAL' : '—');
    setCheck(2, decryptionState, decryptionState === true ? 'OK' : decryptionState === false ? 'DITOLAK' : '—');
    setCheck(
      3,
      validation.message_match === true ? true : validation.message_match === false ? false : null,
      validation.message_match === true ? 'OK' : validation.message_match === false ? 'TIDAK COCOK' : '—'
    );

    const note = $('#arenaValidNote');
    if (note) {
      if (validation.last_error) {
        note.textContent = 'Penolakan terakhir: ' + validation.last_error;
        note.classList.add('has-error');
      } else {
        note.textContent = 'Tidak ada penolakan pada sesi ini. Server memakai damage dari mapping aksi.';
        note.classList.remove('has-error');
      }
    }
    const status = $('#arenaValidStatus');
    if (status) {
      status.textContent = validation.last_error ? 'ada penolakan' : 'live';
    }
  }

  function renderLog(logs) {
    const list = $('#arenaLog');
    if (!list) return;
    const items = logs || [];
    setText('arenaLogCount', items.length + ' event');
    if (!items.length) {
      list.innerHTML = '<li class="arena-log-empty">Belum ada event. Jalankan aksi di arena.</li>';
      return;
    }
    list.innerHTML = items
      .slice()
      .reverse()
      .map(function (entry) {
        const tone = ['ok', 'warn', 'bad'].indexOf(entry.tone) >= 0 ? ' is-' + entry.tone : '';
        return '<li class="' + tone.trim() + '">' +
          '<span class="arena-log-time">' + esc(entry.time) + '</span>' +
          '<span class="arena-log-actor">' + esc(entry.actor) + '</span>' +
          '<span class="arena-log-tag">' + esc(entry.tag) + '</span>' +
          '<span class="arena-log-msg">' + esc(entry.message) + '</span>' +
          '</li>';
      })
      .join('');
  }

  /* ── textbook p=23 ─────────────────────────────────────────── */

  function fillSteps(container, steps) {
    if (!container) return;
    container.innerHTML = '';
    (steps || []).forEach(function (step) {
      const li = document.createElement('li');
      const index = document.createElement('span');
      index.className = 'arena-step-index';
      index.textContent = step.index;
      const main = document.createElement('div');
      main.className = 'arena-step-main';
      const title = document.createElement('b');
      title.className = 'arena-step-title';
      title.textContent = step.title;
      const formula = document.createElement('code');
      formula.className = 'arena-step-formula';
      formula.textContent = step.formula + ' · ' + step.substitution;
      const result = document.createElement('span');
      result.className = 'arena-step-result';
      result.textContent = step.result;
      main.appendChild(title);
      main.appendChild(formula);
      main.appendChild(result);
      li.appendChild(index);
      li.appendChild(main);
      container.appendChild(li);
    });
  }

  function traceText(trace) {
    if (!trace || !Array.isArray(trace.steps)) return '';
    const rows = trace.steps.map(function (step) {
      return 'i' + step.bit_index + ':bit' + step.bit + ' f=' + step.factor +
        ' ' + step.result_before + '→' + step.result_after + (step.multiplied ? ' ×' : '');
    });
    return trace.base + '^' + trace.exponent + ' mod ' + trace.modulus + ' = ' + trace.result +
      ' · biner ' + trace.binary + ' · ' + rows.join(' | ');
  }

  function renderTraces(container, traces, title) {
    if (!container) return null;
    container.innerHTML = '';
    const details = document.createElement('details');
    details.className = 'arena-trace-box';
    const summary = document.createElement('summary');
    summary.textContent = title || 'Jejak square-and-multiply';
    details.appendChild(summary);
    Object.keys(traces || {}).forEach(function (key) {
      const trace = traces[key];
      const div = document.createElement('div');
      div.className = 'arena-trace';
      const label = document.createElement('b');
      label.textContent = key + ': ';
      const code = document.createElement('code');
      code.textContent = traceText(trace);
      div.appendChild(label);
      div.appendChild(code);
      details.appendChild(div);
    });
    container.appendChild(details);
    return details;
  }

  function renderDemo(keys) {
    if (keys.public) {
      setText('arenaDemoY', keys.public.y);
      setText('arenaDemoX', keys.private_demo ? keys.private_demo.x : '—');
    }
    if (!state.textbook) return;
    const demo = state.textbook;
    const dh = demo.dh || {};
    const eg = demo.elgamal || {};
    setText('arenaDemoK', dh.K_A);
    setText('arenaDemoY', eg.y);
    setText('arenaDemoX', eg.x);
    setText('arenaDemoVerified', dh.verified ? 'ya' : 'tidak');
    const status = $('#arenaDemoStatus');
    if (status) {
      const ok = dh.verified && eg.verified;
      status.textContent = ok ? 'terverifikasi' : 'gagal';
      status.classList.toggle('is-bad', !ok);
    }
    fillSteps($('#textbookDhSteps'), dh.steps || []);
    fillSteps($('#textbookEgSteps'), eg.steps || []);
    renderTraces($('#textbookDhTrace'), dh.traces || {}, 'Jejak square-and-multiply DH (4 perhitungan)');
    const egTraceBox = renderTraces(
      $('#textbookEgTrace'),
      eg.traces || {},
      'Jejak square-and-multiply ElGamal (3 perhitungan)'
    );

    const inv = eg.inverse_trace;
    if (inv && inv.steps && egTraceBox) {
      const details = document.createElement('details');
      details.className = 'arena-trace-box';
      const summary = document.createElement('summary');
      summary.textContent = 'Invers modular s⁻¹ (extended Euclidean)';
      const div = document.createElement('div');
      div.className = 'arena-trace';
      const code = document.createElement('code');
      code.textContent = inv.steps.map(function (step) {
        return step.dividend + ' = ' + step.quotient + '×' + step.divisor + ' + ' + step.remainder;
      }).join('; ') + ' → s⁻¹ = ' + inv.inverse + '; cek ' + inv.check_expression;
      div.appendChild(code);
      details.appendChild(summary);
      details.appendChild(div);
      const egTraceContainer = $('#textbookEgTrace');
      if (egTraceContainer) egTraceContainer.appendChild(details);
    }
  }

  /* ── actions ───────────────────────────────────────────────── */

  async function load() {
    try {
      const results = await Promise.all([api('/api/arena/state'), api('/api/textbook')]);
      state.textbook = results[1].textbook;
      renderArena(results[0].arena);
    } catch (error) {
      setText('arenaMessage', 'Arena belum dapat dimuat: ' + error.message);
      const message = $('#arenaMessage');
      if (message) message.classList.add('is-error');
      toast('Gagal memuat arena: ' + error.message, 'error');
    }
  }

  async function refreshArena() {
    const result = await api('/api/arena/state');
    renderArena(result.arena);
  }

  async function runAction(actionId, claimedDamage) {
    if (state.busy || !state.arena || state.arena.game.status !== 'active') return;
    state.busy = true;
    setButtonsDisabled(true);
    const message = $('#arenaMessage');
    if (message) {
      message.classList.remove('is-error');
      message.textContent = 'Menyiapkan aksi di sisi client…';
    }
    try {
      const mode = $('#arenaMode') && $('#arenaMode').checked ? 'deterministic' : 'random';
      const encrypted = await api('/api/arena/encrypt', {
        method: 'POST',
        body: { action: actionId, mode: mode }
      });
      renderArena(encrypted.arena);
      if (message) {
        message.textContent = 'Ciphertext C=(' + encrypted.encryption.ciphertext.c1 + ', ' +
          encrypted.encryption.ciphertext.c2 + ') dikirim ke server…';
      }
      await sleep(240);

      const body = { ciphertext: encrypted.encryption.ciphertext, action: actionId };
      if (claimedDamage !== undefined && claimedDamage !== null) body.damage = claimedDamage;
      const submitted = await api('/api/arena/submit', { method: 'POST', body: body });
      renderArena(submitted.arena);
      const result = submitted.transaction.result;
      if (result.victory) toast('Monster dikalahkan. HP mencapai 0.', 'success');
      else if (result.defeat) toast('Pemain kalah. Reset arena untuk mencoba lagi.', 'error');
      else if (claimedDamage !== undefined) toast('Klaim damage ' + claimedDamage + ' diabaikan; server memakai ' + result.damage_dealt + '.', 'success');
      else toast('Aksi diterima server. HP monster: ' + result.monster_hp_after + '/100.', 'success');
    } catch (error) {
      if (message) {
        message.textContent = error.message;
        message.classList.add('is-error');
      }
      toast(error.message, 'error');
      if (error.payload && error.payload.arena) {
        renderArena(error.payload.arena);
      } else {
        try { await refreshArena(); } catch (_ignored) { /* biarkan pesan */ }
      }
    } finally {
      state.busy = false;
      if (state.arena) setButtonsDisabled(state.arena.game.status !== 'active');
    }
  }

  async function resetArena() {
    if (state.busy) return;
    state.busy = true;
    setButtonsDisabled(true);
    try {
      const result = await api('/api/arena/reset', { method: 'POST', body: {} });
      renderArena(result.arena);
      const message = $('#arenaMessage');
      if (message) {
        message.classList.remove('is-error');
        message.textContent = 'Arena direset. Kunci ElGamal server tetap p=23, g=5, y=8.';
      }
      toast('Arena direset.', 'success');
    } catch (error) {
      toast(error.message, 'error');
    } finally {
      state.busy = false;
      if (state.arena) setButtonsDisabled(state.arena.game.status !== 'active');
    }
  }

  async function tamper() {
    if (state.busy || !state.arena) return;
    state.busy = true;
    setButtonsDisabled(true);
    try {
      const last = state.arena.last_encryption;
      const c2 = last ? last.ciphertext.c2 : 3;
      await api('/api/arena/submit', {
        method: 'POST',
        body: { ciphertext: { c1: 0, c2: c2 }, damage: 999 }
      });
      toast('Server menerima ciphertext rusak (tidak diharapkan).', 'error');
    } catch (error) {
      toast('Ciphertext rusak ditolak: ' + error.message, 'error');
      if (error.payload && error.payload.arena) renderArena(error.payload.arena);
    } finally {
      state.busy = false;
      if (state.arena) setButtonsDisabled(state.arena.game.status !== 'active');
    }
  }

  function wire() {
    document.querySelectorAll('[data-arena-action]').forEach(function (button) {
      button.addEventListener('click', function () {
        runAction(button.dataset.arenaAction);
      });
    });
    const reset = $('#arenaReset');
    if (reset) reset.addEventListener('click', resetArena);
    const claim = $('#arenaClaim');
    if (claim) claim.addEventListener('click', function () { runAction('attack', 999); });
    const tamperButton = $('#arenaTamper');
    if (tamperButton) tamperButton.addEventListener('click', tamper);
    const mode = $('#arenaMode');
    if (mode) {
      mode.addEventListener('change', function () {
        toast(mode.checked ? 'Mode deterministik k=3 aktif.' : 'Mode acak aktif: k dipilih server.', 'success');
      });
    }

    // Sorot navigasi sesuai bagian yang terlihat.
    if ('IntersectionObserver' in window) {
      const sections = ['game-arena', 'simulator', 'tahapan', 'protokol', 'keamanan']
        .map(function (id) { return document.getElementById(id); })
        .filter(Boolean);
      const links = Array.from(document.querySelectorAll('.nav-link'));
      const observer = new IntersectionObserver(function (entries) {
        entries.forEach(function (entry) {
          if (!entry.isIntersecting) return;
          links.forEach(function (link) {
            link.classList.toggle('is-active', link.getAttribute('href') === '#' + entry.target.id);
          });
        });
      }, { rootMargin: '-20% 0px -65% 0px', threshold: 0.01 });
      sections.forEach(function (section) { observer.observe(section); });
    }
  }

  function init() {
    wire();
    load();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();