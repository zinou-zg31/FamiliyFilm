"""Sample frames with OpenCV and classify them with pretrained Hugging Face image models."""
import cv2
from PIL import Image
from .common import Finding, ModuleResult, env

# Maps label keywords from a model to our categories.
LABEL_MAP = {"nsfw": "sexual", "porn": "sexual", "nude": "sexual", "sexy": "sexual",
             "violen": "violence", "fight": "violence", "weapon": "violence", "gun": "violence",
             "blood": "violence", "gore": "horror", "horror": "horror", "scary": "horror"}

def _load(name):
    from transformers import pipeline
    return pipeline("image-classification", model=name)

def _map(label):
    l = label.lower()
    for k, cat in LABEL_MAP.items():
        if k in l: return cat
    return None

def analyze_video(path: str, progress=lambda p, m: None) -> ModuleResult:
    models, notes = {}, []
    for key in ("NSFW_MODEL", "VIOLENCE_MODEL"):
        name = env(key, "Falconsai/nsfw_image_detection" if key == "NSFW_MODEL" else "")
        if not name:
            notes.append(f"{key} not configured: violence/weapons/gore/horror NOT analyzed visually.")
            continue
        try: models[name] = _load(name)
        except Exception as e: notes.append(f"Could not load {name}: {e}")
    if not models:
        return ModuleResult("video", False, notes=notes + ["No visual model available."])

    cap = cv2.VideoCapture(path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 25
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    step = max(1, int(fps * float(env("FRAME_INTERVAL_SEC", "3"))))
    res = ModuleResult("video", True, notes=notes)
    covered, analyzed = set(), 0
    sampled = max(1, total // step)
    for idx in range(0, total, step):
        cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        ok, frame = cap.read()
        if not ok: continue
        img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        ts = idx / fps
        for name, pipe in models.items():
            for p in pipe(img):
                cat = _map(p["label"])
                if cat:
                    covered.add(cat)
                    if p["score"] >= 0.6:
                        sev = 3 if p["score"] > 0.9 else 2 if p["score"] > 0.75 else 1
                        res.findings.append(Finding(cat, p["score"], sev, ts, p["label"]))
        analyzed += 1
        progress(analyzed / sampled, f"Analyzed frame at {int(ts)}s")
    cap.release()
    res.coverage = analyzed / sampled
    res.categories_covered = sorted(covered)
    res.notes.append(f"Sampled 1 frame every {step/fps:.1f}s; short scenes can be missed.")
    return res
