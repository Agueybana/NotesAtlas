from __future__ import annotations

import re
import sqlite3
import subprocess
import threading
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


RECORD_SEP = chr(30)
FIELD_SEP = chr(31)
SECTION_SEP = chr(29)
MAX_SEARCH_TEXT = 2200
MAX_SNIPPET_BATCH = 24
SYNC_PORTION_FOR_DEEP_READ: int | None = None


STOPWORDS = {
    "a",
    "about",
    "after",
    "all",
    "also",
    "am",
    "an",
    "and",
    "any",
    "are",
    "as",
    "at",
    "be",
    "because",
    "been",
    "being",
    "but",
    "by",
    "can",
    "do",
    "for",
    "from",
    "had",
    "has",
    "have",
    "he",
    "her",
    "him",
    "his",
    "how",
    "i",
    "if",
    "in",
    "into",
    "is",
    "it",
    "its",
    "just",
    "me",
    "more",
    "most",
    "my",
    "new",
    "no",
    "not",
    "of",
    "on",
    "or",
    "our",
    "out",
    "she",
    "so",
    "that",
    "the",
    "their",
    "them",
    "there",
    "they",
    "this",
    "to",
    "up",
    "was",
    "we",
    "what",
    "when",
    "which",
    "who",
    "why",
    "with",
    "would",
    "you",
    "your",
}


GENERIC_TITLES = {
    "",
    "new note",
    "note",
    "untitled",
    "draft",
    "ideas",
    "thoughts",
    "misc",
}


TAXONOMY: dict[str, dict[str, list[str]]] = {
    "IBD": {
        "Crohn's disease": [
            "crohn",
            "crohn's",
            "ileum",
            "terminal ileum",
            "fistula",
            "stricture",
            "perianal",
        ],
        "Colitis": [
            "colitis",
            "ulcerative colitis",
            "uc",
            "colon inflammation",
            "bloody stool",
            "rectal bleeding",
        ],
        "Gut health": [
            "gut",
            "digestive",
            "digestion",
            "microbiome",
            "stomach",
            "bowel",
            "intestine",
            "ibs",
            "inflammation",
        ],
        "Treatment & diet": [
            "prednisone",
            "mesalamine",
            "biologic",
            "remicade",
            "entyvio",
            "diet",
            "fiber",
            "probiotic",
            "supplement",
            "flare",
        ],
    },
    "Philosophy": {
        "Consciousness": [
            "consciousness",
            "awareness",
            "qualia",
            "mind",
            "experience",
            "subjective",
            "self-awareness",
        ],
        "Freedom & control": [
            "free will",
            "freedom",
            "control",
            "determinism",
            "agency",
            "choice",
            "destiny",
        ],
        "Meaning & purpose": [
            "meaning",
            "purpose",
            "existence",
            "teleology",
            "truth",
            "reality",
            "ontology",
            "epistemology",
            "metaphysics",
        ],
        "Ethics & identity": [
            "morality",
            "ethics",
            "virtue",
            "identity",
            "self",
            "character",
            "goodness",
            "evil",
        ],
    },
    "Religion": {
        "God": [
            "god",
            "divine",
            "creator",
            "ground of being",
            "theism",
            "theistic",
            "atheist",
            "atheism",
        ],
        "Spirituality": [
            "spiritual",
            "soul",
            "mystic",
            "mysticism",
            "prayer",
            "grace",
            "revelation",
            "transcendence",
        ],
        "Christianity": [
            "jesus",
            "christ",
            "christian",
            "bible",
            "scripture",
            "church",
            "resurrection",
            "gospel",
            "romans",
        ],
        "Comparative religion": [
            "buddha",
            "buddhist",
            "maya",
            "jnana",
            "hindu",
            "islam",
            "religion",
            "theologian",
            "theology",
        ],
    },
    "Science Critique": {
        "Scientism": [
            "scientism",
            "materialism",
            "reductionism",
            "scientific method",
            "science is",
            "epistemology",
            "peer review",
        ],
        "Medicine critique": [
            "big pharma",
            "medicine",
            "medical",
            "diagnosis",
            "cure",
            "doctor",
            "pharmaceutical",
            "psychiatry",
            "therapeutic state",
        ],
        "Institutions & bias": [
            "bias",
            "censorship",
            "propaganda",
            "narrative",
            "data",
            "study",
            "statistics",
            "capitalism",
            "funding",
        ],
    },
    "Science": {
        "Research": [
            "research",
            "lab",
            "experiment",
            "hypothesis",
            "paper",
            "study",
            "phd",
            "academia",
            "scientific",
        ],
        "Genetics & biology": [
            "dna",
            "genome",
            "genes",
            "genetic",
            "sequencing",
            "bacteria",
            "microbiology",
            "biology",
            "molecular",
        ],
    },
    "Relationships": {
        "Women": [
            "women",
            "woman",
            "female",
            "femininity",
            "girlfriend",
            "wife",
            "wives",
            "bride",
        ],
        "Men": [
            "men",
            "man",
            "male",
            "masculinity",
            "husband",
            "boyfriend",
            "gentleman",
        ],
        "Dating": [
            "dating",
            "attraction",
            "desire",
            "seduction",
            "romance",
            "love",
            "breakup",
            "marriage",
        ],
        "Intimacy": [
            "intimacy",
            "sex",
            "sexual",
            "porn",
            "kiss",
            "bed",
            "desire",
            "connection",
        ],
    },
    "Poetry": {
        "Poems & fragments": [
            "poem",
            "poetry",
            "verse",
            "stanza",
            "line break",
            "haiku",
            "lyric fragment",
        ],
        "Metaphors & aphorisms": [
            "aphorism",
            "metaphor",
            "imagery",
            "beautiful",
            "beauty",
            "soul",
            "silence",
            "hidden gem",
        ],
    },
    "Art": {
        "Aesthetics": [
            "art",
            "aesthetic",
            "beauty",
            "painting",
            "brush",
            "masterpiece",
            "design",
            "artist",
        ],
        "Visual ideas": [
            "photo",
            "photography",
            "image",
            "visual",
            "color",
            "composition",
            "gallery",
        ],
    },
    "Music": {
        "Lyrics & songs": [
            "music",
            "song",
            "lyrics",
            "album",
            "melody",
            "playlist",
            "listen",
            "sound",
            "beat",
        ],
        "Artists & references": [
            "victor hugo",
            "janis joplin",
            "thom yorke",
            "tomás rodriguez",
            "joplin",
            "hugo",
        ],
    },
    "Drugs": {
        "Psychedelics": [
            "psychedelic",
            "dmt",
            "lsd",
            "mushroom",
            "psilocybin",
            "ayahuasca",
            "trip",
        ],
        "Substances": [
            "weed",
            "cannabis",
            "alcohol",
            "nicotine",
            "drug",
            "pill",
            "substance",
        ],
    },
    "Entertainment": {
        "Movies & TV": [
            "movie",
            "film",
            "show",
            "series",
            "episode",
            "netflix",
            "cinema",
        ],
        "Books & media": [
            "book",
            "novel",
            "story",
            "fiction",
            "character",
            "plot",
            "podcast",
            "video",
        ],
        "Comedy & memes": [
            "funny",
            "humor",
            "joke",
            "meme",
            "dark humor",
            "comedian",
            "laugh",
        ],
    },
    "Marketing": {
        "Branding": [
            "brand",
            "branding",
            "positioning",
            "audience",
            "identity",
            "messaging",
        ],
        "Sales & persuasion": [
            "sales",
            "offer",
            "funnel",
            "copy",
            "copywriting",
            "pitch",
            "persuasion",
            "conversion",
            "lead",
        ],
        "Social growth": [
            "marketing",
            "social media",
            "instagram",
            "twitter",
            "linkedin",
            "viral",
            "content strategy",
        ],
    },
    "Technology": {
        "AI & LLMs": [
            "ai",
            "llm",
            "chatgpt",
            "claude",
            "gemini",
            "prompt",
            "grok",
            "deepseek",
            "model",
            "prompting",
            "intelligence",
            "agent",
            "agents",
        ],
        "Software & code": [
            "software",
            "code",
            "coding",
            "python",
            "javascript",
            "api",
            "app",
            "website",
            "database",
            "automation",
            "error",
            "fixed",
            "debug",
            "user",
        ],
        "Computing & internet": [
            "technology",
            "tech",
            "internet",
            "hardware",
            "computer",
            "quantum computing",
            "startup",
            "saas",
        ],
    },
    "Jobs": {
        "Career": [
            "career",
            "job",
            "employment",
            "work",
            "professional",
            "hire",
            "promotion",
        ],
        "Applications": [
            "application",
            "resume",
            "cv",
            "cover letter",
            "interview",
            "recruiter",
            "linkedin",
        ],
        "Operations & management": [
            "manager",
            "leadership",
            "management",
            "team",
            "headcount",
            "operator",
            "workplace",
        ],
    },
    "Finance": {
        "Money & budgeting": [
            "money",
            "budget",
            "frugality",
            "salary",
            "income",
            "expense",
            "price",
        ],
        "Investing": [
            "invest",
            "investment",
            "stock",
            "market",
            "equity",
            "portfolio",
            "crypto",
            "bitcoin",
        ],
        "Business economics": [
            "economics",
            "finance",
            "profit",
            "revenue",
            "cash flow",
            "monetization",
            "capital",
        ],
    },
    "Health": {
        "General wellness": [
            "health",
            "sleep",
            "exercise",
            "longevity",
            "wellness",
            "body",
            "nutrition",
            "pain",
        ],
        "Mental health": [
            "depression",
            "anxiety",
            "stress",
            "therapy",
            "trauma",
            "healing",
            "psychology",
            "adhd",
        ],
    },
    "Business": {
        "Strategy": [
            "strategy",
            "business",
            "entrepreneur",
            "startup",
            "execution",
            "operations",
            "scaling",
            "opportunity",
        ],
        "Leadership": [
            "leadership",
            "principle",
            "decision",
            "management",
            "teamwork",
            "resourcefulness",
        ],
    },
    "Politics & Society": {
        "Power & governance": [
            "politics",
            "state",
            "power",
            "government",
            "law",
            "regulation",
            "censorship",
            "war",
        ],
        "Culture critique": [
            "society",
            "culture",
            "civilization",
            "propaganda",
            "public",
            "ideology",
            "freedom of speech",
        ],
    },
    "Writing": {
        "Drafts & essays": [
            "essay",
            "draft",
            "writing",
            "chapter",
            "manuscript",
            "outline",
            "treatise",
        ],
        "Prompts & ideas": [
            "prompt",
            "idea",
            "brainstorm",
            "concept",
            "template",
            "framework",
            "wit engine",
        ],
    },
    "Personal": {
        "Journal": [
            "journal",
            "diary",
            "today",
            "yesterday",
            "felt",
            "feel",
            "my life",
            "life",
            "vida",
            "myself",
            "experience",
            "realization",
        ],
        "Goals & plans": [
            "goal",
            "plan",
            "priority",
            "focus",
            "project",
            "next step",
            "todo",
        ],
    },
    "Projects": {
        "BouncyPaint": [
            "bouncypaint",
            "bouncy paint",
        ],
        "BODS / BODSai": [
            "bods",
            "bodsai",
        ],
        "AGM Wisdom Center": [
            "agm",
            "wisdom center",
            "craftee",
            "craftychat",
        ],
    },
    "Reference": {
        "Links & bookmarks": [
            "http://",
            "https://",
            "www.",
            ".com",
            ".org",
            ".ai",
            ".io",
        ],
        "Quotes & excerpts": [
            "quote",
            "excerpt",
            "—",
            "\"",
            "“",
            "”",
        ],
    },
    "Uncategorized": {
        "General": [],
    },
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def normalize_spaces(value: str) -> str:
    return re.sub(r"\s+", " ", ensure_text(value)).strip()


def normalize_for_match(value: str) -> str:
    value = ensure_text(value).replace("\u202f", " ").lower()
    value = re.sub(r"[\u2018\u2019]", "'", value)
    value = re.sub(r"[^a-z0-9+/#'.\-\s]", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def parse_applescript_date(value: str) -> str:
    clean = ensure_text(value).replace("\u202f", " ").strip()
    if not clean:
        return ""
    for fmt in ("%A, %B %d, %Y at %I:%M:%S %p", "%A, %B %d, %Y at %H:%M:%S"):
        try:
            return datetime.strptime(clean, fmt).isoformat()
        except ValueError:
            continue
    return clean


def apple_escape(value: str) -> str:
    return ensure_text(value).replace("\\", "\\\\").replace('"', '\\"')


def run_osascript(script: str, timeout: int = 180) -> str:
    proc = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or "osascript failed")
    return proc.stdout.rstrip("\n")


def clip_text(value: str, limit: int) -> str:
    value = normalize_spaces(value)
    if len(value) <= limit:
        return value
    cut = value[: limit - 1].rsplit(" ", 1)[0].strip()
    return (cut or value[: limit - 1]).rstrip(" ,.;:") + "…"


def first_sentence(value: str, limit: int = 88) -> str:
    compact = ensure_text(value).replace("\n", " ").strip()
    if not compact:
        return ""
    parts = re.split(r"(?<=[.!?])\s+", compact)
    for part in parts:
        part = normalize_spaces(part)
        if len(part) >= 12:
            return clip_text(part, limit)
    return clip_text(compact, limit)


def extract_keywords(value: str, limit: int = 3) -> list[str]:
    tokens = re.findall(r"[a-zA-Z][a-zA-Z0-9'+-]{2,}", ensure_text(value).lower())
    counts: Counter[str] = Counter()
    for token in tokens:
        if token in STOPWORDS:
            continue
        if token.startswith("http"):
            continue
        counts[token] += 1
    return [word for word, _ in counts.most_common(limit)]


def label_tokens(value: str) -> list[str]:
    return [
        token
        for token in re.findall(r"[a-zA-Z][a-zA-Z0-9'+-]{2,}", ensure_text(value).lower())
        if token not in STOPWORDS
    ]


def is_generic_title(title: str) -> bool:
    clean = normalize_for_match(title)
    if clean in GENERIC_TITLES:
        return True
    if clean.startswith("http://") or clean.startswith("https://"):
        return True
    if re.fullmatch(r"[\W_]+", ensure_text(title) or ""):
        return True
    if re.fullmatch(r"\d{1,2}[:/\-]\d{1,2}([:/\-]\d{2,4})?", clean):
        return True
    return False


def score_text(keyword: str, haystack: str) -> float:
    if not keyword:
        return 0.0
    keyword = keyword.lower()
    if "://" in keyword or "." in keyword:
        return 1.3 if keyword in haystack else 0.0
    if " " in keyword or "'" in keyword or "-" in keyword:
        return 1.3 if keyword in haystack else 0.0
    pattern = rf"\b{re.escape(keyword)}\b"
    matches = re.findall(pattern, haystack)
    return min(len(matches), 3) * 1.1


def candidate_keywords(category: str, subcategory: str) -> list[str]:
    keywords = list(TAXONOMY.get(category, {}).get(subcategory, []))
    for token in label_tokens(category):
        if token not in keywords:
            keywords.append(token)
    for token in label_tokens(subcategory):
        if token not in keywords:
            keywords.append(token)
    return keywords


def score_candidate(category: str, subcategory: str, title: str, text: str) -> tuple[float, list[str]]:
    haystack = normalize_for_match(f"{title}\n{text}")
    title_haystack = normalize_for_match(title)
    score = 0.0
    matched_keywords: list[str] = []
    for keyword in candidate_keywords(category, subcategory):
        text_score = score_text(keyword, haystack)
        title_score = score_text(keyword, title_haystack) * 2.2
        keyword_score = text_score + title_score
        if keyword_score > 0:
            matched_keywords.append(keyword)
            score += keyword_score
    if normalize_for_match(category) in haystack:
        score += 0.9
    if normalize_for_match(subcategory) in haystack:
        score += 1.1
    return score, matched_keywords[:4]


def fallback_suggestions(title: str, text: str) -> list[tuple[str, str, str]]:
    haystack = normalize_for_match(f"{title}\n{text}")
    if "http://" in haystack or "https://" in haystack or "www." in haystack:
        return [
            ("Reference", "Links & bookmarks", "The note looks link-heavy."),
            ("Technology", "Computing & internet", "The note references web or internet content."),
            ("Entertainment", "Books & media", "The note may be media-related."),
        ]
    if any(mark in ensure_text(text) for mark in ['"', "“", "”", "—"]) or ensure_text(text).count("\n") >= 4:
        return [
            ("Reference", "Quotes & excerpts", "The note reads like a saved quote or excerpt."),
            ("Writing", "Drafts & essays", "The note reads like longer-form text."),
            ("Personal", "Journal", "The note may be a personal reflection."),
        ]
    return [
        ("Writing", "Drafts & essays", "The note reads like a freeform written draft."),
        ("Personal", "Journal", "The note may be a personal note or reflection."),
        ("Reference", "Quotes & excerpts", "The note may fit a reference bucket."),
    ]


def rank_category_suggestions(
    title: str,
    text: str,
    available_pairs: list[tuple[str, str]],
    limit: int = 3,
) -> list[dict[str, Any]]:
    ranked: list[dict[str, Any]] = []
    for category, subcategory in available_pairs:
        if category == "Uncategorized":
            continue
        score, matched = score_candidate(category, subcategory, title, text)
        if score <= 0:
            continue
        ranked.append(
            {
                "category": category,
                "subcategory": subcategory,
                "score": round(score, 3),
                "reason": f"Matched: {', '.join(matched[:3])}" if matched else "Matched note content.",
            }
        )
    ranked.sort(key=lambda item: (-item["score"], item["category"], item["subcategory"]))
    if ranked:
        return ranked[:limit]

    fallbacks = []
    for category, subcategory, reason in fallback_suggestions(title, text):
        if (category, subcategory) not in available_pairs:
            continue
        fallbacks.append(
            {
                "category": category,
                "subcategory": subcategory,
                "score": 0.0,
                "reason": reason,
            }
        )
    if fallbacks:
        return fallbacks[:limit]

    generic = []
    for category, subcategory in available_pairs:
        if category == "Uncategorized":
            continue
        generic.append(
            {
                "category": category,
                "subcategory": subcategory,
                "score": 0.0,
                "reason": "General fallback suggestion.",
            }
        )
    return generic[:limit]


def classify_note(original_name: str, snippet: str = "", force_category: bool = False) -> dict[str, Any]:
    name = normalize_spaces(original_name)
    text_source = f"{name}\n{snippet}".strip()
    haystack = normalize_for_match(text_source)
    title_haystack = normalize_for_match(name)
    if not haystack:
        return {
            "category": "Uncategorized",
            "subcategory": "General",
            "confidence": 0.0,
            "generated_title": "Untitled note",
            "preview_text": "",
            "search_text": "",
        }

    best: tuple[str, str, float] = ("Uncategorized", "General", 0.0)
    second_score = 0.0
    for category, subcategories in TAXONOMY.items():
        for subcategory, keywords in subcategories.items():
            score = 0.0
            for keyword in keywords:
                score += score_text(keyword, haystack)
                score += score_text(keyword, title_haystack) * 1.9
            if category == "Reference" and any(mark in original_name for mark in ('"', "“", "”", "—")):
                score += 1.0
            if score > best[2]:
                second_score = best[2]
                best = (category, subcategory, score)
            elif score > second_score:
                second_score = score

    if best[2] <= 0.5:
        category = "Uncategorized"
        subcategory = "General"
        confidence = 0.08
        if force_category and snippet.strip():
            fallback = fallback_suggestions(original_name, snippet)
            category, subcategory = fallback[0][0], fallback[0][1]
            confidence = 0.12
    else:
        category, subcategory, top_score = best
        margin = top_score - second_score
        confidence = min(0.99, 0.35 + (top_score * 0.08) + (margin * 0.07))

    preview_basis = snippet or original_name
    preview_text = clip_text(preview_basis, 190)
    generated_title = build_generated_title(
        original_name=original_name,
        preview_text=preview_basis,
        category=category,
        subcategory=subcategory,
    )

    search_text = clip_text(f"{original_name}\n{snippet}", MAX_SEARCH_TEXT)
    return {
        "category": category,
        "subcategory": subcategory,
        "confidence": round(confidence, 3),
        "generated_title": generated_title,
        "preview_text": preview_text,
        "search_text": search_text,
    }


def build_generated_title(original_name: str, preview_text: str, category: str, subcategory: str) -> str:
    clean_name = normalize_spaces(original_name)
    if clean_name and not is_generic_title(clean_name):
        return clip_text(clean_name, 92)

    sentence = first_sentence(preview_text, 80)
    if sentence and not is_generic_title(sentence):
        return sentence

    keywords = extract_keywords(preview_text, limit=3)
    if keywords:
        human = ", ".join(keywords[:2])
        if category == "Uncategorized":
            return clip_text(f"Note about {human}", 92)
        return clip_text(f"{subcategory}: {human}", 92)

    if category == "Uncategorized":
        return "Untitled note"
    return clip_text(f"{subcategory} note", 92)


def default_categories() -> dict[str, list[str]]:
    return {category: list(subcategories.keys()) for category, subcategories in TAXONOMY.items()}


@dataclass
class SyncSnapshot:
    running: bool = False
    phase: str = "idle"
    message: str = "Waiting to sync"
    current: int = 0
    total: int = 0
    started_at: str = ""
    finished_at: str = ""
    error: str = ""
    last_summary: str = ""


class SyncTracker:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._state = SyncSnapshot()

    def get(self) -> dict[str, Any]:
        with self._lock:
            return dict(self._state.__dict__)

    def start(self, phase: str, message: str, total: int = 0) -> None:
        with self._lock:
            self._state = SyncSnapshot(
                running=True,
                phase=phase,
                message=message,
                current=0,
                total=total,
                started_at=now_iso(),
                finished_at="",
                error="",
                last_summary=self._state.last_summary,
            )

    def update(self, phase: str | None = None, message: str | None = None, current: int | None = None, total: int | None = None) -> None:
        with self._lock:
            if phase is not None:
                self._state.phase = phase
            if message is not None:
                self._state.message = message
            if current is not None:
                self._state.current = current
            if total is not None:
                self._state.total = total

    def finish(self, summary: str) -> None:
        with self._lock:
            self._state.running = False
            self._state.phase = "done"
            self._state.message = "Sync finished"
            self._state.finished_at = now_iso()
            self._state.error = ""
            self._state.last_summary = summary

    def fail(self, error: str) -> None:
        with self._lock:
            self._state.running = False
            self._state.phase = "error"
            self._state.message = "Sync failed"
            self._state.finished_at = now_iso()
            self._state.error = error


class CatalogStore:
    def __init__(self, base_dir: Path) -> None:
        self.base_dir = Path(base_dir)
        self.db_path = self.base_dir / "data" / "notes_catalog.db"
        self.sync = SyncTracker()
        self._sync_lock = threading.Lock()
        self._sync_thread: threading.Thread | None = None
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=60)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def _init_db(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS notes (
                    note_id TEXT PRIMARY KEY,
                    account_name TEXT NOT NULL,
                    folder_name TEXT NOT NULL,
                    note_index INTEGER NOT NULL DEFAULT 0,
                    original_name TEXT NOT NULL,
                    generated_title TEXT NOT NULL,
                    preview_text TEXT NOT NULL DEFAULT '',
                    search_text TEXT NOT NULL DEFAULT '',
                    category TEXT NOT NULL DEFAULT 'Uncategorized',
                    subcategory TEXT NOT NULL DEFAULT 'General',
                    classifier_confidence REAL NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL DEFAULT '',
                    modified_at TEXT NOT NULL DEFAULT '',
                    password_protected INTEGER NOT NULL DEFAULT 0,
                    is_active INTEGER NOT NULL DEFAULT 1,
                    last_synced_at TEXT NOT NULL DEFAULT '',
                    opened_at TEXT NOT NULL DEFAULT ''
                );

                CREATE TABLE IF NOT EXISTS note_overrides (
                    note_id TEXT PRIMARY KEY REFERENCES notes(note_id) ON DELETE CASCADE,
                    category TEXT NOT NULL,
                    subcategory TEXT NOT NULL DEFAULT 'General',
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS custom_categories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category TEXT NOT NULL,
                    subcategory TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    UNIQUE(category, subcategory)
                );

                CREATE INDEX IF NOT EXISTS idx_notes_active_modified ON notes(is_active, modified_at DESC);
                CREATE INDEX IF NOT EXISTS idx_notes_category ON notes(category, subcategory);
                CREATE INDEX IF NOT EXISTS idx_notes_folder ON notes(account_name, folder_name);
                """
            )

    def count_active_notes(self) -> int:
        with self._connect() as conn:
            row = conn.execute("SELECT COUNT(*) AS c FROM notes WHERE is_active = 1").fetchone()
            return int(row["c"])

    def start_sync(self) -> bool:
        with self._sync_lock:
            if self._sync_thread and self._sync_thread.is_alive():
                return False
            self._sync_thread = threading.Thread(target=self._sync_worker, daemon=True)
            self._sync_thread.start()
            return True

    def sync_blocking(self) -> None:
        with self._sync_lock:
            self._sync_worker()

    def get_sync_status(self) -> dict[str, Any]:
        return self.sync.get()

    def _sync_worker(self) -> None:
        self.sync.start("inventory", "Reading Notes folder inventory")
        try:
            inventory = self.fetch_folder_inventory()
            folders = [item for item in inventory if item["note_count"] > 0]
            total_notes = sum(item["note_count"] for item in folders)
            self.sync.update(total=total_notes, message=f"Found {total_notes} notes across {len(folders)} folders")

            existing = self._load_existing()
            collected: list[dict[str, Any]] = []
            processed = 0

            for folder_meta in folders:
                account_name = folder_meta["account_name"]
                folder_name = folder_meta["folder_name"]
                self.sync.update(
                    phase="metadata",
                    message=f"Reading metadata from {account_name} / {folder_name}",
                    current=processed,
                    total=total_notes,
                )
                notes = self.fetch_folder_metadata(account_name, folder_name)
                for note in notes:
                    note_id = note["note_id"]
                    previous = existing.get(note_id)
                    base = classify_note(note["original_name"], "")
                    note.update(base)

                    if previous and previous["modified_at"] == note["modified_at"] and previous["original_name"] == note["original_name"] and previous["search_text"]:
                        note["generated_title"] = previous["generated_title"]
                        note["preview_text"] = previous["preview_text"]
                        note["search_text"] = previous["search_text"]
                        note["category"] = previous["category"]
                        note["subcategory"] = previous["subcategory"]
                        note["confidence"] = previous["classifier_confidence"]
                        if note["category"] == "Uncategorized":
                            note.update(classify_note(note["original_name"], note["search_text"], force_category=True))

                    collected.append(note)
                processed += len(notes)
                self.sync.update(current=processed)

            self.sync.update(phase="classify", message="Choosing notes that need deeper reading", current=processed, total=total_notes)
            self._upsert_notes(collected)
            to_enrich = self._notes_needing_snippets(collected, existing)
            if to_enrich:
                self.sync.update(phase="snippets", message=f"Reading deeper snippets for {len(to_enrich)} notes", current=0, total=len(to_enrich))
                self._enrich_with_snippets(collected, to_enrich)

            self.sync.update(phase="database", message="Writing catalog database", current=0, total=len(collected))
            self._upsert_notes(collected)
            summary = f"Catalog contains {len(collected)} active notes. Deep-read enrichment covered {len(to_enrich)} notes."
            self.sync.finish(summary)
        except Exception as exc:
            self.sync.fail(str(exc))

    def fetch_folder_inventory(self) -> list[dict[str, Any]]:
        script = f"""
        set us to character id {ord(FIELD_SEP)}
        set rs to character id {ord(RECORD_SEP)}
        set out to {{}}
        tell application "Notes"
            repeat with a in every account
                set acctName to name of a
                repeat with f in every folder of a
                    set end of out to acctName & us & (name of f) & us & ((count of every note of f) as text)
                end repeat
            end repeat
        end tell
        set AppleScript's text item delimiters to rs
        set joined to out as text
        set AppleScript's text item delimiters to ""
        return joined
        """
        raw = run_osascript(script, timeout=180)
        items = []
        if not raw:
            return items
        for row in raw.split(RECORD_SEP):
            if not row:
                continue
            account_name, folder_name, count_text = row.split(FIELD_SEP)
            items.append(
                {
                    "account_name": account_name,
                    "folder_name": folder_name,
                    "note_count": int(count_text or 0),
                }
            )
        return items

    def fetch_folder_metadata(self, account_name: str, folder_name: str) -> list[dict[str, Any]]:
        ids = self._fetch_note_property_list(account_name, folder_name, "id")
        names = self._fetch_note_property_list(account_name, folder_name, "name")
        modified = self._fetch_note_property_list(account_name, folder_name, "modification date")

        total = len(ids)
        if not (len(names) == len(modified) == total):
            raise RuntimeError(f"Metadata list mismatch for {account_name} / {folder_name}")

        notes: list[dict[str, Any]] = []
        for index in range(total):
            modified_at = parse_applescript_date(modified[index])
            notes.append(
                {
                    "note_id": ids[index],
                    "account_name": account_name,
                    "folder_name": folder_name,
                    "note_index": index + 1,
                    "original_name": normalize_spaces(names[index]),
                    "created_at": modified_at,
                    "modified_at": modified_at,
                    "password_protected": 0,
                    "is_active": 1,
                    "last_synced_at": now_iso(),
                }
            )
        return notes

    def _fetch_note_property_list(self, account_name: str, folder_name: str, property_name: str) -> list[str]:
        script = f"""
        set rs to character id {ord(RECORD_SEP)}
        tell application "Notes"
            tell folder "{apple_escape(folder_name)}" of account "{apple_escape(account_name)}"
                set valuesList to {property_name} of every note
            end tell
        end tell
        set AppleScript's text item delimiters to rs
        set outText to valuesList as text
        set AppleScript's text item delimiters to ""
        return outText
        """
        raw = run_osascript(script, timeout=240)
        if not raw:
            return []
        return raw.split(RECORD_SEP)

    def _notes_needing_snippets(self, notes: list[dict[str, Any]], existing: dict[str, sqlite3.Row]) -> list[dict[str, Any]]:
        candidates: list[dict[str, Any]] = []
        for note in notes:
            previous = existing.get(note["note_id"])
            generic = is_generic_title(note["original_name"])
            low_conf = note["confidence"] < 0.5 if "confidence" in note else note["classifier_confidence"] < 0.5
            uncategorized = note.get("category") == "Uncategorized"
            changed = not previous or previous["modified_at"] != note["modified_at"] or previous["original_name"] != note["original_name"]
            missing_search_text = not previous or not previous["search_text"]
            if note["password_protected"]:
                continue
            if uncategorized or missing_search_text or generic or (changed and low_conf):
                candidates.append(note)

        candidates.sort(key=lambda item: item["modified_at"], reverse=True)
        if SYNC_PORTION_FOR_DEEP_READ is None:
            return candidates
        return candidates[:SYNC_PORTION_FOR_DEEP_READ]

    def _enrich_with_snippets(self, notes: list[dict[str, Any]], targets: list[dict[str, Any]]) -> None:
        by_folder: dict[tuple[str, str], list[int]] = defaultdict(list)
        by_id = {note["note_id"]: note for note in notes}
        for note in targets:
            by_folder[(note["account_name"], note["folder_name"])].append(note["note_index"])

        enriched = 0
        total = len(targets)
        for (account_name, folder_name), indexes in by_folder.items():
            for chunk in self._chunks(sorted(indexes), MAX_SNIPPET_BATCH):
                rows = self.fetch_snippet_indexes(account_name, folder_name, chunk)
                for row in rows:
                    note = by_id.get(row["note_id"])
                    if not note:
                        continue
                    classified = classify_note(note["original_name"], row["snippet"], force_category=True)
                    note.update(classified)
                    enriched += 1
                self.sync.update(current=min(enriched, total))

    def fetch_snippet_batch(self, account_name: str, folder_name: str, start_index: int, end_index: int) -> list[dict[str, str]]:
        if start_index > end_index:
            return []
        return self.fetch_snippet_indexes(account_name, folder_name, list(range(start_index, end_index + 1)))

    def fetch_snippet_indexes(self, account_name: str, folder_name: str, indexes: list[int]) -> list[dict[str, str]]:
        indexes = [int(index) for index in indexes if int(index) > 0]
        if not indexes:
            return []
        index_list = "{" + ", ".join(str(index) for index in indexes) + "}"
        script = f"""
        on replace_text(theText, findText, replaceText)
            set AppleScript's text item delimiters to findText
            set textItems to every text item of theText
            set AppleScript's text item delimiters to replaceText
            set newText to textItems as text
            set AppleScript's text item delimiters to ""
            return newText
        end replace_text

        on sanitize(theText)
            set t to theText as text
            set t to my replace_text(t, character id {ord(FIELD_SEP)}, " ")
            set t to my replace_text(t, character id {ord(RECORD_SEP)}, " ")
            set t to my replace_text(t, character id {ord(SECTION_SEP)}, " ")
            return t
        end sanitize

        set us to character id {ord(FIELD_SEP)}
        set rs to character id {ord(RECORD_SEP)}
        set indexList to {index_list}
        set rowCount to 0
        set out to ""
        tell application "Notes"
            tell folder "{apple_escape(folder_name)}" of account "{apple_escape(account_name)}"
                repeat with noteIndex in indexList
                    try
                        set targetNote to note (noteIndex as integer)
                        set noteId to id of targetNote
                        set snippetText to plaintext of targetNote
                        if (length of snippetText) > {MAX_SEARCH_TEXT} then
                            set snippetText to text 1 thru {MAX_SEARCH_TEXT} of snippetText
                        end if
                        if rowCount > 0 then set out to out & rs
                        set out to out & (my sanitize(noteId)) & us & (my sanitize(snippetText))
                        set rowCount to rowCount + 1
                    end try
                end repeat
            end tell
        end tell
        return out
        """
        try:
            raw = run_osascript(script, timeout=300)
        except Exception:
            if len(indexes) <= 1:
                return []
            midpoint = len(indexes) // 2
            left = self.fetch_snippet_indexes(account_name, folder_name, indexes[:midpoint])
            right = self.fetch_snippet_indexes(account_name, folder_name, indexes[midpoint:])
            return left + right

        results = []
        if not raw:
            return results
        for row in raw.split(RECORD_SEP):
            if not row:
                continue
            note_id, snippet = row.split(FIELD_SEP, 1)
            results.append({"note_id": note_id, "snippet": snippet})
        return results

    def _chunks(self, indexes: list[int], size: int) -> list[list[int]]:
        return [indexes[index : index + size] for index in range(0, len(indexes), size)]

    def _group_ranges(self, indexes: list[int], max_batch: int) -> list[tuple[int, int]]:
        if not indexes:
            return []
        groups: list[tuple[int, int]] = []
        start = indexes[0]
        prev = indexes[0]
        count = 1
        for index in indexes[1:]:
            contiguous = index == prev + 1
            if contiguous and count < max_batch:
                prev = index
                count += 1
                continue
            groups.append((start, prev))
            start = index
            prev = index
            count = 1
        groups.append((start, prev))
        return groups

    def _load_existing(self) -> dict[str, sqlite3.Row]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT note_id, original_name, generated_title, preview_text, search_text,
                       category, subcategory, classifier_confidence, modified_at
                FROM notes
                """
            ).fetchall()
        return {row["note_id"]: row for row in rows}

    def _upsert_notes(self, notes: list[dict[str, Any]]) -> None:
        now = now_iso()
        with self._connect() as conn:
            conn.execute("UPDATE notes SET is_active = 0, last_synced_at = ?", (now,))
            conn.executemany(
                """
                INSERT INTO notes (
                    note_id, account_name, folder_name, note_index, original_name, generated_title,
                    preview_text, search_text, category, subcategory, classifier_confidence,
                    created_at, modified_at, password_protected, is_active, last_synced_at
                ) VALUES (
                    :note_id, :account_name, :folder_name, :note_index, :original_name, :generated_title,
                    :preview_text, :search_text, :category, :subcategory, :confidence,
                    :created_at, :modified_at, :password_protected, 1, :last_synced_at
                )
                ON CONFLICT(note_id) DO UPDATE SET
                    account_name = excluded.account_name,
                    folder_name = excluded.folder_name,
                    note_index = excluded.note_index,
                    original_name = excluded.original_name,
                    generated_title = excluded.generated_title,
                    preview_text = excluded.preview_text,
                    search_text = excluded.search_text,
                    category = excluded.category,
                    subcategory = excluded.subcategory,
                    classifier_confidence = excluded.classifier_confidence,
                    created_at = excluded.created_at,
                    modified_at = excluded.modified_at,
                    password_protected = excluded.password_protected,
                    is_active = 1,
                    last_synced_at = excluded.last_synced_at
                """,
                notes,
            )

    def _categories_with_counts(self) -> dict[str, Any]:
        structure = default_categories()
        with self._connect() as conn:
            custom = conn.execute("SELECT category, subcategory FROM custom_categories ORDER BY category, subcategory").fetchall()
            for row in custom:
                category = row["category"]
                subcategory = row["subcategory"] or "General"
                structure.setdefault(category, [])
                if subcategory not in structure[category]:
                    structure[category].append(subcategory)

            counts = conn.execute(
                """
                SELECT
                    COALESCE(o.category, n.category) AS category,
                    COALESCE(NULLIF(o.subcategory, ''), n.subcategory) AS subcategory,
                    COUNT(*) AS total
                FROM notes n
                LEFT JOIN note_overrides o ON o.note_id = n.note_id
                WHERE n.is_active = 1
                GROUP BY 1, 2
                """
            ).fetchall()

        category_totals: dict[str, int] = defaultdict(int)
        subcategory_totals: dict[tuple[str, str], int] = defaultdict(int)
        for row in counts:
            category = row["category"] or "Uncategorized"
            subcategory = row["subcategory"] or "General"
            total = int(row["total"])
            category_totals[category] += total
            subcategory_totals[(category, subcategory)] += total
            structure.setdefault(category, [])
            if subcategory not in structure[category]:
                structure[category].append(subcategory)

        categories = []
        for category in sorted(structure.keys()):
            subcats = []
            for subcategory in sorted(set(structure[category])):
                subcats.append(
                    {
                        "name": subcategory,
                        "count": subcategory_totals.get((category, subcategory), 0),
                    }
                )
            categories.append(
                {
                    "name": category,
                    "count": category_totals.get(category, 0),
                    "subcategories": subcats,
                }
            )
        return {"categories": categories}

    def query_state(
        self,
        search: str = "",
        category: str = "",
        subcategory: str = "",
        page: int = 1,
        page_size: int = 120,
    ) -> dict[str, Any]:
        page = max(page, 1)
        page_size = min(max(page_size, 1), 250)
        where = ["n.is_active = 1"]
        params: list[Any] = []

        if search:
            term = f"%{search.strip()}%"
            where.append("(n.generated_title LIKE ? OR n.original_name LIKE ? OR n.preview_text LIKE ? OR n.search_text LIKE ?)")
            params.extend([term, term, term, term])
        if category:
            where.append("COALESCE(o.category, n.category) = ?")
            params.append(category)
        if subcategory:
            where.append("COALESCE(NULLIF(o.subcategory, ''), n.subcategory) = ?")
            params.append(subcategory)

        where_sql = " AND ".join(where)
        offset = (page - 1) * page_size
        with self._connect() as conn:
            notes = conn.execute(
                f"""
                SELECT
                    n.note_id,
                    n.generated_title,
                    n.original_name,
                    n.preview_text,
                    n.account_name,
                    n.folder_name,
                    n.created_at,
                    n.modified_at,
                    n.password_protected,
                    n.classifier_confidence,
                    COALESCE(o.category, n.category) AS category,
                    COALESCE(NULLIF(o.subcategory, ''), n.subcategory) AS subcategory,
                    CASE WHEN o.note_id IS NOT NULL THEN 1 ELSE 0 END AS is_overridden
                FROM notes n
                LEFT JOIN note_overrides o ON o.note_id = n.note_id
                WHERE {where_sql}
                ORDER BY n.modified_at DESC, n.created_at DESC, n.note_id DESC
                LIMIT ? OFFSET ?
                """,
                [*params, page_size, offset],
            ).fetchall()
            total_row = conn.execute(
                f"""
                SELECT COUNT(*) AS c
                FROM notes n
                LEFT JOIN note_overrides o ON o.note_id = n.note_id
                WHERE {where_sql}
                """,
                params,
            ).fetchone()

        payload = {
            "notes": [dict(row) for row in notes],
            "total_notes": int(total_row["c"]),
            "page": page,
            "page_size": page_size,
            "has_more": offset + len(notes) < int(total_row["c"]),
            "filters": {"search": search, "category": category, "subcategory": subcategory},
        }
        payload.update(self._categories_with_counts())
        payload["sync_status"] = self.get_sync_status()
        return payload

    def create_category(self, category: str, subcategory: str = "") -> None:
        category = normalize_spaces(category)
        subcategory = normalize_spaces(subcategory or "General")
        if not category:
            raise ValueError("Category name is required")
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO custom_categories(category, subcategory, created_at)
                VALUES (?, ?, ?)
                """,
                (category, subcategory, now_iso()),
            )

    def _available_category_pairs(self, conn: sqlite3.Connection | None = None) -> list[tuple[str, str]]:
        close_conn = False
        if conn is None:
            conn = self._connect()
            close_conn = True
        try:
            pairs = {(category, subcategory) for category, subcategories in default_categories().items() for subcategory in subcategories}
            rows = conn.execute("SELECT category, subcategory FROM custom_categories").fetchall()
            for row in rows:
                pairs.add((row["category"], row["subcategory"] or "General"))
            return sorted(pairs)
        finally:
            if close_conn:
                conn.close()

    def fetch_note_plaintext(self, note_id: str, limit: int = 24000) -> str:
        script = f"""
        tell application "Notes"
            set textValue to plaintext of note id "{apple_escape(note_id)}"
        end tell
        if (length of textValue) > {limit} then
            set textValue to text 1 thru {limit} of textValue
        end if
        return textValue
        """
        return run_osascript(script, timeout=90)

    def move_note(self, note_id: str, category: str, subcategory: str = "") -> None:
        category = normalize_spaces(category)
        subcategory = normalize_spaces(subcategory or "General")
        if not note_id or not category:
            raise ValueError("Note id and category are required")
        self.create_category(category, subcategory)
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO note_overrides(note_id, category, subcategory, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(note_id) DO UPDATE SET
                    category = excluded.category,
                    subcategory = excluded.subcategory,
                    updated_at = excluded.updated_at
                """,
                (note_id, category, subcategory, now_iso()),
            )

    def recategorize_uncategorized_blocking(self) -> dict[str, int]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    n.note_id,
                    n.account_name,
                    n.folder_name,
                    n.note_index,
                    n.original_name,
                    n.preview_text,
                    n.search_text
                FROM notes n
                LEFT JOIN note_overrides o ON o.note_id = n.note_id
                WHERE n.is_active = 1
                  AND o.note_id IS NULL
                  AND (
                    n.category = 'Uncategorized'
                    OR (
                        n.category = 'Writing'
                        AND n.subcategory = 'Drafts & essays'
                        AND n.classifier_confidence <= 0.13
                    )
                  )
                  AND n.password_protected = 0
                ORDER BY n.folder_name, n.note_index
                """
            ).fetchall()

        total = len(rows)
        self.sync.start("recategorize", f"Deep-reading {total} uncategorized notes", total=total)
        if total == 0:
            self.sync.finish("No uncategorized notes needed recategorization.")
            return {"total": 0, "updated": 0, "remaining": 0}

        notes = [dict(row) for row in rows]
        updates: list[dict[str, Any]] = []
        remaining_for_notes_read: list[dict[str, Any]] = []
        for note in notes:
            cached_text = note.get("search_text") or note.get("preview_text") or ""
            if not cached_text.strip():
                remaining_for_notes_read.append(note)
                continue
            classified = classify_note(note["original_name"], cached_text, force_category=True)
            if classified["category"] == "Uncategorized":
                remaining_for_notes_read.append(note)
                continue
            updates.append(
                {
                    "note_id": note["note_id"],
                    "generated_title": classified["generated_title"],
                    "preview_text": classified["preview_text"],
                    "search_text": classified["search_text"],
                    "category": classified["category"],
                    "subcategory": classified["subcategory"],
                    "classifier_confidence": classified["confidence"],
                    "last_synced_at": now_iso(),
                }
            )

        by_folder: dict[tuple[str, str], list[int]] = defaultdict(list)
        by_id = {note["note_id"]: note for note in remaining_for_notes_read}
        for note in remaining_for_notes_read:
            by_folder[(note["account_name"], note["folder_name"])].append(int(note["note_index"]))

        processed = len(notes) - len(remaining_for_notes_read)
        self.sync.update(current=processed)
        for (account_name, folder_name), indexes in by_folder.items():
            self.sync.update(message=f"Reading {account_name} / {folder_name}")
            for chunk in self._chunks(sorted(indexes), MAX_SNIPPET_BATCH):
                snippet_rows = self.fetch_snippet_indexes(account_name, folder_name, chunk)
                for row in snippet_rows:
                    note = by_id.get(row["note_id"])
                    if not note:
                        continue
                    classified = classify_note(note["original_name"], row["snippet"], force_category=True)
                    if classified["category"] == "Uncategorized":
                        continue
                    updates.append(
                        {
                            "note_id": note["note_id"],
                            "generated_title": classified["generated_title"],
                            "preview_text": classified["preview_text"],
                            "search_text": classified["search_text"],
                            "category": classified["category"],
                            "subcategory": classified["subcategory"],
                            "classifier_confidence": classified["confidence"],
                            "last_synced_at": now_iso(),
                        }
                    )
                processed += len(chunk)
                self.sync.update(current=min(processed, total))

        with self._connect() as conn:
            conn.executemany(
                """
                UPDATE notes
                SET generated_title = :generated_title,
                    preview_text = :preview_text,
                    search_text = :search_text,
                    category = :category,
                    subcategory = :subcategory,
                    classifier_confidence = :classifier_confidence,
                    last_synced_at = :last_synced_at
                WHERE note_id = :note_id
                """,
                updates,
            )
            remaining = conn.execute(
                """
                SELECT COUNT(*) AS c
                FROM notes n
                LEFT JOIN note_overrides o ON o.note_id = n.note_id
                WHERE n.is_active = 1
                  AND COALESCE(o.category, n.category) = 'Uncategorized'
                """
            ).fetchone()["c"]

        summary = f"Recategorized {len(updates)} of {total} uncategorized notes. {remaining} remain uncategorized."
        self.sync.finish(summary)
        return {"total": total, "updated": len(updates), "remaining": int(remaining)}

    def suggest_categories(self, note_id: str, limit: int = 3) -> dict[str, Any]:
        if not note_id:
            raise ValueError("Note id is required")
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT
                    n.note_id,
                    n.original_name,
                    n.generated_title,
                    n.preview_text,
                    n.search_text,
                    COALESCE(o.category, n.category) AS category,
                    COALESCE(NULLIF(o.subcategory, ''), n.subcategory) AS subcategory
                FROM notes n
                LEFT JOIN note_overrides o ON o.note_id = n.note_id
                WHERE n.note_id = ? AND n.is_active = 1
                """,
                (note_id,),
            ).fetchone()
            if row is None:
                raise ValueError("Note not found in catalog")
            available_pairs = self._available_category_pairs(conn)

        title = row["generated_title"] or row["original_name"] or "Untitled note"
        full_text = ""
        try:
            full_text = self.fetch_note_plaintext(note_id)
        except Exception:
            full_text = row["search_text"] or row["preview_text"] or row["original_name"]

        suggestions = rank_category_suggestions(
            title=row["original_name"] or title,
            text=full_text,
            available_pairs=available_pairs,
            limit=limit,
        )
        seen: set[tuple[str, str]] = set()
        unique_suggestions = []
        for suggestion in suggestions:
            key = (suggestion["category"], suggestion["subcategory"])
            if key in seen:
                continue
            seen.add(key)
            unique_suggestions.append(suggestion)
        return {
            "note_id": row["note_id"],
            "title": title,
            "current_category": row["category"],
            "current_subcategory": row["subcategory"],
            "suggestions": unique_suggestions[:limit],
        }

    def mind_map_meta(self) -> dict[str, Any]:
        with self._connect() as conn:
            active_notes = conn.execute("SELECT COUNT(*) AS c FROM notes WHERE is_active = 1").fetchone()["c"]
            categories = conn.execute(
                """
                SELECT COUNT(DISTINCT COALESCE(o.category, n.category)) AS c
                FROM notes n
                LEFT JOIN note_overrides o ON o.note_id = n.note_id
                WHERE n.is_active = 1
                """
            ).fetchone()["c"]
            subcategories = conn.execute(
                """
                SELECT COUNT(*) AS c
                FROM (
                    SELECT DISTINCT
                        COALESCE(o.category, n.category) AS category,
                        COALESCE(NULLIF(o.subcategory, ''), n.subcategory) AS subcategory
                    FROM notes n
                    LEFT JOIN note_overrides o ON o.note_id = n.note_id
                    WHERE n.is_active = 1
                )
                """
            ).fetchone()["c"]
        return {
            "active_notes": int(active_notes),
            "categories": int(categories),
            "subcategories": int(subcategories),
            "methodology": "Builds a local graph from category, subcategory, note, and recurring keyword nodes. Notes are linked to their local category path and to concept hubs extracted from cached titles and snippets.",
        }

    def build_mind_map(self) -> dict[str, Any]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    n.note_id,
                    n.generated_title,
                    n.original_name,
                    n.preview_text,
                    n.search_text,
                    n.folder_name,
                    n.modified_at,
                    n.classifier_confidence,
                    COALESCE(o.category, n.category) AS category,
                    COALESCE(NULLIF(o.subcategory, ''), n.subcategory) AS subcategory
                FROM notes n
                LEFT JOIN note_overrides o ON o.note_id = n.note_id
                WHERE n.is_active = 1
                ORDER BY category, subcategory, n.modified_at DESC
                """
            ).fetchall()

        category_counts: Counter[str] = Counter()
        subcategory_counts: Counter[tuple[str, str]] = Counter()
        concept_counts: Counter[str] = Counter()
        note_keywords: dict[str, list[str]] = {}
        blocked_concepts = {
            "note",
            "notes",
            "new",
            "version",
            "things",
            "thing",
            "there",
            "like",
            "know",
            "want",
            "make",
            "because",
            "only",
            "need",
            "something",
            "really",
            "always",
            "every",
            "following",
        }

        for row in rows:
            category = row["category"] or "Uncategorized"
            subcategory = row["subcategory"] or "General"
            category_counts[category] += 1
            subcategory_counts[(category, subcategory)] += 1
            source = f"{row['generated_title']} {row['original_name']} {row['preview_text']} {ensure_text(row['search_text'])[:900]}"
            keywords = []
            for keyword in extract_keywords(source, limit=7):
                if keyword in blocked_concepts or len(keyword) < 4:
                    continue
                keywords.append(keyword)
            unique_keywords = list(dict.fromkeys(keywords))[:5]
            note_keywords[row["note_id"]] = unique_keywords
            concept_counts.update(unique_keywords)

        top_concepts = {
            keyword
            for keyword, count in concept_counts.most_common(220)
            if count >= 8
        }

        palette = [
            "#69e4ff",
            "#f6cf65",
            "#ff6f91",
            "#90f18a",
            "#b69cff",
            "#f78fb3",
            "#7df6d8",
            "#ff9b6a",
            "#93b7ff",
            "#d4f56a",
        ]
        category_palette = {
            category: palette[index % len(palette)]
            for index, category in enumerate(sorted(category_counts))
        }

        nodes: list[dict[str, Any]] = [
            {
                "id": "root:notes-atlas",
                "type": "root",
                "label": "Notes Atlas",
                "count": len(rows),
                "size": 28,
                "color": "#ffffff",
            }
        ]
        links: list[dict[str, Any]] = []

        for category, count in sorted(category_counts.items()):
            category_id = f"category:{category}"
            color = category_palette[category]
            nodes.append(
                {
                    "id": category_id,
                    "type": "category",
                    "label": category,
                    "count": count,
                    "size": min(26, 9 + int(count ** 0.34)),
                    "color": color,
                }
            )
            links.append({"source": "root:notes-atlas", "target": category_id, "type": "category", "weight": 2.4})

        for (category, subcategory), count in sorted(subcategory_counts.items()):
            subcategory_id = f"subcategory:{category}/{subcategory}"
            nodes.append(
                {
                    "id": subcategory_id,
                    "type": "subcategory",
                    "label": subcategory,
                    "category": category,
                    "count": count,
                    "size": min(20, 7 + int(count ** 0.32)),
                    "color": category_palette.get(category, "#69e4ff"),
                }
            )
            links.append(
                {
                    "source": f"category:{category}",
                    "target": subcategory_id,
                    "type": "subcategory",
                    "weight": 1.8,
                }
            )

        for keyword, count in sorted(concept_counts.items()):
            if keyword not in top_concepts:
                continue
            nodes.append(
                {
                    "id": f"concept:{keyword}",
                    "type": "concept",
                    "label": keyword.title(),
                    "count": count,
                    "size": min(15, 5 + int(count ** 0.3)),
                    "color": "#d7f56f",
                }
            )

        for row in rows:
            category = row["category"] or "Uncategorized"
            subcategory = row["subcategory"] or "General"
            note_id = row["note_id"]
            graph_note_id = f"note:{note_id}"
            title = row["generated_title"] or row["original_name"] or "Untitled note"
            nodes.append(
                {
                    "id": graph_note_id,
                    "type": "note",
                    "label": clip_text(title, 92),
                    "note_id": note_id,
                    "category": category,
                    "subcategory": subcategory,
                    "folder": row["folder_name"],
                    "modified_at": row["modified_at"],
                    "snippet": clip_text(row["preview_text"] or row["search_text"] or row["original_name"], 210),
                    "confidence": row["classifier_confidence"],
                    "size": 3.8,
                    "color": category_palette.get(category, "#69e4ff"),
                }
            )
            links.append(
                {
                    "source": f"subcategory:{category}/{subcategory}",
                    "target": graph_note_id,
                    "type": "note",
                    "weight": 0.42,
                }
            )
            for keyword in note_keywords.get(note_id, [])[:3]:
                if keyword in top_concepts:
                    links.append(
                        {
                            "source": graph_note_id,
                            "target": f"concept:{keyword}",
                            "type": "concept",
                            "weight": 0.18,
                        }
                    )

        return {
            "generated_at": now_iso(),
            "methodology": {
                "summary": "Local interactive mind map generated from the Notes Atlas SQLite catalog.",
                "steps": [
                    "Every active note becomes a note node.",
                    "Category and subcategory nodes provide the stable local taxonomy.",
                    "Recurring keywords from generated titles, original titles, snippets, and cached search text become concept hubs.",
                    "Links connect category to subcategory, subcategory to note, and note to shared concept hubs.",
                    "Clicking a note node calls the same local Notes-opening endpoint used by the catalog list.",
                ],
            },
            "counts": {
                "notes": len(rows),
                "categories": len(category_counts),
                "subcategories": len(subcategory_counts),
                "concepts": len(top_concepts),
                "nodes": len(nodes),
                "links": len(links),
            },
            "nodes": nodes,
            "links": links,
        }

    def open_note(self, note_id: str) -> None:
        script = f"""
        tell application "Notes"
            activate
            try
                set targetNote to note id "{apple_escape(note_id)}"
                show targetNote separately false
            on error
                open note location "{apple_escape(note_id)}"
            end try
        end tell
        """
        run_osascript(script, timeout=60)
        with self._connect() as conn:
            conn.execute("UPDATE notes SET opened_at = ? WHERE note_id = ?", (now_iso(), note_id))
