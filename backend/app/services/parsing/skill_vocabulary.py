import re
from typing import Dict, List, Optional, Tuple

# Canonical display name -> surface forms found in resumes and job descriptions.
# The canonical name is what gets stored and shown, so matching is case- and
# spelling-tolerant while output stays consistent ("FastAPI", never "Fastapi").
SKILL_ALIASES: Dict[str, Tuple[str, ...]] = {
    "Python": ("python",),
    "FastAPI": ("fastapi", "fast api"),
    "Django": ("django",),
    "Flask": ("flask",),
    "PostgreSQL": ("postgresql", "postgres", "psql"),
    "MySQL": ("mysql",),
    "MongoDB": ("mongodb", "mongo"),
    "Redis": ("redis",),
    "Elasticsearch": ("elasticsearch", "elastic search"),
    "Docker": ("docker",),
    "Kubernetes": ("kubernetes", "k8s"),
    "AWS": ("aws", "amazon web services"),
    "Azure": ("azure",),
    "GCP": ("gcp", "google cloud"),
    "Terraform": ("terraform",),
    "React": ("react", "react.js", "reactjs"),
    "Next.js": ("next.js", "nextjs"),
    "TypeScript": ("typescript", "ts"),
    "JavaScript": ("javascript", "js"),
    "Node.js": ("node.js", "nodejs", "node"),
    "SQL": ("sql",),
    "GraphQL": ("graphql",),
    "REST API": ("rest api", "restful api", "rest apis", "api design", "apis"),
    "CI/CD": ("ci/cd", "cicd", "continuous integration"),
    "Git": ("git",),
    "Linux": ("linux", "unix"),
    "Spark": ("spark", "apache spark"),
    "Machine Learning": ("machine learning", "ml"),
    "Deep Learning": ("deep learning",),
    "NLP": ("nlp", "natural language processing"),
    "LLM": ("llm", "llms", "large language model", "large language models"),
    "RAG": ("rag", "retrieval-augmented generation", "retrieval augmented generation"),
    "Data Engineering": ("data engineering",),
    # Plural forms are listed explicitly rather than allowing a blanket trailing
    # "s", which would make verbs like "reacts" match React.
    "Microservices": ("microservices", "micro services", "microservice"),
    "Backend": ("backend", "back-end", "backends", "back-ends"),
    "Frontend": ("frontend", "front-end", "frontends", "front-ends"),
    "Java": ("java",),
    "Go": ("golang",),
    "C++": ("c\\+\\+",),
    "Celery": ("celery",),
    "RabbitMQ": ("rabbitmq",),
    "Kafka": ("kafka", "apache kafka"),
    "Airflow": ("airflow", "apache airflow"),
    "Express.js": ("express.js", "expressjs", "express"),
    "Tailwind CSS": ("tailwind css", "tailwindcss", "tailwind"),
    "Jenkins": ("jenkins",),
    "Snowflake": ("snowflake",),
    "Databricks": ("databricks",),
    "Pandas": ("pandas",),
    "NumPy": ("numpy",),
    "PyTorch": ("pytorch",),
    "TensorFlow": ("tensorflow", "tensor flow"),
    "Scala": ("scala",),
    "Firebase": ("firebase",),
    "Redux": ("redux",),
}

# Longer aliases are tested first so "google cloud" is not shadowed by a
# shorter overlapping term. The lookbehind also rejects a preceding dot, so the
# "js" alias does not fire inside "Express.js"; a trailing dot stays allowed
# because skills routinely end a sentence ("... built in Python.").
_COMPILED: List[Tuple[str, re.Pattern]] = sorted(
    (
        (canonical, re.compile(rf"(?<![\w+#.]){alias}(?![\w+#])", re.IGNORECASE))
        for canonical, aliases in SKILL_ALIASES.items()
        for alias in aliases
    ),
    key=lambda item: -len(item[1].pattern),
)


def find_skills(text: str) -> List[str]:
    """Return the canonical names of every known skill mentioned in `text`."""
    if not text:
        return []

    found: List[str] = []
    for canonical, pattern in _COMPILED:
        if canonical not in found and pattern.search(text):
            found.append(canonical)
    return sorted(found)


# Soft skills are only reported when the resume actually mentions them. The
# parser used to return a fixed list for every candidate, which was fiction.
SOFT_SKILL_ALIASES: Dict[str, Tuple[str, ...]] = {
    "Communication": ("communication", "communicating", "verbal communication"),
    "Leadership": ("leadership", "led a team", "team lead", "leading teams"),
    "Teamwork": ("teamwork", "collaboration", "collaborative", "cross-functional"),
    "Problem Solving": ("problem solving", "problem-solving", "analytical thinking"),
    "Mentoring": ("mentoring", "mentored", "coaching"),
    "Stakeholder Management": ("stakeholder management", "stakeholder communication", "client management"),
    "Time Management": ("time management", "prioritisation", "prioritization"),
    "Adaptability": ("adaptability", "adaptable", "flexibility"),
    "Critical Thinking": ("critical thinking",),
    "Presentation": ("presentation skills", "public speaking", "presenting"),
    "Ownership": ("ownership", "self-driven", "self driven", "proactive"),
    "Agile": ("agile", "scrum", "kanban"),
}

_COMPILED_SOFT: List[Tuple[str, re.Pattern]] = sorted(
    (
        (canonical, re.compile(rf"(?<![\w-]){alias}(?![\w-])", re.IGNORECASE))
        for canonical, aliases in SOFT_SKILL_ALIASES.items()
        for alias in aliases
    ),
    key=lambda item: -len(item[1].pattern),
)


def find_soft_skills(text: str) -> List[str]:
    """Return soft skills the resume actually mentions, not a fixed list."""
    if not text:
        return []

    found: List[str] = []
    for canonical, pattern in _COMPILED_SOFT:
        if canonical not in found and pattern.search(text):
            found.append(canonical)
    return sorted(found)


# Category of each canonical skill. Used to award partial credit when a resume
# covers the same area with a different tool - a JD asking for Kubernetes is
# partly satisfied by Docker experience.
SKILL_CATEGORIES: Dict[str, str] = {
    "Python": "language", "TypeScript": "language", "JavaScript": "language",
    "Java": "language", "Go": "language", "C++": "language", "Scala": "language",
    "SQL": "language",

    "FastAPI": "web-framework", "Django": "web-framework", "Flask": "web-framework",
    "Node.js": "web-framework", "Express.js": "web-framework",

    "React": "frontend", "Next.js": "frontend", "Redux": "frontend",
    "Tailwind CSS": "frontend", "Frontend": "discipline", "Backend": "discipline",

    "PostgreSQL": "database", "MySQL": "database", "MongoDB": "database",
    "Redis": "database", "Elasticsearch": "database", "Snowflake": "database",

    "Docker": "containers", "Kubernetes": "containers",

    "AWS": "cloud", "Azure": "cloud", "GCP": "cloud", "Firebase": "cloud",
    "Terraform": "infrastructure",

    "CI/CD": "devops", "Jenkins": "devops", "Git": "tooling", "Linux": "tooling",

    "Kafka": "messaging", "RabbitMQ": "messaging", "Celery": "messaging",

    "Spark": "data", "Airflow": "data", "Databricks": "data",
    "Pandas": "data", "NumPy": "data", "Data Engineering": "data",

    "Machine Learning": "ai-ml", "Deep Learning": "ai-ml", "NLP": "ai-ml",
    "LLM": "ai-ml", "RAG": "ai-ml", "PyTorch": "ai-ml", "TensorFlow": "ai-ml",

    "REST API": "api", "GraphQL": "api",
    "Microservices": "architecture",
}

# Categories where one tool is a genuine partial substitute for another.
# "language" is excluded on purpose: knowing Java says little about a Python
# role, so crediting it would inflate the score.
PARTIAL_CREDIT_CATEGORIES = frozenset({
    "web-framework", "frontend", "database", "containers", "cloud",
    "infrastructure", "devops", "messaging", "data", "ai-ml", "api",
})


def category_of(skill: str) -> Optional[str]:
    """Category of a skill, accepting either a canonical name or an alias."""
    if not skill:
        return None
    direct = SKILL_CATEGORIES.get(skill)
    if direct:
        return direct
    return SKILL_CATEGORIES.get(normalize_skill(skill))


def supports_partial_credit(category: Optional[str]) -> bool:
    return bool(category) and category in PARTIAL_CREDIT_CATEGORIES


def normalize_skill(name: str) -> str:
    """Map a free-form skill name onto its canonical form, if it is known."""
    candidate = (name or "").strip()
    if not candidate:
        return ""
    for canonical, pattern in _COMPILED:
        if pattern.fullmatch(candidate):
            return canonical
    return candidate
