"""Shortlist Agent evaluation using Ragas AspectCritic.

For each CV, run the actual shortlist agent 3 times and ask Ragas's gpt-4o-mini
judge whether:
  - score_in_band: average score is within expected band [min, max]
  - score_is_stable: spread (max-min) is within tolerance
Total = 10 CVs x 2 checks = 20 checks.
"""
import json
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

from ragas import EvaluationDataset, evaluate
from ragas.dataset_schema import SingleTurnSample
from ragas.metrics import AspectCritic
from ragas.llms import LangchainLLMWrapper
from langchain_openai import ChatOpenAI


CRITERIA = [
    ("score_in_band",
     "Given the response contains 'average=<N> expected_band=[<MIN>, <MAX>]', "
     "is the average score within the expected band? Return 1 if MIN <= average <= MAX, else 0."),
    ("score_is_stable",
     "Given the response contains 'spread=<S> tolerance=<T>', is the spread within tolerance? "
     "Return 1 if S <= T, else 0."),
]


def generate_jd_text(job_form: dict) -> str:
    agent = create_workflow_agent()
    config = {"configurable": {"thread_id": f"ragas-shortlist-{uuid.uuid4()}"}}
    try:
        response = agent.invoke({"form_data": job_form}, config=config)
        if isinstance(response, dict) and "__interrupt__" in response:
            return response["__interrupt__"][0].value.get("generated_post", "")
        return response.get("generated_post", "") if isinstance(response, dict) else ""
    except GraphInterrupt as e:
        interrupts = e.args[0] if e.args else []
        return interrupts[0].value.get("generated_post", "") if interrupts else ""


def main():
    dataset_path = Path(__file__).resolve().parent / "eval_dataset.json"
    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    rules = dataset["shortlist_eval_rules"]
    eval_jd_id = f"RAGASEV_{uuid.uuid4().hex[:8]}"
    runs = rules["stability_runs"]
    tolerance = rules["stability_tolerance"]

    print("[ragas-shortlist] generating fresh JD...", file=sys.stderr)
    jd_text = generate_jd_text(dataset["job_form"])
    if not jd_text:
        print("ERROR: empty JD", file=sys.stderr)
        sys.exit(1)

    judge_llm = LangchainLLMWrapper(ChatOpenAI(model="gpt-4o-mini", temperature=0))
    metrics = [AspectCritic(name=n, definition=d, llm=judge_llm) for n, d in CRITERIA]

    samples = []
    score_records = []
    cv_ids = []
    for cv in dataset["cvs"]:
        file_path = (Path(__file__).resolve().parent / cv["file"]).resolve()
        band = cv["expected_score_band"]
        print(f"\n[ragas-shortlist] {cv['id']}: scoring 3x...", file=sys.stderr)
        parsed = process_cv(str(file_path), jd_id=eval_jd_id)["data"]
        scores = [_score_candidate_against_jd(parsed, jd_text) for _ in range(runs)]
        avg = sum(scores) / len(scores)
        spread = max(scores) - min(scores)

        response_text = (
            f"scores={scores} average={avg:.1f} "
            f"expected_band=[{band['min']}, {band['max']}] "
            f"spread={spread} tolerance={tolerance}"
        )
        sample = SingleTurnSample(
            user_input=f"Evaluate shortlist score for CV {cv['id']}",
            response=response_text,
        )
        samples.append(sample)
        score_records.append({
            "id": cv["id"],
            "scores": scores,
            "average": avg,
            "expected_band": band,
            "spread": spread,
            "tolerance": tolerance,
        })
        cv_ids.append(cv["id"])

    eval_ds = EvaluationDataset(samples=samples)
    print(f"\n[ragas-shortlist] running Ragas evaluate() on {len(samples)} CVs x {len(metrics)} criteria...", file=sys.stderr)
    result = evaluate(dataset=eval_ds, metrics=metrics, llm=judge_llm, show_progress=False)
    df = result.to_pandas()

    per_cv = []
    total_passed = 0
    total_checks = 0
    for i, rec in enumerate(score_records):
        in_band_val = df["score_in_band"].iloc[i]
        stable_val = df["score_is_stable"].iloc[i]
        try:
            in_band = int(round(float(in_band_val))) == 1
        except (TypeError, ValueError):
            in_band = False
        try:
            stable = int(round(float(stable_val))) == 1
        except (TypeError, ValueError):
            stable = False
        rec["in_band"] = in_band
        rec["stable"] = stable
        per_cv.append(rec)
        total_passed += int(in_band) + int(stable)
        total_checks += 2
        print(f"  {rec['id']}: avg={rec['average']:.1f} in_band={'PASS' if in_band else 'FAIL'} stable={'PASS' if stable else 'FAIL'}")

    print(f"\n[ragas-shortlist] {total_passed}/{total_checks} checks passed")

    out = {
        "framework": "ragas 0.2.15",
        "model": "gpt-4o-mini",
        "eval_jd_id": eval_jd_id,
        "per_cv": per_cv,
        "summary": f"{total_passed}/{total_checks}",
    }
    out_path = Path(__file__).resolve().parent / "results_shortlist_ragas.json"
    out_path.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Saved to {out_path}")


if __name__ == "__main__":
    main()
