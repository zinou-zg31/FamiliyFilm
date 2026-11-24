"""Build a downloadable PDF report."""
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

def build_pdf(path: str, title: str, official_rating: str | None, verdict: dict):
    c = canvas.Canvas(path, pagesize=A4); y = 800
    def line(t, size=11):
        nonlocal y
        c.setFont("Helvetica", size); c.drawString(50, y, t[:95]); y -= size + 6
        if y < 60: c.showPage(); y = 800
    line(f"FamilyCheck AI report: {title}", 16)
    line(f"AI assessment: {verdict['label']}  (suitability {verdict['suitability_score']}/100)")
    line(f"Official rating (separate, not AI): {official_rating or 'unknown'}")
    line(f"Analysis coverage: {int(verdict['analysis_coverage']*100)}% of categories")
    line("Category scores (estimated share) / model confidence:", 12)
    for k, v in verdict["category_scores"].items():
        conf = verdict["category_confidence"][k]
        line(f" - {k}: {'not analyzed' if v is None else f'{v}%'} / confidence {conf if conf is not None else 'n/a'}")
    line("Reasons:", 12)
    for r in verdict["reasons"]: line(f" - {r}")
    line("Flagged scenes:", 12)
    for s in verdict["scenes"][:60]:
        t = int(s["timestamp"] or 0); line(f" {t//60:02d}:{t%60:02d} {s['category']} (sev {s['severity']}, conf {s['confidence']:.2f})")
    c.save()
