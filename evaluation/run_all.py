"""Run all three agent evaluations in sequence and print a final summary."""
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

scripts = ["eval_post.py", "eval_parser.py", "eval_shortlist.py"]

for s in scripts:
    print("\n" + "=" * 70)
    print(f"Running {s}")
    print("=" * 70)
    rc = subprocess.call([sys.executable, str(HERE / s)])
    if rc != 0:
        print(f"[run_all] {s} exited with code {rc}", file=sys.stderr)

print("\n" + "=" * 70)
print("Done. See results_*.json files in evaluation/ folder.")
print("=" * 70)
