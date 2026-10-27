/* ============================================================
   Pixel sprites — hand-authored 8-bit maps.
   Flat blocks only, no gradients. Dipakai sebagai dekorasi game.
   ============================================================ */

window.PIX = (function () {
  'use strict';

  const PALETTES = {
    cloud: {
      o: '#5c6066',
      w: '#ffffff',
      b: '#c9e2fa'
    },
    cat: {
      O: '#8a3a12',
      F: '#ff5e24',
      L: '#ffb08c',
      W: '#ffffff',
      K: '#232629'
    },
    shield: {
      O: '#232629',
      F: '#cfe6fb',
      W: '#ffffff'
    },
    lock: {
      O: '#232629',
      F: '#ff5e24',
      K: '#ffffff'
    },
    key: {
      O: '#232629',
      F: '#ff5e24',
      W: '#ffffff'
    },
    eye: {
      O: '#6c3200',
      F: '#fff3e9',
      W: '#ffffff',
      K: '#232629'
    }
  };

  const SPRITES = {
    cloud: [
      '........oooo........',
      '......oowwwwoo......',
      '....oowwwwwwwwoo....',
      '...owwwwwwwwwwwwo...',
      '..owwwwwwwwwwwwwwo..',
      '.owwwwwwwwwwwwwwwwo.',
      'owwwwwwwwwwwwwwwwwwo',
      'owwwwwwwwwwwwwwwwwwo',
      'obbbbbbbbbbbbbbbbbbo',
      '.oobbbbbbbbbbbbbboo.',
      '....oooooooooooo....'
    ],
    cat: [
      '....OO....OO....',
      '...OLLO..OLLO...',
      '..OFFFFFFFFFFO..',
      '.OFFFFFFFFFFFFO.',
      '.OFFFFFFFFFFFFO.',
      '.OFWWFFFFFFWWFO.',
      '.OFWKFFFFFFKWFO.',
      '.OFFFFFLLFFFFFO.',
      '.OFFFFFKKFFFFFO.',
      '.OFFFFFFFFFFFFO.',
      '..OFFFFFFFFFFO..',
      '...OFFFFFFFFO...',
      '....OOOOOOOO....'
    ],
    shield: [
      '.OOOOOOOOOO.',
      'OFFFFFFFFFFO',
      'OFWWFFFFFFFO',
      'OFWWFFFFFFFO',
      'OFFFFFFFFFFO',
      'OFFFFFFFFFFO',
      'OFFFFFFFFFFO',
      '.OFFFFFFFFO.',
      '.OFFFFFFFFO.',
      '..OFFFFFFO..',
      '...OFFFFO...',
      '....OFFO....',
      '.....OO.....'
    ],
    lock: [
      '...OOOOOO...',
      '..OFFFFFFO..',
      '..OFOOOOFO..',
      '..OFO..OFO..',
      '..OFO..OFO..',
      'OOOOOOOOOOOO',
      'OFFFFFFFFFFO',
      'OFFFFKKFFFFO',
      'OFFFFKKFFFFO',
      'OFFFFFFFFFFO',
      'OFFFFFFFFFFO',
      'OOOOOOOOOOOO'
    ],
    key: [
      '....OOOOO.....',
      '...OFFFFFO....',
      '..OFFFFFFFO...',
      '..OFWWWWWFO...',
      '..OFWOOOWFO...',
      '..OFWWWWWFO...',
      '...OFFFFFO....',
      '....OFFFFO....',
      '.....OFFFFO...',
      '......OFFFFO..',
      '.......OFFFFO.',
      '........OFFFFO',
      '.........OOO..'
    ],
    eye: [
      '............',
      '...OOOOOO...',
      '..OFFFFFFO..',
      '.OFFFFFFFFO.',
      'OFWWWWWWWWFO',
      'OFWKKKKKKWFO',
      'OFWKKKKKKWFO',
      'OFWWWWWWWWFO',
      '.OFFFFFFFFO.',
      '..OFFFFFFO..',
      '...OOOOOO...',
      '............'
    ]
  };

  function draw(canvas, name, scale) {
    const rows = SPRITES[name];
    const palette = PALETTES[name];
    if (!rows || !palette) return;

    scale = Math.max(1, Math.round(scale || 4));

    const w = rows[0].length;
    const h = rows.length;
    const dpr = Math.min(window.devicePixelRatio || 1, 3);

    canvas.width = Math.round(w * scale * dpr);
    canvas.height = Math.round(h * scale * dpr);
    canvas.style.width = w * scale + 'px';
    canvas.style.height = h * scale + 'px';
    canvas.style.imageRendering = 'pixelated';

    const ctx = canvas.getContext('2d');
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.imageSmoothingEnabled = false;
    ctx.clearRect(0, 0, w * scale, h * scale);

    for (let y = 0; y < h; y++) {
      const row = rows[y];
      for (let x = 0; x < w; x++) {
        const ch = row[x];
        if (ch === '.' || ch === ' ') continue;
        const color = palette[ch];
        if (!color) continue;
        ctx.fillStyle = color;
        ctx.fillRect(x * scale, y * scale, scale, scale);
      }
    }
  }

  function initAll(root) {
    (root || document).querySelectorAll('canvas[data-sprite]').forEach(function (cv) {
      draw(cv, cv.dataset.sprite, Number(cv.dataset.scale || 4));
    });
  }

  return { draw: draw, initAll: initAll, SPRITES: SPRITES };
})();