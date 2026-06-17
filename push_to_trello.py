"""Create the HR Recruited sprint board in Trello from the sprint workbook.

Workflow board: To Do / In Progress / Review / Done. All 21 tasks land in To Do,
labelled by epic (EP-RANK / EP-PIPE) and sprint (Sprint 1 / Sprint 2).
Reads creds from .trello_creds and task data from the generated .xlsx.
"""

import json
import time
import urllib.request
import urllib.parse

import openpyxl

API = "https://api.trello.com/1"
creds = dict(l.strip().split("=", 1) for l in open(".trello_creds") if "=" in l)
KEY, TOK = creds["TRELLO_API_KEY"], creds["TRELLO_TOKEN"]


def call(method: str, path: str, **params) -> dict:
    params.update(key=KEY, token=TOK)
    data = urllib.parse.urlencode(params).encode()
    url = f"{API}/{path}"
    req = urllib.request.Request(url, data=data, method=method)
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < 3:  # rate limit
                time.sleep(1 + attempt)
                continue
            raise


def sprint_of(task_id: str) -> str:
    if task_id.startswith("EP-RANK"):
        return "Sprint 1"
    n = int(task_id.rsplit("-", 1)[1])  # EP-PIPE-BE-00N
    return "Sprint 1" if n <= 5 else "Sprint 2"


# Parse tasks out of the workbook (preserves epic / user-story context)
def read_tasks(xlsx: str):
    wb = openpyxl.load_workbook(xlsx)
    tasks = []
    for ws in wb.worksheets:
        epic = story = None
        for a, b, c, d, e, f, g, h, i, j, k in ws.iter_rows(min_row=2, values_only=True):
            if a and not b:
                epic = a
            elif b:
                story = e
            elif c:
                tasks.append({
                    "id": c, "epic": epic, "story": story, "title": f,
                    "deliverable": g, "dep": h, "intdep": j, "eta": k,
                })
    return tasks


tasks = read_tasks("HRRecruited_Sprint_RANK_PIPE.xlsx")
print(f"loaded {len(tasks)} tasks")

# Board
board = call("POST", "boards/", name="HR Recruited — Sprint (RANK + PIPE)",
             defaultLists="false",
             desc="Autonomous AI recruitment system — Ranking Agent (Agent 5) + cohesive LangGraph pipeline. Backend-only. Owner: Filza.")
bid = board["id"]
print("board:", board["shortUrl"])

# Lists (pos ascending = left to right)
lists = {}
for idx, name in enumerate(["To Do", "In Progress", "Review", "Done"]):
    lst = call("POST", "lists", name=name, idBoard=bid, pos=(idx + 1) * 100)
    lists[name] = lst["id"]
print("lists:", list(lists))

# Labels
label_defs = {
    "EP-RANK": "green", "EP-PIPE": "blue",
    "Sprint 1": "yellow", "Sprint 2": "orange",
}
labels = {}
for name, color in label_defs.items():
    lab = call("POST", "labels", name=name, color=color, idBoard=bid)
    labels[name] = lab["id"]
print("labels:", list(labels))

# Cards -> To Do
todo = lists["To Do"]
for t in tasks:
    sprint = sprint_of(t["id"])
    name = f"{t['id']} · {t['title']} ({t['eta']})"
    desc_lines = [
        t["deliverable"], "",
        f"**Epic:** {t['epic']}  |  **Sprint:** {sprint}  |  **ETA:** {t['eta']}",
        f"**User story:** {t['story']}",
        f"**Depends on:** {t['dep'] or '—'}",
    ]
    if t["intdep"]:
        desc_lines.append(f"**Cross-epic dependency:** {t['intdep']}")
    idlabels = ",".join([labels[t["epic"]], labels[sprint]])
    card = call("POST", "cards", idList=todo, name=name,
                desc="\n".join(desc_lines), idLabels=idlabels, pos="bottom")
    print("  +", t["id"], "->", sprint)

print("\nDONE. Board URL:", board["shortUrl"])
