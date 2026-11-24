"""Extract audio with FFmpeg, transcribe with Whisper, analyze the transcript."""
import shutil, subprocess, tempfile, os
from .common import ModuleResult, env
from .subtitle_analyzer import analyze_segments

def analyze_audio(video_path: str, progress=lambda p, m: None) -> ModuleResult:
    if not shutil.which("ffmpeg"):
        return ModuleResult("audio", False, notes=["FFmpeg not installed."])
    try:
        import whisper
    except ImportError:
        return ModuleResult("audio", False, notes=["openai-whisper not installed."])
    with tempfile.TemporaryDirectory() as d:
        wav = os.path.join(d, "a.wav")
        progress(0.0, "Extracting audio")
        proc = subprocess.run(["ffmpeg", "-y", "-i", video_path, "-vn", "-ac", "1", "-ar", "16000", wav],
                              capture_output=True, text=True)
        if proc.returncode != 0 or not os.path.exists(wav):
            err = (proc.stderr or "").strip().splitlines()
            reason = err[-1] if err else "unknown error"
            return ModuleResult("audio", False, notes=[
                "Audio NOT analyzed: could not extract audio (the file may have no audio track or may be damaged). "
                f"FFmpeg said: {reason}"])
        progress(0.2, "Transcribing speech")
        model = whisper.load_model(env("WHISPER_MODEL", "base"))
        out = model.transcribe(wav)
    segs = [(s["start"], s["text"]) for s in out["segments"]]
    res = analyze_segments(segs, "audio")
    res.notes.append(f"Language detected: {out.get('language')}. Audio analysis covers speech only (no sound-effect detection).")
    return res
