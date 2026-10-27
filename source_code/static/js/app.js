/* ============================================================
   Secure Multiplayer Game Simulator — frontend controller.
   Semua perhitungan kripto dilakukan oleh server Python.
   JavaScript hanya memanggil API dan merender hasil.
   ============================================================ */

(function () {
  'use strict';

  const $ = function (selector, root) {
    return (root || document).querySelector(selector);
  };

  const MAX_SCORE = 1000000;

  const STAGE_DEFS = [
    {
      number: 0,
      title: 'Parameter publik',
      desc: 'Server membangkitkan safe prime p = 2q + 1 dan generator g. Semua nilai ini boleh diketahui siapa pun.',
      formula: 'p = 2q + 1 (p, q prima) ; g generator grup modulo p'
    },
    {
      number: 1,
      title: 'Kunci ElGamal server',
      desc: 'Server memilih kunci privat x, lalu mempublikasikan kunci publik y = g^x mod p.',
      formula: 'x ∈ [2, p-2] ; y = g^x mod p'
    },
    {
      number: 2,
      title: 'Diffie-Hellman',
      desc: 'Pemain dan server bertukar A dan B, lalu masing-masing menghitung kunci sesi K yang sama tanpa pernah mengirim K.',
      formula: 'A = g^a mod p ; B = g^b mod p ; K = B^a = A^b mod p',
      wide: true
    },
    {
      number: 3,
      title: 'Penyamaran pesan',
      desc: 'Pesan asli m diikat ke kunci sesi K sebelum masuk ke ElGamal: m′ = (m + K) mod p.',
      formula: 'm′ = (m + K) mod p'
    },
    {
      number: 4,
      title: 'Enkripsi ElGamal',
      desc: 'Pemain memilih nonce k, menghitung c1 dan c2 dengan kunci publik server, lalu mengirim ciphertext.',
      formula: 'c1 = g^k mod p ; c2 = m′ · y^k mod p'
    },
    {
      number: 5,
      title: 'Dekripsi server',
      desc: 'Server memakai x untuk membuka ElGamal, lalu K untuk melepas topeng dan memperoleh aksi atau skor asli.',
      formula: 's = c1^x mod p ; m′ = c2 · s^-1 mod p ; m = (m′ - K) mod p'
    },
    {
      number: 6,
      title: 'Panel penyadap',
      desc: 'Eve memeriksa semua data yang bisa ia lihat di jaringan dan menyadari nilai rahasia apa saja yang tertutup baginya.',
      formula: 'Eve tahu: p, q, g, y, A, B, c1, c2'
    },
    {
      number: 7,
      title: 'Serangan cheater',
      desc: 'Eve mengubah c2 di tengah jalan. Server mendekripsi nilai yang berubah dan menandainya sebagai aktivitas mencurigakan.',
      formula: 'c2′ = (c2 + Δ) mod p',
      wide: true
    }
  ];

  const ACTIONS = [
    { index: 0, stage: 0, endpoint: '/api/setup', label: 'Tahap 0 — parameter publik', body: function () { return { mode: state.mode }; } },
    { index: 1, stage: 1, endpoint: '/api/elgamal/key', label: 'Tahap 1 — kunci ElGamal server' },
    { index: 2, stage: 2, endpoint: '/api/dh/start', label: 'Tahap 2a — pemain mengirim A' },
    { index: 3, stage: 2, endpoint: '/api/dh/finish', label: 'Tahap 2b–2d — server mengirim B dan verifikasi K' },
    { index: 4, stage: 3, endpoint: '/api/send', label: 'Tahap 3 — penyamaran pesan', body: buildMessagePayload },
    { index: 5, stage: 4, endpoint: '/api/encrypt', label: 'Tahap 4 — enkripsi ElGamal' },
    { index: 6, stage: 5, endpoint: '/api/decrypt', label: 'Tahap 5 — dekripsi server' },
    { index: 7, stage: 6, endpoint: '/api/eve', label: 'Tahap 6 — panel penyadap', method: 'GET' },
    { index: 8, stage: 7, endpoint: '/api/tamper', label: 'Tahap 7 — serangan cheater' }
  ];

  const state = {
    view: emptyView(),
    mode: 'demo',
    dataType: 'action',
    stageData: {},
    busy: false,
    note: null,
    toastTimer: null
  };

  const el = {};

  function emptyView() {
    return {
      has_session: false,
      mode: null,
      mode_label: null,
      bits: 0,
      step: -1,
      params: null,
      dh: {},
      elgamal: {},
      message: {},
      cipher: {},
      decryption: {},
      tamper: null,
      packets: [],
      logs: [],
      roles: {
        player: { public: [], secret: [], sent: [] },
        server: { public: [], secret: [], received: [] },
        eve: { visible: [], hidden: [] }
      }
    };
  }

  /* ── util ──────────────────────────────────────────────── */

  function make(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined && text !== null) node.textContent = String(text);
    return node;
  }

  function shortNumber(value, head, tail) {
    const text = String(value);
    if (text.length <= 30) return text;
    return text.slice(0, head || 10) + '…' + text.slice(-(tail || 6));
  }

  function decimalLessThan(a, b) {
    let x = String(a).replace(/^0+(?=\d)/, '');
    const y = String(b).replace(/^0+(?=\d)/, '');
    if (x.length !== y.length) return x.length < y.length;
    return x < y;
  }

  function completedCount() {
    let total = 0;
    for (let i = 0; i < 8; i++) {
      if (stageIsComplete(i)) total += 1;
    }
    return total;
  }

  function stageIsComplete(number) {
    const step = state.view.step;
    if (number === 2) return step >= 3;
    const threshold = { 0: 0, 1: 1, 3: 4, 4: 5, 5: 6, 6: 7, 7: 8 };
    return step >= threshold[number];
  }

  function nextAction() {
    const index = state.view.step + 1;
    return index >= 0 && index < ACTIONS.length ? ACTIONS[index] : null;
  }

  function sleep(ms) {
    return new Promise(function (resolve) { window.setTimeout(resolve, ms); });
  }

  function toast(message, kind) {
    if (!el.toast) return;
    el.toast.textContent = message;
    el.toast.className = 'toast is-visible' + (kind ? ' is-' + kind : '');
    window.clearTimeout(state.toastTimer);
    state.toastTimer = window.setTimeout(function () {
      el.toast.className = 'toast';
    }, 4200);
  }

  function setNote(kind, message) {
    state.note = { kind: kind || '', message: message };
    if (!el.controlNote) return;
    el.controlNote.className = 'control-note' + (kind ? ' is-' + kind : '');
    el.controlNoteText.textContent = message;
  }

  /* ── API ───────────────────────────────────────────────── */

  async function api(path, options) {
    const opts = options || {};
    const init = {
      method: opts.method || 'POST',
      headers: { 'Accept': 'application/json' }
    };
    if (init.method !== 'GET' && opts.body !== undefined) {
      init.headers['Content-Type'] = 'application/json';
      init.body = JSON.stringify(opts.body || {});
    }

    const response = await fetch(path, init);
    let data;
    try {
      data = await response.json();
    } catch (err) {
      throw new Error('Respons server bukan JSON yang valid.');
    }

    if (data && data.view) {
      state.view = data.view;
      if (data.view.mode) state.mode = data.view.mode;
      renderAll();
    }
    if (!response.ok || !data.ok) {
      throw new Error((data && data.error) || 'Permintaan ke server gagal.');
    }
    return data;
  }

  /* ── payload input pemain ──────────────────────────────── */

  function buildMessagePayload() {
    if (state.dataType === 'action') {
      const action = Number(el.actionValue.value);
      if (!Number.isInteger(action) || action < 1 || action > 3) {
        throw new Error('Kode aksi harus 1, 2, atau 3.');
      }
      return { data_type: 'action', action: action };
    }

    const raw = String(el.scoreValue.value).trim();
    if (!/^\d+$/.test(raw)) {
      throw new Error('Skor harus berupa bilangan bulat tidak negatif (tanpa titik/koma).');
    }
    if (!decimalLessThan(raw, String(MAX_SCORE + 1))) {
      throw new Error('Skor melebihi batas aplikasi 1.000.000.');
    }
    const p = state.view.params && state.view.params.p;
    if (p && !decimalLessThan(raw, p)) {
      throw new Error('Skor harus lebih kecil dari p. Gunakan Mode Aman atau nilai yang lebih kecil.');
    }
    return { data_type: 'score', score: raw };
  }

  /* ── rendering ─────────────────────────────────────────── */

  function renderAll() {
    renderModeButtons();
    renderRolePanels();
    renderPackets();
    renderLog();
    renderServerResult();
    renderFoot();
    renderStageCards();
    updateControls();
    updateNote();
  }

  function renderModeButtons() {
    document.querySelectorAll('[data-mode]').forEach(function (btn) {
      const active = btn.dataset.mode === state.mode;
      btn.classList.toggle('is-active', active);
      btn.setAttribute('aria-pressed', String(active));
      btn.disabled = state.busy || state.view.has_session;
    });
  }

  function renderRoleList(container, rows, emptyText) {
    if (!container) return;
    container.replaceChildren();
    if (!rows || rows.length === 0) {
      container.appendChild(make('p', 'vault-empty', emptyText));
      return;
    }
    rows.forEach(function (row) {
      const wrap = make('div', 'kv-row');
      const key = make('span', 'kv-key', row.label || row.key);
      const value = make('span', 'kv-val', row.value);
      value.title = row.value;
      wrap.appendChild(key);
      wrap.appendChild(value);
      container.appendChild(wrap);
    });
  }

  function renderMiniList(container, rows, hidden) {
    if (!container) return;
    container.replaceChildren();
    if (!rows || rows.length === 0) {
      const li = make('li', 'is-muted', '—');
      container.appendChild(li);
      return;
    }
    rows.forEach(function (row) {
      const li = document.createElement('li');
      const key = make('b', null, row.label || row.key);
      const value = make('span', null, hidden ? row.note : row.value);
      if (!hidden) li.title = row.value;
      li.appendChild(key);
      li.appendChild(value);
      container.appendChild(li);
    });
  }

  function renderRolePanels() {
    const roles = state.view.roles || emptyView().roles;

    renderRoleList(el.playerPublic, roles.player.public, 'Belum ada parameter.');
    renderRoleList(el.playerSecret, roles.player.secret, 'a, K, m, m′, dan k akan muncul di sini.');
    renderRoleList(el.playerSent, roles.player.sent, 'Belum ada paket keluar.');

    renderRoleList(el.serverPublic, roles.server.public, 'Belum ada parameter.');
    renderRoleList(el.serverSecret, roles.server.secret, 'x, b, K, dan hasil dekripsi akan muncul di sini.');
    renderRoleList(el.serverReceived, roles.server.received, 'Belum ada ciphertext.');

    renderMiniList(el.eveVisible, roles.eve.visible, false);
    renderMiniList(el.eveHidden, roles.eve.hidden, true);

    const step = state.view.step;
    const playerState = step < 0 ? 'idle' : step < 3 ? 'menyiapkan' : step < 6 ? 'mengirim' : 'selesai';
    const serverState = step < 0 ? 'idle' : step < 6 ? 'menerima' : 'selesai';
    el.playerState.textContent = playerState;
    el.serverState.textContent = serverState;
    el.playerState.className = 'role-state' + (step >= 0 ? ' is-live' : '') + (step >= 6 ? ' is-done' : '');
    el.serverState.className = 'role-state' + (step >= 0 ? ' is-live' : '') + (step >= 6 ? ' is-done' : '');

    if (step >= 6) {
      el.playerCaption.textContent = 'Pesan sudah terkirim. Pemain menyimpan a, K, dan k sebagai rahasia.';
      el.serverCaption.textContent = 'Server berhasil memulihkan pesan dengan x dan K.';
    } else if (step >= 4) {
      el.playerCaption.textContent = 'Ciphertext sudah dikirim. Pemain tidak mengirim a, K, m, atau k.';
      el.serverCaption.textContent = 'Server menerima c1 dan c2, lalu menyiapkan dekripsi.';
    } else if (step >= 2) {
      el.playerCaption.textContent = 'Pemain bertukar nilai publik DH dan menghitung kunci sesi K.';
      el.serverCaption.textContent = 'Server menyepakati K yang sama tanpa menerima rahasia pemain.';
    } else {
      el.playerCaption.textContent = 'Pemain memilih aksi dan mengenkripsi pesan sebelum dikirim.';
      el.serverCaption.textContent = 'Server memiliki kunci privat ElGamal dan kunci sesi hasil DH.';
    }
  }

  function renderPackets() {
    if (!el.packetFeed) return;
    const packets = state.view.packets || [];
    el.packetFeed.replaceChildren();
    el.packetCount.textContent = packets.length + ' paket';

    if (packets.length === 0) {
      el.packetFeed.appendChild(make('p', 'vault-empty', 'Belum ada paket. Jalankan Tahap 2a untuk melihat A melintas.'));
      return;
    }

    packets.forEach(function (packet) {
      const card = make('article', 'packet-card' + (packet.status === 'tampered' ? ' is-tampered' : ''));
      const top = make('div', 'packet-top');
      top.appendChild(make('span', null, '#' + String(packet.seq).padStart(2, '0') + ' · ' + packet.from + ' → ' + packet.to));
      top.appendChild(make('span', null, packet.type));
      card.appendChild(top);

      const fields = make('div', 'packet-fields');
      (packet.fields || []).forEach(function (field) {
        const chip = make('span', 'packet-field');
        const label = make('b', null, field.label + ': ');
        chip.appendChild(label);
        chip.appendChild(document.createTextNode(field.value));
        chip.title = field.label + ' = ' + field.value;
        fields.appendChild(chip);
      });
      card.appendChild(fields);

      if (packet.note) card.appendChild(make('p', 'packet-note', packet.note));
      el.packetFeed.appendChild(card);
    });
    el.packetFeed.scrollTop = el.packetFeed.scrollHeight;
  }

  function renderLog() {
    if (!el.logList) return;
    const logs = state.view.logs || [];
    el.logList.replaceChildren();
    el.logCount.textContent = logs.length + ' entri';
    if (logs.length === 0) {
      el.logList.appendChild(make('li', 'log-empty', 'Log akan terisi saat tahap dijalankan.'));
      return;
    }
    logs.forEach(function (entry) {
      const li = make('li', 'log-entry is-' + entry.kind);
      li.appendChild(make('span', 'log-seq', '#' + String(entry.seq).padStart(2, '0')));
      li.appendChild(make('span', 'log-stage', entry.stage === '0' ? 'T0' : 'T' + entry.stage));
      li.appendChild(make('span', 'log-msg', entry.message));
      el.logList.appendChild(li);
    });
    el.logList.scrollTop = el.logList.scrollHeight;
  }

  function renderServerResult() {
    if (!el.serverResult) return;
    const valueNode = $('.result-value', el.serverResult);
    const metaNode = $('.result-meta', el.serverResult);
    el.serverResult.className = 'server-result';

    if (state.view.tamper) {
      valueNode.textContent = state.view.tamper.label;
      metaNode.textContent = 'MENCURIGAKAN · nilai berbeda dari aslinya';
      el.serverResult.classList.add('is-danger');
      return;
    }

    const dec = state.view.decryption || {};
    if (dec.valid && dec.label) {
      valueNode.textContent = dec.label;
      metaNode.textContent = 'dekripsi valid · m = ' + shortNumber(dec.m, 12, 6);
      el.serverResult.classList.add('is-success');
      return;
    }

    if (state.view.message && state.view.message.m && state.view.message.label) {
      valueNode.textContent = state.view.message.label;
      metaNode.textContent = 'pesan disiapkan, menunggu enkripsi';
      return;
    }

    valueNode.textContent = '—';
    metaNode.textContent = 'menunggu dekripsi';
  }

  function renderFoot() {
    const step = state.view.step;
    const done = step >= 8;
    if (el.footMode) el.footMode.textContent = state.view.mode_label || (state.mode === 'safe' ? 'Mode Aman · 128 bit' : 'Mode Demo · 16 bit');
    if (el.footStep) el.footStep.textContent = completedCount() + ' / 8';
    if (el.footP) {
      const p = state.view.params && state.view.params.p;
      el.footP.textContent = p || '—';
      el.footP.title = p || '';
    }
    if (el.footStatus) {
      if (state.busy) el.footStatus.textContent = 'Menjalankan tahap…';
      else if (done) el.footStatus.textContent = 'Sesi selesai — semua tahap berhasil';
      else if (step < 0) el.footStatus.textContent = 'Siap memulai sesi baru';
      else el.footStatus.textContent = 'Sesi berjalan · ' + completedCount() + ' tahap selesai';
    }
    if (el.windowBadge) el.windowBadge.textContent = done ? 'Sesi selesai' : state.busy ? 'Memproses…' : 'Sesi lokal · offline';
  }

  /* ── stage cards ───────────────────────────────────────── */

  function renderStageShells() {
    if (!el.stageGrid) return;
    el.stageGrid.replaceChildren();
    STAGE_DEFS.forEach(function (def) {
      const card = make('article', 'stage-card is-locked' + (def.wide ? ' is-wide' : ''));
      card.id = 'stage-card-' + def.number;
      card.dataset.stage = String(def.number);

      const head = make('div', 'stage-head');
      head.appendChild(make('span', 'stage-number', String(def.number).padStart(2, '0')));
      head.appendChild(make('span', 'stage-status', 'Menunggu'));
      card.appendChild(head);
      card.appendChild(make('h3', 'stage-title', def.title));
      card.appendChild(make('p', 'stage-desc', def.desc));

      const body = make('div', 'stage-body');
      body.appendChild(make('div', 'stage-formula', def.formula));
      card.appendChild(body);
      card.appendChild(make('p', 'stage-locked-note', 'Jalankan tahap ini untuk menampilkan rumus, substitusi angka, dan hasil.'));
      el.stageGrid.appendChild(card);
    });
  }

  function renderStageCards() {
    STAGE_DEFS.forEach(renderStageCard);
  }

  function renderStageCard(def) {
    const card = $('#stage-card-' + def.number);
    if (!card) return;
    const data = state.stageData[def.number];
    const complete = stageIsComplete(def.number);
    const current = !!nextAction() && nextAction().stage === def.number && !complete;

    card.className = 'stage-card' + (def.wide ? ' is-wide' : '') +
      (complete ? ' is-done' : '') +
      (data && !complete ? ' is-active' : '') +
      (!data ? ' is-locked' : '') +
      (current ? ' is-current' : '');

    const status = $('.stage-status', card);
    if (status) {
      if (complete) status.textContent = 'Selesai';
      else if (data && def.number === 2) status.textContent = (data.blocks || []).length + ' / 4';
      else if (current && data) status.textContent = 'Berjalan';
      else if (current) status.textContent = 'Berikutnya';
      else status.textContent = 'Menunggu';
    }

    const body = $('.stage-body', card);
    if (!body) return;
    body.replaceChildren();

    if (!data) {
      body.appendChild(make('div', 'stage-formula', def.formula));
      const locked = $('.stage-locked-note', card);
      if (locked) locked.remove();
      card.appendChild(make('p', 'stage-locked-note', 'Jalankan tahap ini untuk menampilkan rumus, substitusi angka, dan hasil.'));
      return;
    }

    const locked = $('.stage-locked-note', card);
    if (locked) locked.remove();

    (data.blocks || []).forEach(function (block) {
      const blockEl = make('div', 'stage-block');
      blockEl.appendChild(make('div', 'stage-block-label', block.label));
      if (block.formula) blockEl.appendChild(make('div', 'stage-formula', block.formula));
      if (block.substitution) blockEl.appendChild(make('div', 'stage-sub', block.substitution));
      if (block.result) {
        const tone = block.tone === 'danger' ? ' is-danger' : block.tone === 'warn' ? ' is-warn' : '';
        blockEl.appendChild(make('div', 'stage-result' + tone, block.result));
      }
      body.appendChild(blockEl);
    });

    if (data.type === 'eve') {
      const grid = make('div', 'stage-eve-grid');
      const visibleCol = make('div', 'stage-eve-col');
      visibleCol.appendChild(make('span', 'data-tag tag-public', 'Bisa dilihat Eve'));
      const visList = document.createElement('ul');
      (data.visible || []).forEach(function (row) {
        const li = document.createElement('li');
        const b = make('b', null, row.label + ': ');
        li.appendChild(b);
        li.appendChild(document.createTextNode(row.value));
        li.title = row.value;
        visList.appendChild(li);
      });
      visibleCol.appendChild(visList);
      grid.appendChild(visibleCol);

      const hiddenCol = make('div', 'stage-eve-col is-concealed');
      hiddenCol.appendChild(make('span', 'data-tag tag-secret', 'Tidak bisa dilihat Eve'));
      const hidList = document.createElement('ul');
      (data.hidden || []).forEach(function (row) {
        const li = document.createElement('li');
        const b = make('b', null, row.label + ': ');
        li.appendChild(b);
        li.appendChild(document.createTextNode(row.note));
        hidList.appendChild(li);
      });
      hiddenCol.appendChild(hidList);
      grid.appendChild(hiddenCol);
      body.appendChild(grid);
    }

    if (data.type === 'tamper') {
      body.appendChild(make('div', 'stage-tamper-banner', 'Paket dimodifikasi di jaringan. Ini bukan ciphertext yang dibuat pemain.'));
      if (data.tamper) {
        const grid = make('div', 'stage-eve-grid');
        const orig = make('div', 'stage-eve-col');
        orig.appendChild(make('span', 'data-tag tag-public', 'Nilai asli'));
        const oul = document.createElement('ul');
        oul.appendChild(make('li', null, 'c2 = ' + data.tamper.original_c2));
        oul.appendChild(make('li', null, 'm = ' + data.tamper.original_m + ' → ' + data.tamper.original_label));
        orig.appendChild(oul);
        grid.appendChild(orig);

        const bad = make('div', 'stage-eve-col is-concealed');
        bad.appendChild(make('span', 'data-tag tag-secret', 'Setelah diubah Eve'));
        const bul = document.createElement('ul');
        bul.appendChild(make('li', null, 'c2′ = ' + data.tamper.tampered_c2));
        bul.appendChild(make('li', null, 'm = ' + data.tamper.m + ' → ' + data.tamper.label));
        bad.appendChild(bul);
        grid.appendChild(bad);
        body.appendChild(grid);
      }
    }

    if (data.summary) body.appendChild(make('div', 'stage-summary', data.summary));
    if (data.note) body.appendChild(make('p', 'stage-note', data.note));
  }

  /* ── controls & state ──────────────────────────────────── */

  function updateControls() {
    const step = state.view.step;
    const done = step >= 8;
    const action = nextAction();

    if (el.btnNext) el.btnNext.disabled = state.busy || !action;
    if (el.btnRunAll) el.btnRunAll.disabled = state.busy || !action;
    if (el.btnReset) el.btnReset.disabled = state.busy;
    if (el.btnCheat) el.btnCheat.disabled = state.busy || step !== 7;

    const lockInputs = state.busy || step >= 4;
    if (el.dataType) el.dataType.disabled = lockInputs;
    if (el.actionValue) el.actionValue.disabled = lockInputs;
    if (el.scoreValue) el.scoreValue.disabled = lockInputs;

    if (el.nextHint) {
      el.nextHint.textContent = action ? 'Berikutnya: ' + action.label + '.' : 'Semua tahap selesai. Reset untuk mengulang sesi.';
    }
    if (el.progressLabel) el.progressLabel.textContent = completedCount() + ' / 8 tahap';

    if (el.sessionStatus) {
      if (state.busy) {
        el.sessionStatus.className = 'session-status is-live';
        el.sessionStatus.innerHTML = '<i aria-hidden="true"></i>Memproses';
      } else if (done) {
        el.sessionStatus.className = 'session-status is-done';
        el.sessionStatus.innerHTML = '<i aria-hidden="true"></i>Selesai';
      } else if (step >= 0) {
        el.sessionStatus.className = 'session-status is-live';
        el.sessionStatus.innerHTML = '<i aria-hidden="true"></i>Berjalan · ' + completedCount() + '/8';
      } else {
        el.sessionStatus.className = 'session-status';
        el.sessionStatus.innerHTML = '<i aria-hidden="true"></i>Belum dimulai';
      }
    }

    if (el.progressTrack) {
      const spans = el.progressTrack.children;
      for (let i = 0; i < spans.length; i++) {
        const isDone = stageIsComplete(i);
        const isCurrent = !!action && action.stage === i && !isDone;
        spans[i].className = isDone ? 'is-done' : isCurrent ? 'is-current' : '';
      }
    }
  }

  function updateNote() {
    if (state.note) {
      setNote(state.note.kind, state.note.message);
      return;
    }
    const step = state.view.step;
    const p = state.view.params && state.view.params.p;
    if (step >= 8) {
      setNote('', 'Sesi selesai. Tekan Reset untuk memulai percobaan baru dengan parameter dan nonce baru.');
    } else if (step >= 4) {
      setNote('', 'Pesan sudah terkunci pada sesi ini. Tekan Reset untuk mengganti aksi/skor atau mode.');
    } else if (p) {
      setNote('', 'Pesan harus memenuhi 0 ≤ m < p. p = ' + shortNumber(p, 18, 8) + '. Gunakan Mode Aman untuk angka yang lebih besar.');
    } else {
      setNote('', 'Pesan harus memenuhi 0 ≤ m < p. Nilai p akan muncul setelah Tahap 0.');
    }
  }

  function setBusy(busy) {
    state.busy = busy;
    updateControls();
    renderModeButtons();
    renderFoot();
  }

  /* ── actions ───────────────────────────────────────────── */

  async function performAction(action) {
    if (!action || state.busy) return false;
    setBusy(true);
    state.note = null;

    if (action.index === 0) {
      state.stageData = {};
      state.stageData = {};
    }

    try {
      const method = action.method || 'POST';
      const body = method === 'GET' ? undefined : (action.body ? action.body() : {});
      const data = await api(action.endpoint, { method: method, body: body });

      if (data.view) {
        state.view = data.view;
        if (data.view.mode) state.mode = data.view.mode;
      } else {
        if (data.progress && typeof data.progress.step === 'number') {
          state.view.step = data.progress.step;
        }
        if (data.logs) state.view.logs = data.logs;
        if (data.packets) state.view.packets = data.packets;
      }
      if (data.stage) {
        state.stageData[data.stage.number] = data.stage;
      }
      if (data.eve) {
        state.eve = data.eve;
      }

      setNote('', '');
      state.note = null;
      renderAll();

      if (action.index === 8 && data.stage && data.stage.tamper) {
        const card = $('#stage-card-7');
        if (card) card.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
      return true;
    } catch (err) {
      setNote('error', err.message);
      toast(err.message, 'error');
      renderAll();
      return false;
    } finally {
      setBusy(false);
    }
  }

  async function runNext() {
    const action = nextAction();
    if (!action) {
      toast('Semua tahap sudah selesai. Reset untuk mengulang.', 'success');
      return;
    }
    await performAction(action);
  }

  async function runAll() {
    if (state.busy) return;
    const start = state.view.step + 1;
    if (start >= ACTIONS.length) {
      toast('Semua tahap sudah selesai. Reset untuk mengulang.', 'success');
      return;
    }

    for (let i = start; i < ACTIONS.length; i++) {
      const ok = await performAction(ACTIONS[i]);
      if (!ok) return;
      await sleep(180);
    }
    toast('Seluruh tahap 0–7 selesai dijalankan.', 'success');
  }

  async function resetSession(silent) {
    if (state.busy) return;
    setBusy(true);
    try {
      const data = await api('/api/reset', { method: 'POST', body: {} });
      state.view = data.view;
      state.stageData = {};
      state.note = null;
      state.mode = 'demo';
      setModeUI('demo');
      setNote('', '');
      renderAll();
      if (!silent) toast('Sesi direset. Parameter baru akan dibuat pada Tahap 0.', 'success');
    } catch (err) {
      setNote('error', err.message);
      toast(err.message, 'error');
    } finally {
      setBusy(false);
    }
  }

  function setModeUI(mode) {
    state.mode = mode;
    document.querySelectorAll('[data-mode]').forEach(function (btn) {
      const active = btn.dataset.mode === mode;
      btn.classList.toggle('is-active', active);
      btn.setAttribute('aria-pressed', String(active));
    });
  }

  function updateDataTypeUI() {
    state.dataType = el.dataType.value;
    if (state.dataType === 'action') {
      el.actionControl.classList.remove('is-hidden');
      el.scoreControl.classList.add('is-hidden');
    } else {
      el.actionControl.classList.add('is-hidden');
      el.scoreControl.classList.remove('is-hidden');
    }
    state.note = null;
    updateNote();
  }

  /* ── initialisation ────────────────────────────────────── */

  function bind() {
    el.toast = $('#toast');
    el.controlNote = $('#controlNote');
    el.controlNoteText = $('#controlNoteText');
    el.sessionStatus = $('#sessionStatus');
    el.btnNext = $('#btnNext');
    el.btnRunAll = $('#btnRunAll');
    el.btnReset = $('#btnReset');
    el.btnCheat = $('#btnCheat');
    el.dataType = $('#dataType');
    el.actionValue = $('#actionValue');
    el.scoreValue = $('#scoreValue');
    el.actionControl = $('#actionControl');
    el.scoreControl = $('#scoreControl');
    el.scoreHint = $('#scoreHint');
    el.progressLabel = $('#progressLabel');
    el.progressTrack = $('#progressTrack');
    el.nextHint = $('#nextHint');
    el.stageGrid = $('#stageGrid');
    el.logList = $('#logList');
    el.logCount = $('#logCount');
    el.packetFeed = $('#packetFeed');
    el.packetCount = $('#packetCount');
    el.eveVisible = $('#eveVisible');
    el.eveHidden = $('#eveHidden');
    el.playerPublic = $('#playerPublic');
    el.playerSecret = $('#playerSecret');
    el.playerSent = $('#playerSent');
    el.serverPublic = $('#serverPublic');
    el.serverSecret = $('#serverSecret');
    el.serverReceived = $('#serverReceived');
    el.serverResult = $('#serverResult');
    el.playerState = $('#playerState');
    el.serverState = $('#serverState');
    el.playerCaption = $('#playerCaption');
    el.serverCaption = $('#serverCaption');
    el.footMode = $('#footMode');
    el.footStep = $('#footStep');
    el.footP = $('#footP');
    el.footStatus = $('#footStatus');
    el.windowBadge = $('#windowBadge');

    document.querySelectorAll('[data-mode]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        if (state.view.has_session || state.busy) return;
        setModeUI(btn.dataset.mode);
        state.note = null;
        updateNote();
      });
    });

    document.querySelectorAll('[data-scroll-sim]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        $('#simulator').scrollIntoView({ behavior: 'smooth', block: 'start' });
      });
    });

    el.btnNext.addEventListener('click', runNext);
    el.btnRunAll.addEventListener('click', runAll);
    el.btnReset.addEventListener('click', function () { resetSession(false); });
    el.btnCheat.addEventListener('click', async function () {
      if (state.view.step !== 7) {
        toast('Selesaikan Tahap 6 (panel Eve) terlebih dahulu.', 'error');
        return;
      }
      await performAction(ACTIONS[8]);
    });

    el.dataType.addEventListener('change', updateDataTypeUI);
    el.scoreValue.addEventListener('input', function () {
      const raw = String(el.scoreValue.value).trim();
      if (raw && !/^\d+$/.test(raw)) {
        el.scoreHint.textContent = 'bilangan bulat ≥ 0';
        return;
      }
      el.scoreHint.textContent = '0 – 1.000.000';
      if (state.note && state.note.kind === 'error') {
        state.note = null;
        updateNote();
      }
    });
  }

  async function loadInitialState() {
    try {
      const response = await fetch('/api/state', { headers: { 'Accept': 'application/json' } });
      const data = await response.json();
      if (!data.ok) throw new Error(data.error || 'Gagal membaca state.');
      if (data.view && data.view.has_session) {
        // Tampilan tahapan tidak disimpan di localStorage; mulai sesi bersih
        // agar state server dan kartu tahap selalu konsisten.
        const resetResponse = await fetch('/api/reset', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' });
        const resetData = await resetResponse.json();
        state.view = resetData.view;
        state.stageData = {};
        toast('Sesi sebelumnya direset agar tampilan dan state server konsisten.', 'success');
      } else {
        state.view = data.view || emptyView();
      }
      if (state.view.mode) state.mode = state.view.mode;
      if (state.view.params && state.view.params.p) {
        el.scoreHint.textContent = '0 – 1.000.000 (harus < p)';
      }
    } catch (err) {
      state.view = emptyView();
      setNote('error', 'Server Python belum berjalan. Jalankan "python server.py" lalu buka http://localhost:8000.');
      toast('Tidak dapat terhubung ke server Python.', 'error');
    }
  }

  async function init() {
    bind();
    if (window.PIX) window.PIX.initAll();
    renderStageShells();
    renderAll();
    await loadInitialState();
    renderAll();
    if (state.view.has_session === false) {
      setNote('', 'Pesan harus memenuhi 0 ≤ m < p. Nilai p akan muncul setelah Tahap 0.');
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
