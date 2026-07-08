"""Parser Agent evaluation using Ragas AspectCritic.

For each CV: parse via parser_agent, then ask Ragas's gpt-4o-mini judge
whether each extracted field matches the ground truth (reference).

5 criteria per CV: name_correct, email_correct, phone_correct,
education_correct, experience_correct. Total = 10 CVs x 5 = 50 checks.
"""
import json
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.stdout.reconfigure(encoding="utf-8")

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from parser_agent import process_cv

from ragas import EvaluationDataset, evaluate
from ragas.dataset_schema import SingleTurnSample
from ragas.metrics import AspectCritic
from ragas.llms import LangchainLLMWrapper
from langchain_openai import ChatOpenAI


FIELD_CRITERIA = [
    ("name_correct",       "Does the extracted name match the reference name (case/whitespace-insensitive, allow nicknames)?"),
    ("email_correct",      "Does the extracted email exactly match the reference email (case-insensitive)?"),
    ("phone_correct",      "Does the extracted phone match the reference phone (ignoring spaces, dashes, country code formatting)?"),
    ("education_correct",  "Does the extracted education degree match the reference degree semantically? Treat 'BS' = 'Bachelor's' = 'Bachelor of Science', 'MS' = 'Master's' = 'M.S' etc."),
    ("experience_correct", "Does the extracted experience_years match the reference within tolerance (+/- 0.5 years)?"),
]


def build_sample_for_cv(cv_entry: dict, parsed: dict) -> SingleTurnSample:
    gt = cv_entry["ground_truth"]
    user_input = json.dumps({
        "task": "Extract structured fields from CV: name, email, phone, education, experience_years",
        "cv_file": cv_entry["file"],
    })
    response = json.dumps({
        "name": parsed.get("name"),
        "email": parsed.get("email"),
        "phone": parsed.get("phone"),
        "last_education_degree": parsed.get("last_education_degree"),
        "experience_years": parsed.get("experience_years"),
    }, ensure_ascii=False)
    reference = json.dumps({
        "name": gt.get("name"),
        "email": gt.get("email"),
        "phone": gt.get("phone"),
        "last_education_degree": gt.get("last_education_degree"),
        "experience_years": gt.get("experience_years_approx"),
        "experience_tolerance": gt.get("experience_years_tolerance"),
    }, ensure_ascii=False)
    return SingleTurnSample(user_input=user_input, response=response, reference=reference)


def main():
    dataset_path = Path(__file__).resolve().parent / "eval_dataset.json"
    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    eval_jd_id = f"RAGASEV_{uuid.uuid4().hex[:8]}"

    judge_llm = LangchainLLMWrapper(ChatOpenAI(model="gpt-4o-mini", temperature=0))
    metrics = [
        AspectCritic(name=name, definition=defn, llm=judge_llm)
        for name, defn in FIELD_CRITERIA
    ]

    samples = []
    cv_ids = []
    for cv in dataset["cvs"]:
        file_path = (Path(__file__).resolve().parent / cv["file"]).resolve()
        print(f"\n[ragas-parser] {cv['id']}: parsing {file_path.name}", file=sys.stderr)
        parsed = process_cv(str(file_path), jd_id=eval_jd_id)["data"]
        samples.append(build_sample_for_cv(cv, parsed))
        cv_ids.append(cv["id"])

    eval_ds = EvaluationDataset(samples=samples)
    print(f"\n[ragas-parser] running Ragas evaluate() on {len(samples)} CVs x {len(metrics)} criteria...", file=sys.stderr)
    result = evaluate(dataset=eval_ds, metrics=metrics, llm=judge_llm, show_progress=False)
    df = result.to_pandas()

    per_cv = []
    total_passed = 0
    total_checks = 0
    for i, cv_id in enumerate(cv_ids):
        checks = {}
        for crit_name, _ in FIELD_CRITERIA:
            value = df[crit_name].iloc[i]
            try:
                score = int(round(float(value)))
            except (TypeError, ValueError):
                score = 0
            checks[crit_name] = bool(score)
            total_passed += score
            total_checks += 1
        per_cv.append({"id": cv_id, "checks": checks})
        passed_for_cv = sum(checks.values())
        print(f"  {cv_id}: {passed_for_cv}/{len(FIELD_CRITERIA)} criteria passed")

    print(f"\n[ragas-parser] {total_passed}/{total_checks} total field checks passed ({100*total_passed/total_checks:.0f}%)")

    out = {
        "framework": "ragas 0.2.15",
        "model": "gpt-4o-mini",
        "eval_jd_id": eval_jd_id,
        "per_cv": per_cv,
        "summary": f"{total_passed}/{total_checks}",
    }
    out_path = Path(__file__).resolve().parent / "results_parser_ragas.json"
    out_path.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Saved to {out_path}")


if __name__ == "__main__":
    main()
