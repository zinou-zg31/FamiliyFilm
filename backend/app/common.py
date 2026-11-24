"""Shared types. Every analyzer returns a ModuleResult."""
import os
from dataclasses import dataclass, field, asdict

CATEGORIES = ["violence", "sexual", "language", "horror", "substances"]

@dataclass
class Finding:
    category: str          # one of CATEGORIES
    confidence: float      # 0-1, model certainty
    severity: int          # 1 mild, 2 moderate, 3 severe
    timestamp: float | None = None   # seconds
    detail: str = ""

@dataclass
class ModuleResult:
    module: str
    available: bool                   # False = model/tool missing, nothing was analyzed
    coverage: float = 0.0             # 0-1 share of the movie actually analyzed
    categories_covered: list[str] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    def to_dict(self): return asdict(self)

def env(name, default=""): return os.getenv(name, default)
