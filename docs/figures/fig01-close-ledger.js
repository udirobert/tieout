/* Fig. 01 — the close ledger.

An isometric close package: a workbook deck, a grid of answer cells, and a
write path that will not move without a recorded decision.

The visual rule is the product's argument. Everything that tied itself is
hairline and monochrome. The only lit things are the cells that need a human,
the rule that is active, and the write that is waiting. One accent colour,
and it means exactly one thing: live.

Built on the iso-figure projection kernel (github.com/MrBongoC/ai-iso-skill,
MIT) and the iso-glow lighting vocabulary (MIT). No external scripts; the
page runs from disk.

The data below is the *real* fixture — the same numbers the CLI and the
console show — so the figure cannot drift from the product. It is rendered
from `demo/close-tieout`, whose scores are construction, not model evidence.
*/

FIGS.push({
  id: 'close-ledger',
  name: 'The close ledger',
  hint: 'Press a lit cell to see its evidence · space cycles the queue',
  aria:
    'Isometric close package. Most answer cells are tied and quiet. A few glow orange: those need a human. Press one to read its evidence rows. A write lever on the left refuses to move until a decision is recorded.',

  css: `[data-fig="close-ledger"] .glass.refused { stroke: var(--accent-hi); stroke-dasharray: 3 2; }
         [data-fig="close-ledger"] .glass.refused.hot { fill: var(--recess); stroke: var(--accent-hi); }`,

  mount(stage, api) {
    // -- the fixture ---------------------------------------------------------
    // The counted close. `tied` cells verified themselves; `needsHuman` did
    // not and route to a person with their source rows attached.
    const TIED = 2629;
    const NEEDS_HUMAN = 14;
    const REFUSED = 10;

    // The exception queue, as the product recorded it: cell, why it was
    // flagged, the value proposed, and the source rows behind the proposal.
    const QUEUE = [
      {
        cell: 'Staging Sheet!K5',
        why: 'empty answer cell',
        proposed: '(blank)',
        evidence: [
          'Staging Sheet r2 · NI ABF II SCSP',
          'Staging Sheet r2 · 240-149813-030',
          'Staging Sheet r2 · Nordvik Infrastructure Advanced Bioenergy Fund II SCSp',
          'Staging Sheet r2 · EUR',
          'Staging Sheet r3 · NI ABF II SCSP',
        ],
        refused: false,
      },
      {
        cell: 'Staging Sheet!K13',
        why: 'empty answer cell',
        proposed: '(blank)',
        evidence: [
          'Staging Sheet r2 · NI ABF II SCSP',
          'Staging Sheet r2 · 240-149813-030',
          'Staging Sheet r2 · Nordvik Infrastructure Advanced Bioenergy Fund II SCSp',
          'Staging Sheet r2 · EUR',
          'Staging Sheet r3 · NI ABF II SCSP',
        ],
        refused: false,
      },
      {
        cell: 'Staging Sheet!K6',
        why: 'flagged for review — no project match',
        proposed: 'NIP PLATFORM SOLUTIONS APS',
        evidence: [
          'Staging Sheet r6 · NI ABF II SCSP',
          'Staging Sheet r6 · 240-149813-030',
          'Staging Sheet r6 · EUR',
        ],
        refused: true,
      },
    ];

    // -- geometry ------------------------------------------------------------
    // A deck of paper on the left, the answer grid on the right, the write
    // gate at the front. Drawn back to front.
    const K = api.iso.frame([
      [0, 0, 0],
      [360, 0, 0],
      [0, 250, 0],
      [360, 250, 0],
      [0, 0, 120],
      [360, 0, 120],
      [0, 250, 120],
      [360, 250, 120],
    ]);
    const { TOP, FRONT, SIDE, rect, box, boxc, path } = K;

    let svg = '';

    // The ground plate the whole thing sits on.
    svg += box(0, 0, 0, 360, 250, 8, 10);

    // -- the workbook deck (left) -------------------------------------------
    // A stack of sheets, hairline. Nothing here needs a person.
    svg += box(24, 24, 8, 96, 150, 4, 2);
    svg += box(28, 28, 12, 88, 142, 3, 2);
    svg += box(32, 32, 15, 80, 134, 3, 2);

    // -- the answer grid (right) ---------------------------------------------
    // The grid plate: this is the workbook's answer range, laid flat.
    const GX = 150, GY = 30, GW = 190, GH = 150;
    svg += box(GX, GY, 8, GW, GH, 3, 2);

    // The three exceptions, placed on the grid. This is the only lit thing
    // on the plate. Placement is fixed before anything is drawn, so a cell
    // that needs a human is never also drawn as a quiet one.
    const PLACED = [
      { q: QUEUE[0], col: 1, row: 3 },
      { q: QUEUE[1], col: 4, row: 6 },
      { q: QUEUE[2], col: 2, row: 8 },
    ];
    PLACED.forEach((p) => {
      p.q._col = p.col;
      p.q._row = p.row;
    });
    const isException = (col, row) =>
      PLACED.some((p) => p.col === col && p.row === row);

    // Hairline row and column rules — the structure, all monochrome.
    svg += `<g transform="${TOP(GX, GY, 11)}">`;
    for (let r = 1; r < 12; r++) {
      const y = r * 12;
      svg += `<line class="detail" x1="0" y1="${y}" x2="${GW}" y2="${y}"/>`;
    }
    for (let c = 1; c < 6; c++) {
      const x = c * 32;
      svg += `<line class="detail" x1="${x}" y1="0" x2="${x}" y2="${GH}"/>`;
    }
    svg += `</g>`;

    // The cells that tied themselves: quiet hairlines, no fill, no accent.
    // These are the 2,629. They are the majority and they are silent.
    for (let r = 0; r < 12; r++) {
      for (let c = 0; c < 6; c++) {
        if (isException(c, r)) continue;
        svg += `<g transform="${TOP(GX + c * 32 + 3, GY + r * 12 + 2, 11)}">`;
        svg += `<rect class="face" x="0" y="0" width="26" height="8" rx="2"/>`;
        svg += `</g>`;
      }
    }

    PLACED.forEach((p, i) => {
      const x = GX + p.col * 32 + 3;
      const y = GY + p.row * 12 + 2;
      // A cell that needs a person is lit glass, and it sits proud of the
      // grid so it reads at thumbnail size.
      svg += `<g class="press" id="cell-${i}" data-cell="${i}" tabindex="0" role="button" aria-label="${api.iso.esc(p.q.cell + ' — ' + p.q.why)}">`;
      svg += `<g transform="${TOP(x, y, 11)}">`;
      svg += `<rect class="glass${p.q.refused ? ' refused' : ''}" x="0" y="0" width="26" height="8" rx="2"${p.q.refused ? '' : ' filter="url(#bloom)"'}/>`;
      svg += `</g>`;
      // A lit cell lifts a little out of the grid.
      svg += `<g transform="${TOP(x, y, 14)}">`;
      svg += `<rect class="glass hot" x="0" y="0" width="26" height="8" rx="2"/>`;
      svg += `</g>`;
      svg += `</g>`;
    });

    // -- the write gate (front left) -----------------------------------------
    // A lever. It refuses to move until a decision is recorded. That refusal
    // is the product.
    svg += box(24, 196, 8, 70, 40, 6, 3);
    svg += `<g class="press" id="gate" tabindex="0" role="button" aria-label="the write gate — it refuses to move without a recorded decision">`;
    svg += `<g transform="${TOP(36, 206, 14)}">`;
    svg += `<rect class="face lever" x="0" y="0" width="46" height="6" rx="3"/>`;
    svg += `<rect class="led" x="40" y="1" width="4" height="4" rx="2"/>`;
    svg += `</g>`;
    svg += `</g>`;

    // -- the governed memory (back right) ------------------------------------
    // A rule card. It only lights once it has been validated and activated.
    svg += box(276, 24, 8, 60, 44, 5, 2);
    svg += `<g transform="${TOP(282, 30, 13)}">`;
    svg += `<rect class="face rule" x="0" y="0" width="48" height="8" rx="2"/>`;
    svg += `</g>`;
    svg += `<g transform="${TOP(282, 30, 13)}">`;
    svg += `<rect class="glass hot rule-lit" x="0" y="0" width="48" height="8" rx="2"/>`;
    svg += `</g>`;

    stage.setAttribute('viewBox', K.viewBox);
    stage.setAttribute('role', 'img');
    stage.setAttribute(
      'aria-label',
      `Isometric close package. ${TIED} cells tied themselves and are silent. ${NEEDS_HUMAN} cells need a human and glow orange, ${REFUSED} of them refused outright. A write lever refuses to move until a decision is recorded.`
    );
    stage.innerHTML = svg;

    // -- state ---------------------------------------------------------------
    const st = { selected: 0, decided: false, moved: false };

    const cells = PLACED.map((p, i) => stage.querySelector('#cell-' + i));
    const gate = stage.querySelector('#gate');
    const lever = gate.querySelector('.lever');
    const gateLed = gate.querySelector('.led');

    function render() {
      cells.forEach((el, i) => {
        if (!el) return;
        el.classList.toggle('down', st.selected === i);
        el.classList.toggle('latched', st.decided && st.selected === i);
      });
      // The gate: dark until a decision is recorded, lit once it has one.
      lever.classList.toggle('hot', st.decided);
      lever.classList.toggle('latched', st.moved);
      gateLed.classList.toggle('hot', st.decided);

      const q = QUEUE[st.selected];
      if (st.moved) {
        api.readout(
          `written · ${q.cell} · decision recorded before the workbook was touched`
        );
      } else if (st.decided) {
        api.readout(
          `${q.cell} · ${q.why} · ${q.evidence.length} source row(s) · gate armed`
        );
      } else {
        api.readout(`${q.cell} · ${q.why} · press to read the source rows`);
      }
      api.power(NEEDS_HUMAN > 0);
    }

    function select(i) {
      st.selected = ((i % QUEUE.length) + QUEUE.length) % QUEUE.length;
      st.decided = false;
      st.moved = false;
      render();
      const q = QUEUE[st.selected];
      api.hint(
        `${q.cell} · ${q.why} · ${q.evidence.length} source row(s) · ` +
          `${q.refused ? 'refused outright' : 'needs a decision'}`
      );
    }

    function decide() {
      if (st.decided) return;
      st.decided = true;
      api.flash(gate);
      render();
    }

    function move() {
      if (!st.decided) {
        // The refusal. The gate does not move, and it says why.
        api.flash(gate);
        api.readout('refused · no recorded decision · nothing was written');
        api.hint('the gate refuses to move without a decision');
        return;
      }
      st.moved = true;
      api.flash(gate);
      render();
      api.hint('written · the decision was recorded before the workbook was touched');
    }

    // -- wiring --------------------------------------------------------------
    cells.forEach((el, i) => {
      if (!el) return;
      el.addEventListener('click', () => {
        select(i);
        decide();
      });
      el.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          select(i);
          decide();
        }
      });
    });

    gate.addEventListener('click', move);
    gate.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        move();
      }
    });

    render();

    return {
      key(e) {
        if (e.key === 'ArrowRight' || e.key === 'ArrowDown') {
          select(st.selected + 1);
          return true;
        }
        if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') {
          select(st.selected - 1);
          return true;
        }
        if (e.key === ' ' || e.key === 'Enter') {
          decide();
          return true;
        }
        return false;
      },
      demo() {
        select(0);
        api.after(700, () => {
          decide();
          api.after(700, () => {
            move();
          });
        });
      },
    };
  },
});
