from app.domain import Category, Priority
from app.providers.triage.base import TriageResult

_CATEGORY_KEYWORDS: dict[Category, tuple[str, ...]] = {
    Category.WATER: ("water", "pani", "paani", "pipe", "leak", "tanker", "tap ", "tubewell", "flood"),
    Category.ELECTRICITY: ("electric", "bijli", "power", "voltage", "transformer", "wire",
                           "meter", "load shedding", "loadshedding", "outage", "spark"),
    Category.SANITATION: ("sewage", "sewerage", "gutter", "nali", "drain", "kachra", "garbage",
                          "waste", "dustbin", "manhole", "sweeper", "dump"),
    Category.ROADS: ("road", "sarak", "pothole", "bridge", "footpath", "speed breaker",
                     "zebra", "tarmac", "caved"),
    Category.STREETLIGHTS: ("streetlight", "street light", "light pole", "lamp", "andhera", "bulb"),
}
_HIGH = ("burst", "flood", "sparking", "electrocut", "fire", "open manhole", "live wire",
         "collapsed", "caved", "accident", "dangerous", "emergency", "sewage overflow")
_LOW = ("minor", "cosmetic", "suggestion", "when budget", "not urgent")


def one_line(text: str) -> str:
    s = " ".join(text.split())
    return s if len(s) <= 140 else s[:137].rstrip() + "..."


class RuleBasedTriage:
    name = "rules"

    def triage(self, text: str, location: str) -> TriageResult:
        t = text.lower()
        scores = {c: sum(1 for k in kws if k in t) for c, kws in _CATEGORY_KEYWORDS.items()}
        category, best = max(scores.items(), key=lambda kv: kv[1])   # ties: first in dict order
        if best == 0:
            category = Category.OTHER
        if any(k in t for k in _HIGH):
            priority = Priority.HIGH
        elif any(k in t for k in _LOW):
            priority = Priority.LOW
        else:
            priority = Priority.NORMAL
        return TriageResult(category=category, priority=priority, summary=one_line(text),
                            confidence=0.4 if best else 0.2)
