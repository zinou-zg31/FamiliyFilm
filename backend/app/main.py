"""FastAPI app: upload, start, progress, results, metadata search, history, PDF."""
import os, uuid, shutil
from dotenv import load_dotenv
load_dotenv()
from fastapi import FastAPI, UploadFile, File, Form, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pathlib import Path
from .db import Session, Analysis
from . import movie_metadata, video_analyzer, audio_analyzer, subtitle_analyzer, classification_engine, report_generator

app = FastAPI(title="FamilyCheck AI")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173"], allow_methods=["*"], allow_headers=["*"])
UPLOADS = "uploads"; os.makedirs(UPLOADS, exist_ok=True)
ALLOWED = {".mp4", ".avi", ".mov"}
MAX_BYTES = 20 * 1024**3

def _update(aid, **kw):
    with Session() as s:
        a = s.get(Analysis, aid)
        for k, v in kw.items(): setattr(a, k, v)
        s.commit()

@app.get("/api/metadata")
def metadata(title: str):
    try: return movie_metadata.search_movie(title)
    except LookupError as e: raise HTTPException(404, str(e))
    except Exception as e: raise HTTPException(502, str(e))

@app.post("/api/upload")
async def upload(file: UploadFile = File(...), title: str = Form("")):
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED: raise HTTPException(400, f"Unsupported format. Allowed: {sorted(ALLOWED)}")
    aid = uuid.uuid4().hex
    path = os.path.join(UPLOADS, aid + ext); size = 0
    with open(path, "wb") as out:                       # streamed to disk: safe for large files
        while chunk := await file.read(1024 * 1024):
            size += len(chunk)
            if size > MAX_BYTES: out.close(); os.remove(path); raise HTTPException(413, "File too large")
            out.write(chunk)
    with Session() as s:
        s.add(Analysis(id=aid, title=title or file.filename)); s.commit()
    return {"id": aid}

def _run(aid: str, path: str | None, srt: str | None, age_group: str, tolerance: str):
    try:
        _update(aid, status="running")
        mods = []
        if path:
            def prog(base, span):
                return lambda p, m: _update(aid, progress=round(base + p * span, 3), message=m)
            mods.append(video_analyzer.analyze_video(path, prog(0.0, 0.6)).to_dict())
            mods.append(audio_analyzer.analyze_audio(path, prog(0.6, 0.3)).to_dict())
        if srt:
            mods.append(subtitle_analyzer.analyze_srt(srt).to_dict())
        verdict = classification_engine.classify(mods, None, age_group, tolerance)
        _update(aid, status="done", progress=1.0, message="Complete", modules=mods, verdict=verdict)
    except Exception as e:
        _update(aid, status="failed", message=str(e))
    finally:
        if path and os.path.exists(path): os.remove(path)   # privacy: always delete the upload

@app.post("/api/analyze/{aid}")
async def analyze(aid: str, bg: BackgroundTasks, age_group: str = Form("7to12"), tolerance: str = Form("normal"),
                  subtitles: UploadFile | None = File(None), official_title: str = Form("")):
    path = next((os.path.join(UPLOADS, f) for f in os.listdir(UPLOADS) if f.startswith(aid)), None)
    if not path: raise HTTPException(404, "Upload not found")
    if age_group not in classification_engine.PROFILES or tolerance not in classification_engine.TOLERANCE:
        raise HTTPException(400, "Invalid age_group or tolerance")
    srt = (await subtitles.read()).decode("utf-8", "ignore") if subtitles else None
    if official_title:
        try: _update(aid, metadata_=movie_metadata.search_movie(official_title))
        except Exception: pass
    bg.add_task(_run, aid, path, srt, age_group, tolerance)
    return {"id": aid, "status": "queued"}

@app.get("/api/progress/{aid}")
def progress(aid: str):
    with Session() as s:
        a = s.get(Analysis, aid)
        if not a: raise HTTPException(404, "Unknown analysis")
        return {"status": a.status, "progress": a.progress, "message": a.message}

@app.get("/api/results/{aid}")
def results(aid: str):
    with Session() as s:
        a = s.get(Analysis, aid)
        if not a: raise HTTPException(404, "Unknown analysis")
        return {"id": a.id, "title": a.title, "status": a.status, "metadata": a.metadata_,
                "modules": a.modules, "verdict": a.verdict}

@app.get("/api/history")
def history():
    with Session() as s:
        rows = s.query(Analysis).order_by(Analysis.created.desc()).limit(100).all()
        return [{"id": r.id, "title": r.title, "status": r.status, "created": r.created.isoformat(),
                 "label": (r.verdict or {}).get("label")} for r in rows]

@app.get("/api/report/{aid}.pdf")
def report(aid: str):
    with Session() as s:
        a = s.get(Analysis, aid)
        if not a or not a.verdict: raise HTTPException(404, "No finished analysis")
        out = f"/tmp/{aid}.pdf"
        report_generator.build_pdf(out, a.title, (a.metadata_ or {}).get("official_rating"), a.verdict)
    return FileResponse(out, media_type="application/pdf", filename=f"{a.title}.pdf")

@app.get("/")
def home():
    return FileResponse(Path(__file__).resolve().parent.parent / "static" / "index.html")
