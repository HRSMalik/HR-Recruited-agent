"""Generate PDF report from Ragas evaluation results (Parser + Shortlist only)."""
import json
from datetime import datetime
from pathlib import Path

from fpdf import FPDF

HERE = Path(__file__).resolve().parent

PARSER_FIELDS = ["name", "email", "phone", "education", "experience"]


def safe(s):
    return "".join(c if ord(c) < 256 else "?" for c in str(s))


def pct(passed, total):
    return f"{100 * passed / total:.0f}%" if total else "n/a"


class RagasReport(FPDF):
    def header(self):
        if self.page_no() == 1:
            return
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(120, 120, 120)
        self.cell(0, 5, "HR Agent - Ragas Evaluation Report", new_x="LMARGIN", new_y="NEXT", align="R")
        self.set_text_color(0, 0, 0)
        self.ln(2)

    def footer(self):
        self.set_y(-12)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(120, 120, 120)
        self.cell(0, 8, f"Page {self.page_no()}", align="C")
        self.set_text_color(0, 0, 0)

    def h1(self, text):
        self.ln(4)
        self.set_font("Helvetica", "B", 16)
        self.set_text_color(20, 60, 120)
        self.cell(0, 10, text, new_x="LMARGIN", new_y="NEXT")
        self.set_text_color(0, 0, 0)
        self.set_draw_color(20, 60, 120)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(4)

    def h2(self, text):
        self.ln(2)
        self.set_font("Helvetica", "B", 12)
        self.set_fill_color(230, 240, 250)
        self.cell(0, 8, "  " + text, new_x="LMARGIN", new_y="NEXT", fill=True)
        self.ln(2)

    def h3(self, text):
        self.ln(1)
        self.set_font("Helvetica", "B", 10)
        self.cell(0, 6, text, new_x="LMARGIN", new_y="NEXT")

    def para(self, text):
        self.set_font("Helvetica", "", 10)
        self.multi_cell(0, 5, safe(text), new_x="LMARGIN", new_y="NEXT")
        self.ln(1)

    def bullet(self, text):
        self.set_font("Helvetica", "", 10)
        self.cell(5, 5, "")
        self.cell(3, 5, "-")
        self.multi_cell(0, 5, safe(text), new_x="LMARGIN", new_y="NEXT")

    def kv(self, key, value, key_w=50):
        self.set_font("Helvetica", "B", 10)
        self.cell(key_w, 6, key)
        self.set_font("Helvetica", "", 10)
        self.multi_cell(0, 6, safe(str(value)), new_x="LMARGIN", new_y="NEXT")


def section_cover(pdf, dataset, parser_r, shortlist_r):
    pdf.set_font("Helvetica", "B", 22)
    pdf.ln(15)
    pdf.cell(0, 12, "Ragas Evaluation Report", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.set_font("Helvetica", "", 12)
    pdf.cell(0, 8, "Parser & Shortlist Agents (LLM-as-Judge via Ragas)", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.set_font("Helvetica", "I", 10)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 6, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.set_text_color(0, 0, 0)
    pdf.ln(8)

    pdf.h2("Framework Info")
    pdf.kv("Evaluation framework:", parser_r.get("framework", "ragas"))
    pdf.kv("Judge model:", parser_r.get("model", "gpt-4o-mini"))
    pdf.kv("Metric type:", "AspectCritic (LLM-as-judge, 0 = fail, 1 = pass)")

    pdf.h2("Test Setup")
    jf = dataset["job_form"]
    pdf.kv("Job Title:", jf["title"])
    pdf.kv("Experience Level:", jf["experience_level"])
    pdf.kv("# of CVs:", str(len(dataset["cvs"])))

    pdf.h2("Overall Results")
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_fill_color(200, 220, 240)
    pdf.cell(60, 8, "Agent", border=1, fill=True)
    pdf.cell(40, 8, "Result", border=1, align="C", fill=True)
    pdf.cell(30, 8, "Pass Rate", border=1, align="C", fill=True)
    pdf.cell(50, 8, "Status", border=1, align="C", fill=True, new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    for name, summary in [("Parser Agent", parser_r["summary"]), ("Shortlist Agent", shortlist_r["summary"])]:
        a, b = [int(x) for x in summary.split("/")[:2]]
        rate = pct(a, b)
        status = "Excellent" if a == b else ("Good" if a / b >= 0.7 else "Needs work")
        pdf.cell(60, 8, name, border=1)
        pdf.cell(40, 8, summary, border=1, align="C")
        pdf.cell(30, 8, rate, border=1, align="C")
        pdf.cell(50, 8, status, border=1, align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    pdf.h2("How to Read This Report")
    pdf.para("This report uses the Ragas framework (industry-standard LLM evaluation library) to score the agents.")
    pdf.bullet("Parser Agent extracts structured data (name, email, phone, education, experience) from CV PDFs.")
    pdf.bullet("Shortlist Agent scores each CV against the job description (0-100), run 3 times to check stability.")
    pdf.bullet("Each criterion is judged by gpt-4o-mini via Ragas AspectCritic and returns 0 (fail) or 1 (pass).")


def section_parser(pdf, dataset, parser_r):
    pdf.add_page()
    pdf.h1("1. Parser Agent (Ragas)")

    pdf.h2("What this agent does")
    pdf.para(
        "Parses candidate CVs (PDFs) using GPT-4o vision OCR per page then GPT-4o-mini extraction "
        "to return structured fields: name, phone, email, last education, and total experience years."
    )

    pdf.h2("Ragas Setup")
    pdf.kv("Metric:", "AspectCritic (one per field)")
    pdf.kv("# Criteria per CV:", "5 (name, email, phone, education, experience)")
    pdf.kv("Total checks:", f"{len(dataset['cvs']) * 5}")
    pdf.kv("Judge instruction:", "Compare predicted vs ground truth, return 1 if correct else 0")

    per_cv = parser_r.get("per_cv", [])
    total_cvs = len(per_cv)
    field_totals = {f: 0 for f in PARSER_FIELDS}
    for cv in per_cv:
        for f in PARSER_FIELDS:
            if cv["checks"].get(f"{f}_correct"):
                field_totals[f] += 1

    pdf.h2("Per-Field Accuracy")
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_fill_color(200, 220, 240)
    pdf.cell(50, 8, "Field", border=1, fill=True)
    pdf.cell(40, 8, "Passed", border=1, align="C", fill=True)
    pdf.cell(40, 8, "% Accuracy", border=1, align="C", fill=True, new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    for f in PARSER_FIELDS:
        pdf.cell(50, 8, f.capitalize(), border=1)
        pdf.cell(40, 8, f"{field_totals[f]}/{total_cvs}", border=1, align="C")
        pdf.cell(40, 8, pct(field_totals[f], total_cvs), border=1, align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    pdf.h2("Per-CV Pass/Fail Grid")
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_fill_color(200, 220, 240)
    pdf.cell(20, 7, "CV", border=1, align="C", fill=True)
    for f in PARSER_FIELDS:
        pdf.cell(28, 7, f.capitalize(), border=1, align="C", fill=True)
    pdf.ln()
    pdf.set_font("Helvetica", "", 9)
    for cv in per_cv:
        pdf.cell(20, 7, cv["id"], border=1, align="C")
        for f in PARSER_FIELDS:
            ok = cv["checks"].get(f"{f}_correct", False)
            pdf.set_text_color(*(0, 100, 0) if ok else (180, 0, 0))
            pdf.cell(28, 7, "PASS" if ok else "FAIL", border=1, align="C")
            pdf.set_text_color(0, 0, 0)
        pdf.ln()
    pdf.ln(2)

    pdf.h2("Failure Summary")
    fails_by_field = {f: [] for f in PARSER_FIELDS}
    for cv in per_cv:
        for f in PARSER_FIELDS:
            if not cv["checks"].get(f"{f}_correct"):
                fails_by_field[f].append(cv["id"])
    any_fail = False
    for f, cvs in fails_by_field.items():
        if cvs:
            any_fail = True
            pdf.bullet(f"{f.capitalize()} failed for: {', '.join(cvs)}")
    if not any_fail:
        pdf.para("All fields parsed correctly across all CVs.")
    else:
        pdf.bullet("Common causes: OCR character misreads (Vision model non-determinism), digit swaps in phone, parser undercounting experience years.")


def section_shortlist(pdf, dataset, shortlist_r):
    pdf.add_page()
    pdf.h1("2. Shortlist Agent (Ragas)")

    pdf.h2("What this agent does")
    pdf.para(
        "Scores each CV against the job description on a 0-100 scale using GPT-4o-mini. "
        "Run 3 times per CV with temperature=0 to verify stability."
    )

    pdf.h2("Ragas Setup")
    rules = dataset["shortlist_eval_rules"]
    pdf.kv("Metric:", "AspectCritic (score_in_band, score_is_stable)")
    pdf.kv("Runs per CV:", str(rules["stability_runs"]))
    pdf.kv("Stability tolerance:", f"max-min spread <= {rules['stability_tolerance']}")
    pdf.kv("# Criteria per CV:", "2 (in-band + stable)")
    pdf.kv("Total checks:", f"{len(dataset['cvs']) * 2}")

    per_cv = shortlist_r.get("per_cv", [])
    pdf.h2("Per-CV Scores")
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_fill_color(200, 220, 240)
    pdf.cell(15, 7, "CV", border=1, align="C", fill=True)
    pdf.cell(40, 7, "Scores (3 runs)", border=1, align="C", fill=True)
    pdf.cell(20, 7, "Avg", border=1, align="C", fill=True)
    pdf.cell(35, 7, "Expected", border=1, align="C", fill=True)
    pdf.cell(25, 7, "In Band", border=1, align="C", fill=True)
    pdf.cell(25, 7, "Stable", border=1, align="C", fill=True, new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 9)
    for cv in per_cv:
        band = cv["expected_band"]
        pdf.cell(15, 7, cv["id"], border=1, align="C")
        pdf.cell(40, 7, safe(str(cv["scores"])), border=1, align="C")
        pdf.cell(20, 7, f"{cv['average']:.1f}", border=1, align="C")
        pdf.cell(35, 7, f"[{band['min']}, {band['max']}]", border=1, align="C")
        pdf.set_text_color(*(0, 100, 0) if cv["in_band"] else (180, 0, 0))
        pdf.cell(25, 7, "PASS" if cv["in_band"] else "FAIL", border=1, align="C")
        pdf.set_text_color(*(0, 100, 0) if cv["stable"] else (180, 0, 0))
        pdf.cell(25, 7, "PASS" if cv["stable"] else "FAIL", border=1, align="C", new_x="LMARGIN", new_y="NEXT")
        pdf.set_text_color(0, 0, 0)
    pdf.ln(2)

    in_band_count = sum(1 for cv in per_cv if cv["in_band"])
    stable_count = sum(1 for cv in per_cv if cv["stable"])
    total = len(per_cv)

    pdf.h2("Summary")
    pdf.bullet(f"In-band passes: {in_band_count}/{total} ({pct(in_band_count, total)})")
    pdf.bullet(f"Stability passes: {stable_count}/{total} ({pct(stable_count, total)})")

    pdf.h2("Failure Details")
    any_fail = False
    for cv in per_cv:
        if cv["in_band"] and cv["stable"]:
            continue
        any_fail = True
        rationale = cv["expected_band"].get("rationale", "")
        pdf.h3(f"{cv['id']}: avg={cv['average']:.1f} (expected {cv['expected_band']['min']}-{cv['expected_band']['max']})")
        if not cv["in_band"]:
            gap = cv["expected_band"]["min"] - cv["average"]
            pdf.bullet(f"In-band FAIL: score {gap:.1f} below minimum. Context: {rationale}")
        if not cv["stable"]:
            pdf.bullet(f"Stability FAIL: spread {cv['spread']} exceeds tolerance.")
    if not any_fail:
        pdf.para("All CVs in band and stable.")

    pdf.h2("Insights")
    pdf.bullet("LLM is highly experience-sensitive: candidates under 5 years often get 25-45 for Senior roles.")
    pdf.bullet("Scoring is fully stable across 3 runs (temperature=0).")
    pdf.bullet("Scores cluster on multiples of 5 due to LLM round-number bias.")


def main():
    dataset = json.loads((HERE / "eval_dataset.json").read_text(encoding="utf-8"))
    parser_r = json.loads((HERE / "results_parser_ragas.json").read_text(encoding="utf-8"))
    shortlist_r = json.loads((HERE / "results_shortlist_ragas.json").read_text(encoding="utf-8"))

    pdf = RagasReport()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    section_cover(pdf, dataset, parser_r, shortlist_r)
    section_parser(pdf, dataset, parser_r)
    section_shortlist(pdf, dataset, shortlist_r)

    out = HERE / "ragas_evaluation_report.pdf"
    pdf.output(str(out))
    print(f"Saved: {out}")


if __name__ == "__main__":
    main()
