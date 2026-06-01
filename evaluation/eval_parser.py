"""Evaluate the Parser Agent against ground truth.

Field-level accuracy check per CV. Exact-match (normalized) for email/phone/name,
numeric tolerance for experience, substring match for education.
"""
import json
import re
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.stdout.reconfigure(encoding="utf-8")

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from parser_agent import process_cv


def norm(s: str) -> str:
    return re.sub(r"\s+", "", str(s or "")).lower()


def name_match(predicted: str, expected: str) -> bool:
    p, e = norm(predicted), norm(expected)
    return p == e or e in p or p in e


def phone_match(predicted: str, expected: str) -> bool:
    p = re.sub(r"\D", "", str(predicted or ""))
    e = re.sub(r"\D", "", str(expected or ""))
    if not p or not e:
        return False
    return p.endswith(e[-10:]) or e.endswith(p[-10:])


def numeric_match(predicted, expected_approx: float, tolerance: float) -> bool:
    try:
        return abs(float(predicted) - expected_approx) <= tolerance
    except (ValueError, TypeError):
        return False


_DEGREE_ALIASES = {
    "bachelor": ["bs", "bsc", "b s", "b sc", "bachelors", "bachelor's", "bachelor s", "bachelor of science", "bachelor"],
    "master":   ["ms", "msc", "m s", "m sc", "mcs", "masters", "master's", "master s", "master of science", "master of computer science", "master"],
    "phd":      ["phd", "ph d", "doctorate", "doctor of philosophy"],
}


def _canonical_degree(s: str) -> str:
    """Lowercase, strip punctuation, replace all degree aliases with their canonical level."""
    s = (s or "").lower()
    s = re.sub(r"[.,'`\"\(\)]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    for canonical, aliases in _DEGREE_ALIASES.items():
        for alias in sorted(aliases, key=len, reverse=True):
            s = re.sub(rf"\b{re.escape(alias)}\b", canonical, s)
    s = re.sub(r"\bin\b", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def education_match(predicted: str, expected: str) -> bool:
    """Treat BS == Bachelor's, MS == Master's, etc. Compare canonical forms."""
    p = _canonical_degree(predicted)
    e = _canonical_degree(expected)
    if not p or not e:
        return False
    return p == e or e in p or p in e


def evaluate_cv(cv_entry: dict, eval_jd_id: str) -> dict:
    file_path = (Path(__file__).resolve().parent / cv_entry["file"]).resolve()
    gt = cv_entry["ground_truth"]
    print(f"\n[parser] {cv_entry['id']}: {file_path.name}", file=sys.stderr)

    result = process_cv(str(file_path), jd_id=eval_jd_id)
    pred = result["data"]

    checks = {
        "name":       name_match(pred.get("name"), gt["name"]),
        "email":      norm(pred.get("email")) == norm(gt["email"]),
        "phone":      phone_match(pred.get("phone"), gt["phone"]),
        "education":  education_match(pred.get("last_education_degree"), gt["last_education_degree"]),
        "experience": numeric_match(pred.get("experience_years"), gt["experience_years_approx"], gt["experience_years_tolerance"]),
    }
    for field, ok in checks.items():
        mark = "✓" if ok else "✗"
        predicted_val = pred.get(f"last_education_degree" if field == "education" else f"{field}_years" if field == "experience" else field)
        print(f"  {field:12s} {mark}  predicted={predicted_val!r}")

    return {"id": cv_entry["id"], "checks": checks, "predicted": pred}


def main():
    dataset_path = Path(__file__).resolve().parent / "eval_dataset.json"
    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    eval_jd_id = f"EVAL_RUN_{uuid.uuid4().hex[:8]}"

    per_cv = []
    for cv in dataset["cvs"]:
        per_cv.append(evaluate_cv(cv, eval_jd_id))

    total = sum(len(r["checks"]) for r in per_cv)
    passed = sum(sum(r["checks"].values()) for r in per_cv)
    print(f"\n[parser] {passed}/{total} field checks passed ({100*passed/total:.0f}%)")

    out = {"eval_jd_id": eval_jd_id, "per_cv": per_cv, "summary": f"{passed}/{total}"}
    out_path = Path(__file__).resolve().parent / "results_parser.json"
    out_path.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Saved to {out_path}")
    print(f"\nNote: Eval data tagged with jd_id={eval_jd_id}. Clean from Mongo with:")
    print(f"  db.candidates_info.deleteMany({{jd_id: '{eval_jd_id}'}})")


if __name__ == "__main__":
    main()
