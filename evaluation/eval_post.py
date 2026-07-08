"""Evaluate the Post Agent using a custom LLM-as-judge.

(Ragas's AspectCritic was the original design but it has Python 3.14 + asyncio
incompatibility issues, so we replicate the same logic with a direct OpenAI call.
Same idea: gpt-4o-mini judges each criterion as pass=1 or fail=0.)
"""
import json
import os
import re
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.stdout.reconfigure(encoding="utf-8")

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from langgraph.errors import GraphInterrupt
from openai import OpenAI

from job_post import create_workflow_agent


def generate_post(job_form: dict) -> str:
    agent = create_workflow_agent()
    config = {"configurable": {"thread_id": f"eval-{uuid.uuid4()}"}}
    try:
        response = agent.invoke({"form_data": job_form}, config=config)
        if isinstance(response, dict) and "__interrupt__" in response:
            return response["__interrupt__"][0].value.get("generated_post", "")
        return response.get("generated_post", "") if isinstance(response, dict) else ""
    except GraphInterrupt as e:
        interrupts = e.args[0] if e.args else []
        return interrupts[0].value.get("generated_post", "") if interrupts else ""


def judge(client: OpenAI, criterion_name: str, definition: str, user_input: str, response: str) -> int:
    """Ask gpt-4o-mini to return 1 (pass) or 0 (fail) for the given criterion."""
    prompt = f"""You are an evaluator. Judge whether the AI's response satisfies the criterion below.

Criterion: {criterion_name}
Definition: {definition}

Input:
{user_input}

Response:
{response}

Reply with ONLY "1" if the response satisfies the criterion, or "0" if it does not.
No other text, no explanation."""
    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0,
        max_tokens=5,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = (completion.choices[0].message.content or "").strip()
    m = re.search(r"[01]", raw)
    return int(m.group(0)) if m else 0


def run_eval(dataset: dict) -> dict:
    job_form = dataset["job_form"]
    print(f"[post] generating post for: {job_form['title']}", file=sys.stderr)
    post = generate_post(job_form)
    if not post:
        return {"error": "generation produced empty post"}

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    results = {"generated_post_preview": post[:200] + "...", "criteria": {}}
    for crit in dataset["post_agent_eval_criteria"]:
        score = judge(client, crit["name"], crit["definition"], json.dumps(job_form), post)
        results["criteria"][crit["name"]] = score
        status = "PASS" if score else "FAIL"
        print(f"  {crit['name']:30s} {status}")

    passed = sum(results["criteria"].values())
    total = len(results["criteria"])
    results["summary"] = f"{passed}/{total} criteria passed"
    print(f"\n[post] {results['summary']}")
    return results


def main():
    dataset_path = Path(__file__).resolve().parent / "eval_dataset.json"
    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    results = run_eval(dataset)

    out_path = Path(__file__).resolve().parent / "results_post.json"
    out_path.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nSaved to {out_path}")


if __name__ == "__main__":
    main()
