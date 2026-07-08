"""Generate a PDF evaluation report from results_*.json files."""
import json
from datetime import datetime
from pathlib import Path

from fpdf import FPDF

HERE = Path(__file__).resolve().parent


class ReportPDF(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 14)
        self.cell(0, 8, "HR Recruitment Agent - Evaluation Report", new_x="LMARGIN", new_y="NEXT", align="C")
        self.set_font("Helvetica", "", 9)
        self.cell(0, 5, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", new_x="LMARGIN", new_y="NEXT", align="C")
        self.ln(3)

    def footer(self):
        self.set_y(-12)
        self.set_font("Helvetica", "I", 8)
        self.cell(0, 8, f"Page {self.page_no()}", align="C")

    def h2(self, text):
        self.ln(3)
        self.set_font("Helvetica", "B", 12)
        self.set_fill_color(230, 230, 230)
        self.cell(0, 8, text, new_x="LMARGIN", new_y="NEXT", fill=True)
        self.ln(2)

    def kv(self, key, value, key_w=50):
        self.set_font("Helvetica", "B", 10)
        self.cell(key_w, 6, key)
        self.set_font("Helvetica", "", 10)
        self.multi_cell(0, 6, str(value), new_x="LMARGIN", new_y="NEXT")

    def line_break(self, h=2):
        self.ln(h)


def safe(s):
    """Strip unicode chars that the default fpdf font can't render."""
    return "".join(c if ord(c) < 256 else "?" for c in str(s))


def add_post_section(pdf: ReportPDF, results: dict):
    pdf.h2("1. Post Agent Evaluation")
    pdf.kv("Summary:", results.get("summary", "n/a"))
    pdf.line_break()

    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(80, 7, "Criterion", border=1)
    pdf.cell(30, 7, "Result", border=1, align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    for name, score in results.get("criteria", {}).items():
        pdf.cell(80, 7, safe(name), border=1)
        pdf.cell(30, 7, "PASS" if score else "FAIL", border=1, align="C",
                 new_x="LMARGIN", new_y="NEXT")
    pdf.line_break()
    pdf.set_font("Helvetica", "I", 9)
    pdf.multi_cell(0, 5, "Generated post (preview): " + safe(results.get("generated_post_preview", "")))


def add_parser_section(pdf: ReportPDF, results: dict):
    pdf.h2("2. Parser Agent Evaluation")
    pdf.kv("Summary:", f"{results.get('summary', 'n/a')} field checks passed")
    pdf.line_break()

    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(20, 7, "CV", border=1, align="C")
    for field in ["name", "email", "phone", "education", "experience"]:
        pdf.cell(28, 7, field.capitalize(), border=1, align="C")
    pdf.ln()
    pdf.set_font("Helvetica", "", 10)
    for cv in results.get("per_cv", []):
        pdf.cell(20, 7, safe(cv["id"]), border=1, align="C")
        for field in ["name", "email", "phone", "education", "experience"]:
            ok = cv["checks"].get(field, False)
            pdf.cell(28, 7, "PASS" if ok else "FAIL", border=1, align="C")
        pdf.ln()


def add_shortlist_section(pdf: ReportPDF, results: dict):
    pdf.h2("3. Shortlist Agent Evaluation")
    pdf.kv("Summary:", f"{results.get('summary', 'n/a')} checks passed (band + stability)")
    pdf.line_break()

    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(20, 7, "CV", border=1, align="C")
    pdf.cell(35, 7, "Expected", border=1, align="C")
    pdf.cell(25, 7, "Avg Score", border=1, align="C")
    pdf.cell(25, 7, "In Band", border=1, align="C")
    pdf.cell(25, 7, "Stable", border=1, align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    for cv in results.get("per_cv", []):
        band = cv["expected_band"]
        pdf.cell(20, 7, safe(cv["id"]), border=1, align="C")
        pdf.cell(35, 7, f"[{band['min']}, {band['max']}]", border=1, align="C")
        pdf.cell(25, 7, str(cv["average"]), border=1, align="C")
        pdf.cell(25, 7, "PASS" if cv["in_band"] else "FAIL", border=1, align="C")
        pdf.cell(25, 7, "PASS" if cv["stable"] else "FAIL", border=1, align="C",
                 new_x="LMARGIN", new_y="NEXT")


def add_overview(pdf: ReportPDF, dataset: dict, post_r: dict, parser_r: dict, shortlist_r: dict):
    pdf.h2("Test Job Description")
    jf = dataset["job_form"]
    pdf.kv("Title:", safe(jf["title"]))
    pdf.kv("Experience level:", safe(jf["experience_level"]))
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(50, 6, "Requirements:")
    pdf.set_font("Helvetica", "", 10)
    pdf.multi_cell(0, 5, safe(jf["requirements"]), new_x="LMARGIN", new_y="NEXT")

    pdf.h2("Overall Summary")
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(50, 7, "Agent", border=1)
    pdf.cell(50, 7, "Result", border=1, align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    for label, summary in [
        ("Post Agent", post_r.get("summary", "")),
        ("Parser Agent", parser_r.get("summary", "")),
        ("Shortlist Agent", shortlist_r.get("summary", "")),
    ]:
        pdf.cell(50, 7, label, border=1)
        pdf.cell(50, 7, safe(summary), border=1, align="C", new_x="LMARGIN", new_y="NEXT")


def main():
    dataset = json.loads((HERE / "eval_dataset.json").read_text(encoding="utf-8"))
    post_r = json.loads((HERE / "results_post.json").read_text(encoding="utf-8"))
    parser_r = json.loads((HERE / "results_parser.json").read_text(encoding="utf-8"))
    shortlist_r = json.loads((HERE / "results_shortlist.json").read_text(encoding="utf-8"))

    pdf = ReportPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    add_overview(pdf, dataset, post_r, parser_r, shortlist_r)
    add_post_section(pdf, post_r)
    add_parser_section(pdf, parser_r)
    add_shortlist_section(pdf, shortlist_r)

    out = HERE / "evaluation_report.pdf"
    pdf.output(str(out))
    print(f"Saved: {out}")


if __name__ == "__main__":
    main()
