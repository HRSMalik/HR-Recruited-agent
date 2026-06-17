# Sprint / CR Excel Sheet — Authoring Spec

Drop this into any project and follow it to produce sprint or change-request planning
workbooks (`.xlsx`) in the standard Rezolv24 "04" style. The output is an openpyxl
workbook with one sheet per track (e.g. Frontend / Backend), each laid out as an
Epic → User Story → Task hierarchy with deterministic styling.

---

## 1. Workbook structure

- **One sheet per track.** Typical split is `Frontend — <EPIC>` and `Backend — <EPIC>`.
  Name sheets `"<Track> — <EPIC-ID>"` (e.g. `Frontend — EP-07-CR`).
- Each sheet has the **same 11-column header**, then one Epic row, then repeating
  blocks of one User Story row followed by its Task rows.

### Column layout (fixed — 11 columns A–K)

| Col | Header | Epic row | User Story row | Task row |
| --- | ------ | -------- | -------------- | -------- |
| A | Epic | Epic ID | — | — |
| B | User Story # | — | US ID | — |
| C | Task # | — | — | Task ID |
| D | Epic Name | Epic name | — | — |
| E | User Story | — | Story sentence | — |
| F | Activity | — | — | Task title (short) |
| G | Deliverable | — | — | Full task description (one dense paragraph) |
| H | Dependent Task | — | — | Predecessor Task ID, or `—` |
| I | Ext. Dependency | — | — | (usually blank) |
| J | Int. Dependency | — | — | (usually blank) |
| K | ETA | — | — | Estimate e.g. `3h` |

Every row still spans all 11 columns (empty cells are filled with the row's
background colour — see styling).

### ID conventions

- **Epic:** `EP-<NN>` (sprint) or `EP-<NN>-CR` (change request). Same epic ID on both sheets.
- **User Story:** `US-<EPIC>-<TRACK>-<NN>` e.g. `US-07-CR-FE-01`, `US-07-CR-BE-02`.
- **Task:** `EP-<EPIC>-<TRACK>-<NNN>` e.g. `EP-07-CR-FE-001`. Numbered **globally and
  sequentially within a sheet** (do not restart per user story).
- `<TRACK>` = `FE` or `BE`.

### Content rules

- **Task title (Activity, col F):** short imperative label, ~3–8 words.
- **Deliverable (col G):** one dense paragraph describing exactly what the task
  produces — scope, endpoints/components touched, validation, audit, edge cases.
  This is the contract for the task. Write it like the existing tickets: specific,
  technical, no fluff, no bullet lists inside the cell.
- **ETA (col K):** each task ≤ ~8h; prefer ≤ 6h. If bigger, split into more tasks.
  Use `h` suffix (`2h`, `0.5h`). The original backlog rule is each item implementable
  in under ~2h where practical; sprint tasks may run larger but keep them bounded.
- **Dependent Task (col H):** the single most important predecessor task ID, or `—`.
- **Group tasks under a User Story** by theme; give each story a one-sentence
  narrative in col E describing the user-facing capability.
- Put a short note above the smaller track listing which items are
  "frontend-only / backend-only — no counterpart ticket", so reviewers see nothing
  was dropped.

---

## 2. Styling — the "04" look (match exactly)

Colours (ARGB hex, no `#`):

| Element | Fill | Font |
| ------- | ---- | ---- |
| Header row (row 1) | `1A1A3E` (navy) | white, **bold**, size 10 |
| Epic row | `1A1A3E` (navy) | white, **bold**, size 10 |
| User Story row | `2D2D6B` (purple) | white, **bold**, size 10 |
| Task row (odd, 1st in story) | `EBEBF9` (lavender) | ink `1A1A3E`, normal, size 9 |
| Task row (even) | `FFFFFF` (white) | ink `1A1A3E`, normal, size 9 |

- **Striping:** task rows alternate lavender / white, **resetting to lavender at the
  start of every user story** (first task after a US row is always lavender).
- **Alignment (all cells):** `wrap_text=True`, vertical `center`, horizontal `left`.
- **Row heights:** header 36, epic 26, user story 22, task 60.
- **Column widths:** A 8, B 14, C 13, D 32, E 36, F 38, G 72, H 28, I 26, J 22, K 7.
- No freeze panes (match the source); add `ws.freeze_panes = 'A2'` only if asked.

---

## 3. Turnkey generator

Define the data as ordered tuples per sheet, then call `build_sheet`. This reproduces
the exact format above.

```python
import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill

HEADERS = ['Epic', 'User Story #', 'Task #', 'Epic Name', 'User Story', 'Activity',
           'Deliverable', 'Dependent Task', 'Ext. Dependency', 'Int. Dependency', 'ETA']

# Row tuples:
#   ('epic', '<EP-ID>', '<Epic name>')
#   ('us',   '<US-ID>', '<Story sentence>')
#   ('task', '<Task-ID>', '<Title>', '<Deliverable paragraph>', '<DepTaskID or —>', '<ETA>')

NAVY, PURPLE, LAVEND, WHITE, INK = '1A1A3E', '2D2D6B', 'EBEBF9', 'FFFFFF', '1A1A3E'
HDR_FILL = EPIC_FILL = PatternFill('solid', fgColor=NAVY)
US_FILL  = PatternFill('solid', fgColor=PURPLE)
LAVEND_FILL = PatternFill('solid', fgColor=LAVEND)
WHITE_FILL  = PatternFill('solid', fgColor=WHITE)
HDR_FONT = Font(bold=True, color='FFFFFF', size=10)
US_FONT  = Font(bold=True, color='FFFFFF', size=10)
TASK_FONT = Font(bold=False, color=INK, size=9)
ALIGN = Alignment(wrap_text=True, vertical='center', horizontal='left')
WIDTHS = {'A':8,'B':14,'C':13,'D':32,'E':36,'F':38,'G':72,'H':28,'I':26,'J':22,'K':7}

def _style(ws, row, fill, font, height):
    for col in range(1, 12):
        c = ws.cell(row=row, column=col)
        c.fill, c.font, c.alignment = fill, font, ALIGN
    ws.row_dimensions[row].height = height

def build_sheet(ws, rows):
    ws.append(HEADERS)
    _style(ws, 1, HDR_FILL, HDR_FONT, 36)
    stripe = 0
    for r in rows:
        if r[0] == 'epic':
            ws.append([r[1], None, None, r[2]])                 # A=id, D=name
            _style(ws, ws.max_row, EPIC_FILL, HDR_FONT, 26)
        elif r[0] == 'us':
            ws.append([None, r[1], None, None, r[2]])           # B=id, E=story
            _style(ws, ws.max_row, US_FILL, US_FONT, 22)
            stripe = 0
        else:  # task: C=id, F=title, G=deliverable, H=dep, K=eta
            _, tid, title, deliverable, dep, eta = r
            ws.append([None, None, tid, None, None, title, deliverable, dep, None, None, eta])
            fill = LAVEND_FILL if stripe % 2 == 0 else WHITE_FILL
            _style(ws, ws.max_row, fill, TASK_FONT, 60)
            stripe += 1
    for col, w in WIDTHS.items():
        ws.column_dimensions[col].width = w

# --- usage ---
FRONTEND = [
    ('epic', 'EP-07', 'My Epic — Frontend'),
    ('us', 'US-07-FE-01', 'As a user I can ...'),
    ('task', 'EP-07-FE-001', 'Build the thing', 'Full paragraph describing the deliverable ...', '—', '3h'),
    # ...
]
BACKEND = [ ('epic', 'EP-07', 'My Epic — Backend'), ... ]

wb = openpyxl.Workbook()
fe = wb.active; fe.title = 'Frontend — EP-07'; build_sheet(fe, FRONTEND)
be = wb.create_sheet('Backend — EP-07');       build_sheet(be, BACKEND)
wb.save('MyProject_Sprint_EP07.xlsx')
```

---

## 4. Authoring workflow (how the other Claude should run it)

1. **Collect requirements** one change/feature at a time; restate each capture back
   for confirmation before moving on.
2. **Classify** each item: frontend, backend, or both. If a change has a server side,
   always add the mirrored backend task.
3. **Chunk** into tasks ≤ ~6–8h; split anything larger. Group tasks under coherent
   user stories with a one-line narrative.
4. **Write deliverables** as dense, specific paragraphs (scope, files/endpoints,
   validation, audit, permissions, edge cases). Ground them in the actual codebase
   where possible (cite real components/routes).
5. **Number IDs** sequentially per sheet; set dependencies via the Dependent Task col.
6. **Generate** with `build_sheet`, then **read the workbook back** to verify layout,
   palette, IDs, dependencies, and ETA totals before handing it over.
7. **Flag overlaps/reversals** (anything that supersedes or contradicts prior work)
   in the relevant deliverable text so reviewers catch it.
```
