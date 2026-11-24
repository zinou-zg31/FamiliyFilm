"""Combine module results into scores and a configurable verdict."""
from .common import CATEGORIES

# Audience profile -> (weight multiplier, partial threshold, not-friendly threshold) on the 0-100 problem score.
PROFILES = {"under7": (1.5, 5, 15), "7to12": (1.0, 10, 30), "teen": (0.6, 20, 50), "adult": (0.3, 30, 60)}
TOLERANCE = {"strict": 0.7, "normal": 1.0, "relaxed": 1.4}  # divides the score thresholds

def classify(results: list[dict], duration_s: float | None, age_group="7to12", tolerance="normal") -> dict:
    weight, partial_t, bad_t = PROFILES[age_group]
    scale = TOLERANCE[tolerance]
    scores, confidence, analyzed = {}, {}, {}
    for cat in CATEGORIES:
        mods = [m for m in results if m["available"] and cat in m["categories_covered"]]
        if not mods:
            scores[cat] = confidence[cat] = None; analyzed[cat] = False; continue
        analyzed[cat] = True
        findings = [f for m in mods for f in m["findings"] if f["category"] == cat]
        # Estimated share: distinct 60-second windows containing a finding, weighted by severity.
        windows = {}
        for f in findings:
            w = int((f["timestamp"] or 0) // 60)
            windows[w] = max(windows.get(w, 0), f["severity"])
        total_w = max(1, int((duration_s or max([f["timestamp"] or 0 for m in results for f in m["findings"]] + [60])) // 60) + 1)
        scores[cat] = round(min(100, sum(windows.values()) / (3 * total_w) * 100 * weight * 3), 1)
        confidence[cat] = round(sum(f["confidence"] for f in findings) / len(findings), 2) if findings else None
    known = [s for s in scores.values() if s is not None]
    worst = max(known) if known else 0
    suitability = round(max(0, 100 - (sum(known) / len(known) if known else 0) * 0.5 - worst * 0.5), 1)
    coverage = sum(analyzed.values()) / len(CATEGORIES)
    reasons = [f"{c}: {scores[c]}% estimated problematic content" for c in CATEGORIES if scores[c]]
    missing = [c for c, ok in analyzed.items() if not ok]
    if not known:
        label = "INCONCLUSIVE"
    elif worst >= bad_t / scale:
        label = "NOT FAMILY FRIENDLY"
    elif worst >= partial_t / scale:
        label = "PARTIALLY FAMILY FRIENDLY"
    else:
        label = "FAMILY FRIENDLY" if not missing else "NO FLAGS FOUND (INCOMPLETE ANALYSIS)"
    if missing:
        reasons.append("Not analyzed (no model/data): " + ", ".join(missing))
    scenes = sorted([{**f, "module": m["module"]} for m in results for f in m["findings"] if f["severity"] >= 2],
                    key=lambda f: f["timestamp"] or 0)
    return {"label": label, "suitability_score": suitability, "category_scores": scores,
            "category_confidence": confidence, "categories_analyzed": analyzed,
            "analysis_coverage": round(coverage, 2), "reasons": reasons, "scenes": scenes,
            "settings": {"age_group": age_group, "tolerance": tolerance}}
