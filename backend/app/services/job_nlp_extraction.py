import re
from typing import Optional, List, Dict, Any, Tuple


# ==========================================
# 1. SKILL DICTIONARY & PRECOMPILED PATTERNS
# ==========================================

SKILL_DICTIONARY = {
    "Python": ["python"],
    "Java": ["java"],
    "C++": ["c++"],
    "JavaScript": ["javascript", "js"],
    "TypeScript": ["typescript"],
    "SQL": ["sql"],
    "PostgreSQL": ["postgresql", "postgres"],
    "MySQL": ["mysql"],
    "MongoDB": ["mongodb"],
    "FastAPI": ["fastapi"],
    "Flask": ["flask"],
    "Django": ["django"],
    "React": ["react", "react.js"],
    "Node.js": ["node.js", "nodejs"],
    "HTML": ["html"],
    "CSS": ["css"],
    "Machine Learning": ["machine learning", "ml"],
    "Deep Learning": ["deep learning"],
    "Natural Language Processing": ["natural language processing", "nlp"],
    "TensorFlow": ["tensorflow"],
    "PyTorch": ["pytorch"],
    "Scikit-learn": ["scikit-learn", "sklearn"],
    "Pandas": ["pandas"],
    "NumPy": ["numpy"],
    "Git": ["git"],
    "Docker": ["docker"],
    "AWS": ["aws"],
    "Azure": ["azure"],
    "REST API": ["rest api", "restful api"]
}

# Pre-compile skill patterns once at module load
COMPILED_SKILL_PATTERNS: Dict[str, List[Tuple[str, re.Pattern]]] = {
    skill_name: [
        (alias, re.compile(r"(?<![A-Za-z0-9])" + re.escape(alias) + r"(?![A-Za-z0-9])", re.IGNORECASE))
        for alias in aliases
    ]
    for skill_name, aliases in SKILL_DICTIONARY.items()
}

PREFERENCE_WORDS = (
    "preferred",
    "preferably",
    "nice to have",
    "good to have",
    "plus",
    "optional",
    "bonus"
)


# ==========================================
# 2. PRECOMPILED EXPERIENCE PATTERNS
# ==========================================

COMPILED_EXP_PATTERNS = [
    re.compile(r"(\d+)\s*[-–—]\s*(\d+)\s+years?", re.IGNORECASE),
    re.compile(r"(\d+)\s*\+\s*years?", re.IGNORECASE),
    re.compile(r"minimum\s+of\s+(\d+)\s+years?", re.IGNORECASE),
    re.compile(r"at\s+least\s+(\d+)\s+years?", re.IGNORECASE),
    re.compile(r"(\d+)\s+years?", re.IGNORECASE)
]

def extract_experience(text: str):
    for pattern in COMPILED_EXP_PATTERNS:
        match = pattern.search(text)
        if match:
            numbers = [int(v) for v in match.groups() if v is not None]
            if len(numbers) == 2:
                return numbers[0], numbers[1]
            if "+" in match.group(0):
                return numbers[0], None
            return numbers[0], numbers[0]
    return None, None


# ==========================================
# 3. PRECOMPILED JOB TITLE PATTERNS
# ==========================================

COMPILED_TITLE_PATTERNS = [
    re.compile(r"(?:job title|position|role)\s*:\s*([^\n.;]+)", re.IGNORECASE),
    re.compile(r"(?:hiring|looking for|seeking)\s+(?:an?\s+)?([A-Z][A-Za-z0-9 /&+-]{2,60})", re.IGNORECASE)
]

def extract_job_title(text: str) -> Optional[str]:
    for pattern in COMPILED_TITLE_PATTERNS:
        match = pattern.search(text)
        if match:
            return match.group(1).strip()
    return None


# ==========================================
# 4. PRECOMPILED EDUCATION PATTERNS
# ==========================================

COMPILED_EDUCATION_PATTERNS = [
    re.compile(r"\bB\.?\s?Tech\b", re.IGNORECASE),
    re.compile(r"\bM\.?\s?Tech\b", re.IGNORECASE),
    re.compile(r"\bB\.?\s?E\b", re.IGNORECASE),
    re.compile(r"\bM\.?\s?E\b", re.IGNORECASE),
    re.compile(r"\bBCA\b", re.IGNORECASE),
    re.compile(r"\bMCA\b", re.IGNORECASE),
    re.compile(r"\bB\.?\s?Sc\b", re.IGNORECASE),
    re.compile(r"\bM\.?\s?Sc\b", re.IGNORECASE),
    re.compile(r"\bMBA\b", re.IGNORECASE),
    re.compile(r"\bPh\.?\s?D\b", re.IGNORECASE),
    re.compile(r"\bBachelor(?:'s)?(?:\s+degree)?\b", re.IGNORECASE),
    re.compile(r"\bMaster(?:'s)?(?:\s+degree)?\b", re.IGNORECASE),
    re.compile(r"\bDiploma\b", re.IGNORECASE)
]

def extract_education(text: str):
    education = []
    seen = set()
    for pattern in COMPILED_EDUCATION_PATTERNS:
        for match in pattern.findall(text):
            normalized = match.strip()
            norm_lower = normalized.lower()
            if norm_lower not in seen:
                seen.add(norm_lower)
                education.append(normalized)
    return education


# ==========================================
# 5. SENTENCE SPLITTING
# ==========================================

SENTENCE_SPLIT_REGEX = re.compile(r"(?<=[.!?])\s+|\n+")

def split_sentences(text: str):
    return [s.strip() for s in SENTENCE_SPLIT_REGEX.split(text) if s.strip()]


# ==========================================
# 6. SKILL EXTRACTION (OPTIMIZED)
# ==========================================

def extract_skills(text: str):
    extracted_skills = {}
    text_lower = text.lower()
    sentences = None  # Lazily computed only if a skill is matched

    for skill_name, alias_patterns in COMPILED_SKILL_PATTERNS.items():
        # Fast substring pre-check before expensive regex
        if not any(alias in text_lower for alias, _ in alias_patterns):
            continue

        for alias, pattern in alias_patterns:
            if pattern.search(text):
                extracted_skills[skill_name] = "required"

                if sentences is None:
                    sentences = split_sentences(text)

                for sentence in sentences:
                    sentence_lower = sentence.lower()
                    if any(pw in sentence_lower for pw in PREFERENCE_WORDS):
                        if pattern.search(sentence):
                            extracted_skills[skill_name] = "preferred"
                            break
                break

    return [
        {"skill_name": skill, "skill_type": skill_type}
        for skill, skill_type in extracted_skills.items()
    ]


# ==========================================
# 7. RESPONSIBILITY EXTRACTION
# ==========================================

RESPONSIBILITY_KEYWORDS = (
    "responsible for",
    "develop",
    "design",
    "build",
    "implement",
    "manage",
    "maintain",
    "create",
    "analyze",
    "collaborate",
    "deploy",
    "optimize"
)

def extract_responsibilities(text: str):
    responsibilities = []
    seen = set()
    for sentence in split_sentences(text):
        sentence_lower = sentence.lower()
        if any(keyword in sentence_lower for keyword in RESPONSIBILITY_KEYWORDS):
            if sentence not in seen:
                seen.add(sentence)
                responsibilities.append(sentence)
    return responsibilities


# ==========================================
# 8. KEYWORD EXTRACTION
# ==========================================

STOP_WORDS = {
    "the", "and", "for", "with", "are",
    "you", "our", "your", "this", "that",
    "will", "have", "has", "from", "who",
    "what", "when", "where", "their",
    "they", "them", "a", "an", "to",
    "of", "in", "on", "at", "is", "be",
    "as", "or", "we", "us", "by"
}

WORD_REGEX = re.compile(r"\b[A-Za-z][A-Za-z0-9+#.-]*\b")

def extract_keywords(text: str):
    text_lower = text.lower()
    words = WORD_REGEX.findall(text_lower)
    keywords = set()

    for word in words:
        if len(word) > 2 and word not in STOP_WORDS:
            keywords.add(word)

    for skill in SKILL_DICTIONARY:
        if skill.lower() in text_lower:
            keywords.add(skill)

    return sorted(keywords)[:30]


# ==========================================
# 9. MAIN NLP EXTRACTION FUNCTION
# ==========================================

def extract_job_details(text: str):
    if not text or not text.strip():
        raise ValueError("Job description cannot be empty.")

    min_experience, max_experience = extract_experience(text)

    return {
        "title": extract_job_title(text),
        "min_experience": min_experience,
        "max_experience": max_experience,
        "education": extract_education(text),
        "responsibilities": extract_responsibilities(text),
        "keywords": extract_keywords(text),
        "skills": extract_skills(text)
    }
