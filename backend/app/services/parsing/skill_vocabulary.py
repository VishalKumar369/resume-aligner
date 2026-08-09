import re
from typing import Dict, List, Tuple

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
    "REST API": ("rest api", "restful api", "rest apis", "api design"),
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
    "Microservices": ("microservices", "micro services"),
    "Backend": ("backend", "back-end"),
    "Frontend": ("frontend", "front-end"),
    "Java": ("java",),
    "Go": ("golang",),
    "C++": ("c\\+\\+",),
    "Celery": ("celery",),
    "RabbitMQ": ("rabbitmq",),
    "Kafka": ("kafka", "apache kafka"),
}

# Longer aliases are tested first so "google cloud" is not shadowed by a
# shorter overlapping term.
_COMPILED: List[Tuple[str, re.Pattern]] = sorted(
    (
        (canonical, re.compile(rf"(?<![\w+#]){alias}(?![\w+#])", re.IGNORECASE))
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


def normalize_skill(name: str) -> str:
    """Map a free-form skill name onto its canonical form, if it is known."""
    candidate = (name or "").strip()
    if not candidate:
        return ""
    for canonical, pattern in _COMPILED:
        if pattern.fullmatch(candidate):
            return canonical
    return candidate
