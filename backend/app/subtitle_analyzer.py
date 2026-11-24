"""Analyze text (subtitles or Whisper transcript). Lexicon rules + optional BERT toxicity model."""
import re
from .common import Finding, ModuleResult, env

# (regex, category, severity). Extend freely; lexicons are a baseline, not the whole system.
LEXICON = [
    (r"\b(fuck\w*|motherfuck\w*)\b", "language", 3),
    (r"\b(shit|bitch|asshole|bastard|dick)\b", "language", 2),
    (r"\b(damn|hell|crap|idiot|stupid)\b", "language", 1),
    (r"\b(cocaine|heroin|meth|weed|marijuana|overdose|joint|high on)\b", "substances", 3),
    (r"\b(beer|whisky|whiskey|vodka|wine|drunk|cigarette|smoking)\b", "substances", 1),
    (r"\b(kill|murder|stab|shoot|gun|blood|dead body)\w*\b", "violence", 2),
    (r"\b(sex|naked|rape|seduce|orgasm|erotic)\w*\b", "sexual", 3),
    (r"\b(scream|nightmare|demon|haunt\w*|monster)\b", "horror", 1),
]
_tox = None

def parse_srt(text: str):
    """Yield (start_seconds, line_text)."""
    for block in re.split(r"\n\s*\n", text.strip()):
        lines = block.strip().splitlines()
        for i, l in enumerate(lines):
            m = re.match(r"(\d+):(\d+):(\d+)[,.](\d+)\s*-->", l)
            if m:
                h, mi, s, ms = map(int, m.groups())
                yield h*3600 + mi*60 + s + ms/1000, " ".join(lines[i+1:])
                break

def _toxicity():
    global _tox
    name = env("TEXT_TOXICITY_MODEL", "unitary/toxic-bert")
    if _tox is None and name:
        try:
            from transformers import pipeline
            _tox = pipeline("text-classification", model=name, top_k=None, truncation=True)
        except Exception:
            _tox = False
    return _tox or None

def analyze_segments(segments, module="subtitles", total_duration=None) -> ModuleResult:
    """segments: iterable of (start_seconds, text)."""
    segments = list(segments)
    res = ModuleResult(module, available=True, coverage=1.0 if segments else 0.0,
                       categories_covered=["language", "substances", "violence", "sexual", "horror"])
    if not segments:
        res.available = False
        res.notes.append("No text to analyze.")
        return res
    tox = _toxicity()
    if not tox:
        res.notes.append("Toxicity model unavailable; using lexicon rules only.")
    for ts, text in segments:
        for pat, cat, sev in LEXICON:
            if re.search(pat, text, re.I):
                res.findings.append(Finding(cat, 0.7, sev, ts, text[:120]))  # lexicon confidence is fixed/heuristic
        if tox:
            try:
                scores = {d["label"]: d["score"] for d in tox(text)[0]}
                for label, cat in [("toxic", "language"), ("insult", "language"),
                                   ("obscene", "language"), ("threat", "violence")]:
                    if scores.get(label, 0) > 0.8:
                        res.findings.append(Finding(cat, scores[label], 2, ts, text[:120]))
            except Exception as e:
                res.notes.append(f"Model error: {e}"); tox = None
    return res

def analyze_srt(srt_text: str) -> ModuleResult:
    return analyze_segments(parse_srt(srt_text), "subtitles")
