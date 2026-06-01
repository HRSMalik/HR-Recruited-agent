"""Post Agent evaluation using Ragas AspectCritic.

Uses Ragas's batch evaluate() to score the generated job post against
5 custom criteria (linkedin_friendly, covers_requirements, etc.).
Each criterion is judged by gpt-4o-mini and returns 0 (fail) or 1 (pass).
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

from ragas import EvaluationDataset, evaluate
from ragas.dataset_schema import SingleTurnSample
from ragas.metrics import AspectCritic
from ragas.llms import LangchainLLMWrapper
from langchain_openai import ChatOpenAI


def generate_post(job_form: dict) -> str:
    agent = create_workflow_agent()
    config = {"configurable": {"thread_id": f"ragas-eval-{uuid.uuid4()}"}}
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

    job_form = dataset["job_form"]
    print(f"[ragas-post] generating post for: {job_form['title']}", file=sys.stderr)
    post = generate_post(job_form)
    if not post:
        print("ERROR: empty post", file=sys.stderr)
        sys.exit(1)

    judge_llm = LangchainLLMWrapper(ChatOpenAI(model="gpt-4o-mini", temperature=0))

    metrics = [
        AspectCritic(name=c["name"], definition=c["definition"], llm=judge_llm)
        for c in dataset["post_agent_eval_criteria"]
    ]

    sample = SingleTurnSample(
        user_input=json.dumps(job_form),
        response=post,
    )
    eval_ds = EvaluationDataset(samples=[sample])

    print(f"[ragas-post] running {len(metrics)} criteria via Ragas evaluate()...", file=sys.stderr)
    result = evaluate(dataset=eval_ds, metrics=metrics, llm=judge_llm, show_progress=False)

    df = result.to_pandas()
    criteria_results = {}
    for col in df.columns:
        if col in ("user_input", "response", "retrieved_contexts", "reference"):
            continue
        value = df[col].iloc[0]
        try:
            score = int(round(float(value)))
        except (TypeError, ValueError):
            score = 0
        criteria_results[col] = score
        print(f"  {col:30s} {'PASS' if score else 'FAIL'}")

    passed = sum(criteria_results.values())
    total = len(criteria_results)
    print(f"\n[ragas-post] {passed}/{total} criteria passed")

    out = {
        "framework": "ragas 0.2.15",
        "model": "gpt-4o-mini",
        "generated_post_preview": post[:200] + "...",
        "criteria": criteria_results,
        "summary": f"{passed}/{total} criteria passed",
    }
    out_path = Path(__file__).resolve().parent / "results_post_ragas.json"
    out_path.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Saved to {out_path}")


if __name__ == "__main__":
    main()
