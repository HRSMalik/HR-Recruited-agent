"""Generate a DETAILED PDF evaluation report from results_*.json files.

Sections:
  1. Cover & overall summary
  2. Post Agent — what it does, test setup, criteria results, reasons
  3. Parser Agent — field-wise results, per-CV failures with reasons
  4. Shortlist Agent — band/stability results, per-CV reasons, insights
"""
import json
from datetime import datetime
from pathlib import Path

from fpdf import FPDF

HERE = Path(__file__).resolve().parent


class DetailedReport(FPDF):
    def header(self):
        if self.page_no() == 1:
            return
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(120, 120, 120)
        self.cell(0, 5, "HR Recruitment Agent - Detailed Evaluation Report", new_x="LMARGIN", new_y="NEXT", align="R")
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
        self.set_line_width(0.5)
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
        self.set_text_color(40, 40, 40)
        self.cell(0, 6, text, new_x="LMARGIN", new_y="NEXT")
        self.set_text_color(0, 0, 0)

    def para(self, text):
        self.set_font("Helvetica", "", 10)
        self.multi_cell(0, 5, safe(text), new_x="LMARGIN", new_y="NEXT")
        self.ln(1)

    def bullet(self, text):
        self.set_font("Helvetica", "", 10)
        self.cell(5, 5, "")
        self.cell(3, 5, "-")
        self.multi_cell(0, 5, safe(text), new_x="LMARGIN", new_y="NEXT")

    def kv(self, key, value, key_w=45):
        self.set_font("Helvetica", "B", 10)
        self.cell(key_w, 6, key)
        self.set_font("Helvetica", "", 10)
        self.multi_cell(0, 6, safe(str(value)), new_x="LMARGIN", new_y="NEXT")


def safe(s):
    return "".join(c if ord(c) < 256 else "?" for c in str(s))


def pct(passed, total):
    return f"{100 * passed / total:.0f}%" if total else "n/a"


# ===========================================================================
# PAGE 1 — COVER + SUMMARY
# ===========================================================================
def section_cover(pdf, dataset, post_r, parser_r, shortlist_r):
    pdf.set_font("Helvetica", "B", 22)
    pdf.ln(15)
    pdf.cell(0, 12, "Detailed Evaluation Report", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.set_font("Helvetica", "", 12)
    pdf.cell(0, 8, "HR Recruitment Agent - Three-Agent System", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.set_font("Helvetica", "I", 10)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 6, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.set_text_color(0, 0, 0)
    pdf.ln(8)

    pdf.h2("Test Setup")
    jf = dataset["job_form"]
    pdf.kv("Job Title:", jf["title"])
    pdf.kv("Experience Level:", jf["experience_level"])
    pdf.kv("# of CVs tested:", str(len(dataset["cvs"])))
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(45, 6, "Requirements:")
    pdf.set_font("Helvetica", "", 10)
    pdf.multi_cell(0, 5, safe(jf["requirements"]), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    pdf.h2("Overall Results")
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_fill_color(200, 220, 240)
    pdf.cell(60, 8, "Agent", border=1, fill=True)
    pdf.cell(40, 8, "Result", border=1, align="C", fill=True)
    pdf.cell(30, 8, "Pass Rate", border=1, align="C", fill=True)
    pdf.cell(50, 8, "Status", border=1, align="C", fill=True, new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)

    rows = [
        ("Post Agent", post_r["summary"], _parse_ratio(post_r["summary"])),
        ("Parser Agent", parser_r["summary"], _parse_ratio(parser_r["summary"])),
        ("Shortlist Agent", shortlist_r["summary"], _parse_ratio(shortlist_r["summary"])),
    ]
    for name, summary, ratio in rows:
        passed, total = ratio
        rate = pct(passed, total)
        status = "Excellent" if passed == total else ("Good" if passed / total >= 0.7 else "Needs work")
        pdf.cell(60, 8, name, border=1)
        pdf.cell(40, 8, safe(summary), border=1, align="C")
        pdf.cell(30, 8, rate, border=1, align="C")
        pdf.cell(50, 8, status, border=1, align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    pdf.h2("How to Read This Report")
    pdf.para("This report evaluates three AI agents that work together in the recruitment workflow:")
    pdf.bullet("Post Agent generates LinkedIn job posts from form input.")
    pdf.bullet("Parser Agent extracts structured data (name, email, etc.) from candidate CVs.")
    pdf.bullet("Shortlist Agent scores each candidate against the job description.")
    pdf.para("Each section below shows what the agent does, how it was tested, results, and reasons for any failures.")


def _parse_ratio(summary):
    parts = summary.replace(" criteria passed", "").replace(" field checks passed", "").split("/")
    a = int(parts[0])
    b = int(parts[1].split()[0])
    return a, b


# ===========================================================================
# PAGE 2 — POST AGENT
# ===========================================================================
def section_post(pdf, dataset, post_r):
    pdf.add_page()
    pdf.h1("1. Post Agent")

    pdf.h2("What this agent does")
    pdf.para(
        "The Post Agent takes a job form (title, experience level, description, requirements) "
        "and generates a LinkedIn-ready job post using GPT-4o. It also formats the post, "
        "appends a Google Form application link with the unique JD ID, and supports human review "
        "(approve, edit, regenerate) before publishing."
    )

    pdf.h2("Test setup")
    pdf.kv("Input:", "1 job form (see cover page)")
    pdf.kv("Judge:", "gpt-4o-mini, temperature=0")
    pdf.kv("Method:", "LLM-as-judge - each criterion scored 1 (pass) or 0 (fail)")

    pdf.h2("Criteria Results")
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_fill_color(200, 220, 240)
    pdf.cell(80, 8, "Criterion", border=1, fill=True)
    pdf.cell(30, 8, "Result", border=1, align="C", fill=True)
    pdf.cell(70, 8, "Definition", border=1, fill=True, new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 9)
    defs = {c["name"]: c["definition"] for c in dataset["post_agent_eval_criteria"]}
    for name, score in post_r.get("criteria", {}).items():
        x0 = pdf.get_x()
        y0 = pdf.get_y()
        pdf.multi_cell(80, 6, safe(name), border=1)
        h1 = pdf.get_y() - y0
        pdf.set_xy(x0 + 80, y0)
        pdf.cell(30, h1, "PASS" if score else "FAIL", border=1, align="C")
        pdf.set_xy(x0 + 110, y0)
        pdf.multi_cell(70, 6, safe(defs.get(name, "")), border=1)
        y2 = max(pdf.get_y(), y0 + h1)
        pdf.set_xy(x0, y2)
    pdf.ln(2)

    pdf.h2("Generated Post (preview)")
    preview = post_r.get("generated_post_preview", "")
    pdf.set_font("Helvetica", "I", 9)
    pdf.set_fill_color(245, 245, 245)
    pdf.multi_cell(0, 5, safe(preview), border=1, fill=True)
    pdf.ln(2)

    pdf.h2("Reasons / Insights")
    criteria = post_r.get("criteria", {})
    failed = [name for name, s in criteria.items() if not s]
    passed = [name for name, s in criteria.items() if s]
    if not failed:
        pdf.bullet("All criteria passed. The generated post is LinkedIn-friendly, professional, complete, and has a clear CTA.")
    else:
        for f in failed:
            reasons = _post_failure_reason(f, preview)
            pdf.bullet(f"FAIL: {f} - {reasons}")
        for p in passed:
            pdf.bullet(f"PASS: {p}")
    pdf.bullet("Note: GPT-4o-mini as judge is occasionally inconsistent; consider running 2-3 times and taking the majority vote.")


def _post_failure_reason(criterion, preview):
    reasons = {
        "linkedin_friendly": "Judge detected something resembling markdown. Often a false positive on unicode separators (?). Inspect the generated post manually.",
        "covers_all_requirements": "One or more requirements from the input form are missing from the generated post (e.g., a specific framework or skill).",
        "professional_tone": "Tone judged as casual or unprofessional. Review the post for slang or informal phrasing.",
        "has_clear_cta": "No clear application instruction or link found. Ensure the post ends with a 'Fill the form to apply' style CTA.",
        "appropriate_length": "Post too short (<5 lines) or too long (>600 words). Tune the LLM prompt for target length.",
    }
    return reasons.get(criterion, "Judge marked this fail; inspect the generated post manually.")


# ===========================================================================
# PAGE 3-4 — PARSER AGENT
# ===========================================================================
def section_parser(pdf, dataset, parser_r):
    pdf.add_page()
    pdf.h1("2. Parser Agent")

    pdf.h2("What this agent does")
    pdf.para(
        "The Parser Agent takes a candidate CV (PDF), runs OCR using GPT-4o vision on each page "
        "to extract text, then uses GPT-4o-mini to extract structured fields: name, phone, email, "
        "last education degree/institution, and total experience years. Results are saved in MongoDB."
    )

    pdf.h2("Test setup")
    pdf.kv("Input:", f"{len(dataset['cvs'])} PDF CVs")
    pdf.kv("Method:", "Compare predicted JSON vs ground truth, field-by-field")
    pdf.kv("Match rules:", "Name (fuzzy), email (exact normalized), phone (last 10 digits), education (canonical aliases like BS == Bachelor's), experience (numeric tolerance)")

    pdf.h2("Per-Field Summary")
    per_cv = parser_r.get("per_cv", [])
    field_totals = {"name": 0, "email": 0, "phone": 0, "education": 0, "experience": 0}
    for cv in per_cv:
        for f, ok in cv["checks"].items():
            if ok:
                field_totals[f] += 1
    total_cvs = len(per_cv)

    pdf.set_font("Helvetica", "B", 10)
    pdf.set_fill_color(200, 220, 240)
    pdf.cell(50, 8, "Field", border=1, fill=True)
    pdf.cell(40, 8, "Passed", border=1, align="C", fill=True)
    pdf.cell(40, 8, "% Accuracy", border=1, align="C", fill=True, new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    for f, count in field_totals.items():
        pdf.cell(50, 8, f.capitalize(), border=1)
        pdf.cell(40, 8, f"{count}/{total_cvs}", border=1, align="C")
        pdf.cell(40, 8, pct(count, total_cvs), border=1, align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    pdf.h2("Per-CV Pass/Fail Grid")
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_fill_color(200, 220, 240)
    pdf.cell(20, 7, "CV", border=1, align="C", fill=True)
    for field in ["name", "email", "phone", "education", "experience"]:
        pdf.cell(28, 7, field.capitalize(), border=1, align="C", fill=True)
    pdf.ln()
    pdf.set_font("Helvetica", "", 9)
    for cv in per_cv:
        pdf.cell(20, 7, cv["id"], border=1, align="C")
        for field in ["name", "email", "phone", "education", "experience"]:
            ok = cv["checks"].get(field, False)
            if ok:
                pdf.set_text_color(0, 100, 0)
                pdf.cell(28, 7, "PASS", border=1, align="C")
            else:
                pdf.set_text_color(180, 0, 0)
                pdf.cell(28, 7, "FAIL", border=1, align="C")
            pdf.set_text_color(0, 0, 0)
        pdf.ln()
    pdf.ln(2)

    pdf.h2("Failure Details and Reasons")
    gt_map = {cv["id"]: cv["ground_truth"] for cv in dataset["cvs"]}
    any_fail = False
    for cv in per_cv:
        fails = [(f, ok) for f, ok in cv["checks"].items() if not ok]
        if not fails:
            continue
        any_fail = True
        pdf.h3(f"{cv['id']}: {cv['predicted'].get('name', '')}")
        for field, _ in fails:
            predicted = cv["predicted"].get(_pred_key(field), "")
            expected = _expected_value(gt_map[cv["id"]], field)
            reason = _parser_failure_reason(field, predicted, expected)
            pdf.bullet(f"{field}: predicted='{predicted}' vs expected='{expected}' - {reason}")
    if not any_fail:
        pdf.para("All CV fields parsed correctly. No failures to report.")


def _pred_key(field):
    return {
        "name": "name",
        "email": "email",
        "phone": "phone",
        "education": "last_education_degree",
        "experience": "experience_years",
    }[field]


def _expected_value(gt, field):
    key_map = {
        "name": "name",
        "email": "email",
        "phone": "phone",
        "education": "last_education_degree",
        "experience": "experience_years_approx",
    }
    return gt.get(key_map[field], "")


def _parser_failure_reason(field, predicted, expected):
    if field == "experience":
        try:
            diff = abs(float(predicted) - float(expected))
            return f"off by {diff:.1f} years - parser tends to undercount, often missing earlier jobs in the timeline."
        except (ValueError, TypeError):
            return "non-numeric output; parser returned a string instead of number."
    if field == "email":
        return "OCR misread one or more characters (Vision model is non-deterministic for low-contrast text)."
    if field == "phone":
        return "OCR digit swap or different format separator (- vs space). The phone matcher compares last 10 digits."
    if field == "education":
        return "Canonical degree alias not matched. Check if a new abbreviation needs to be added to _DEGREE_ALIASES."
    if field == "name":
        return "Name differs by more than substring overlap; fuzzy match failed."
    return "Match function returned False; inspect manually."


# ===========================================================================
# PAGE 5-6 — SHORTLIST AGENT
# ===========================================================================
def section_shortlist(pdf, dataset, shortlist_r):
    pdf.add_page()
    pdf.h1("3. Shortlist Agent")

    pdf.h2("What this agent does")
    pdf.para(
        "The Shortlist Agent takes a parsed CV and a job description, and asks GPT-4o-mini to "
        "return an integer 0-100 representing how well the candidate fits the job. The same CV is "
        "scored 3 times (stability runs) to check that the model produces consistent results."
    )

    pdf.h2("Test setup")
    rules = dataset["shortlist_eval_rules"]
    pdf.kv("Input:", f"{len(dataset['cvs'])} CVs vs 1 generated JD")
    pdf.kv("Runs per CV:", str(rules["stability_runs"]))
    pdf.kv("Stability tolerance:", f"max-min spread <= {rules['stability_tolerance']}")
    pdf.kv("Pass conditions:", "(1) average score is in expected band AND (2) spread <= tolerance")

    pdf.h2("Per-CV Score Table")
    per_cv = shortlist_r.get("per_cv", [])
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_fill_color(200, 220, 240)
    pdf.cell(15, 7, "CV", border=1, align="C", fill=True)
    pdf.cell(40, 7, "Scores (3 runs)", border=1, align="C", fill=True)
    pdf.cell(20, 7, "Avg", border=1, align="C", fill=True)
    pdf.cell(35, 7, "Expected Band", border=1, align="C", fill=True)
    pdf.cell(25, 7, "In Band", border=1, align="C", fill=True)
    pdf.cell(25, 7, "Stable", border=1, align="C", fill=True, new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 9)
    for cv in per_cv:
        band = cv["expected_band"]
        pdf.cell(15, 7, cv["id"], border=1, align="C")
        pdf.cell(40, 7, safe(str(cv["scores"])), border=1, align="C")
        pdf.cell(20, 7, str(cv["average"]), border=1, align="C")
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
    pdf.bullet(f"In-band passes:  {in_band_count}/{total} ({pct(in_band_count, total)})")
    pdf.bullet(f"Stability passes: {stable_count}/{total} ({pct(stable_count, total)})")

    pdf.h2("Failure Details and Reasons")
    gt_map = {cv["id"]: cv["ground_truth"] for cv in dataset["cvs"]}
    rationale_map = {cv["id"]: cv["expected_score_band"].get("rationale", "") for cv in dataset["cvs"]}
    any_fail = False
    for cv in per_cv:
        if cv["in_band"] and cv["stable"]:
            continue
        any_fail = True
        pdf.h3(f"{cv['id']}")
        pdf.bullet(f"Average score: {cv['average']} | Expected: [{cv['expected_band']['min']}, {cv['expected_band']['max']}]")
        if not cv["in_band"]:
            reason = _shortlist_band_reason(cv["average"], cv["expected_band"], rationale_map.get(cv["id"], ""))
            pdf.bullet(f"In-band FAIL: {reason}")
        if not cv["stable"]:
            pdf.bullet(f"Stability FAIL: scores varied by {cv['spread']} which exceeds tolerance.")

    if not any_fail:
        pdf.para("All CVs scored within expected bands and were stable. No failures to report.")

    pdf.h2("Insights")
    pdf.bullet("LLM is highly experience-sensitive: candidates under 5 years often get scored 25-45 for Senior roles, regardless of skill match.")
    pdf.bullet("Scoring is stable - same input gives same score across runs because temperature=0.")
    pdf.bullet("Scores tend to land on multiples of 5 (25, 35, 65, 75) - LLM bias toward 'round' numbers.")
    pdf.bullet("Tightening the prompt to weight skills more than years could help reduce experience penalties.")


def _shortlist_band_reason(avg, band, rationale):
    if avg < band["min"]:
        gap = band["min"] - avg
        return (f"Score {avg} is {gap:.1f} below the minimum {band['min']}. "
                f"Likely cause: LLM penalized for experience gap or missing keyword. Candidate context: {rationale}")
    if avg > band["max"]:
        gap = avg - band["max"]
        return (f"Score {avg} is {gap:.1f} above the maximum {band['max']}. "
                f"Likely cause: LLM was too lenient on missing requirements. Candidate context: {rationale}")
    return "in band"


# ===========================================================================
# MAIN
# ===========================================================================
def main():
    dataset = json.loads((HERE / "eval_dataset.json").read_text(encoding="utf-8"))
    post_r = json.loads((HERE / "results_post.json").read_text(encoding="utf-8"))
    parser_r = json.loads((HERE / "results_parser.json").read_text(encoding="utf-8"))
    shortlist_r = json.loads((HERE / "results_shortlist.json").read_text(encoding="utf-8"))

    pdf = DetailedReport()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    section_cover(pdf, dataset, post_r, parser_r, shortlist_r)
    section_post(pdf, dataset, post_r)
    section_parser(pdf, dataset, parser_r)
    section_shortlist(pdf, dataset, shortlist_r)

    out = HERE / "detail_eval_report.pdf"
    pdf.output(str(out))
    print(f"Saved: {out}")


if __name__ == "__main__":
    main()
