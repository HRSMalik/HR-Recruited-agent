"""Run all three Ragas evaluations in sequence."""
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
scripts = ["eval_post_ragas.py", "eval_parser_ragas.py", "eval_shortlist_ragas.py"]

for s in scripts:
    print("\n" + "=" * 70)
    print(f"Running {s}")
    print("=" * 70)
    rc = subprocess.call([sys.executable, str(HERE / s)])
    if rc != 0:
        print(f"[run_all_ragas] {s} exited with code {rc}", file=sys.stderr)

print("\n" + "=" * 70)
print("Done. See results_*_ragas.json files in ragasev/ folder.")
print("=" * 70)
