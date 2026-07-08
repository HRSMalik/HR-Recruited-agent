"""Evaluate the Shortlist Agent for score banding + stability.

For each CV in dataset:
  - Generate a fresh job post for the eval JD
  - Score the candidate vs that JD
  - Check if score is inside expected_score_band
  - Run the scoring N times and check variance is within stability_tolerance
"""
import json
import statistics
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.stdout.reconfigure(encoding="utf-8")

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from langgraph.errors import GraphInterrupt
from job_post import create_workflow_agent
from parser_agent import process_cv
from shortlisting_agent import _score_candidate_against_jd


def generate_jd_text(job_form: dict) -> str:
    """Run post agent to get the formatted draft (without LinkedIn / interrupt resume)."""
    agent = create_workflow_agent()
    config = {"configurable": {"thread_id": f"shortlist-eval-{uuid.uuid4()}"}}
    try:
        response = agent.invoke({"form_data": job_form}, config=config)
        if isinstance(response, dict) and "__interrupt__" in response:
            return response["__interrupt__"][0].value.get("generated_post", "")
        return response.get("generated_post", "") if isinstance(response, dict) else ""
    except GraphInterrupt as e:
        interrupts = e.args[0] if e.args else []
        return interrupts[0].value.get("generated_post", "") if interrupts else ""


def evaluate_cv(cv_entry: dict, jd_text: str, eval_jd_id: str, runs: int, tolerance: int) -> dict:
    file_path = (Path(__file__).resolve().parent / cv_entry["file"]).resolve()
    band = cv_entry["expected_score_band"]
    print(f"\n[shortlist] {cv_entry['id']}: expected band [{band['min']}, {band['max']}]", file=sys.stderr)

    parsed = process_cv(str(file_path), jd_id=eval_jd_id)["data"]

    scores = [_score_candidate_against_jd(parsed, jd_text) for _ in range(runs)]
    avg = sum(scores) / len(scores)
    in_band = band["min"] <= avg <= band["max"]
    spread = max(scores) - min(scores)
    stable = spread <= tolerance

    print(f"  runs={scores}  avg={avg:.1f}")
    print(f"  in_band:  {'✓ PASS' if in_band else '✗ FAIL'}")
    print(f"  stable:   {'✓ PASS' if stable else '✗ FAIL'} (spread {spread} vs tolerance {tolerance})")

    return {
        "id": cv_entry["id"],
        "scores": scores,
        "average": avg,
        "expected_band": band,
        "in_band": in_band,
        "spread": spread,
        "stable": stable,
    }


def main():
    dataset_path = Path(__file__).resolve().parent / "eval_dataset.json"
    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    rules = dataset["shortlist_eval_rules"]
    eval_jd_id = f"EVAL_RUN_{uuid.uuid4().hex[:8]}"

    print("[shortlist] generating fresh JD for evaluation...", file=sys.stderr)
    jd_text = generate_jd_text(dataset["job_form"])
    if not jd_text:
        print("ERROR: could not generate JD text", file=sys.stderr)
        sys.exit(1)

    per_cv = []
    for cv in dataset["cvs"]:
        per_cv.append(evaluate_cv(cv, jd_text, eval_jd_id, rules["stability_runs"], rules["stability_tolerance"]))

    total = len(per_cv) * 2
    passed = sum(r["in_band"] for r in per_cv) + sum(r["stable"] for r in per_cv)
    print(f"\n[shortlist] {passed}/{total} checks passed (band + stability combined)")

    out = {"eval_jd_id": eval_jd_id, "per_cv": per_cv, "summary": f"{passed}/{total}"}
    out_path = Path(__file__).resolve().parent / "results_shortlist.json"
    out_path.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Saved to {out_path}")


if __name__ == "__main__":
    main()
