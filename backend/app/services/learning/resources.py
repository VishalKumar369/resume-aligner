"""Curated learning resources.

Every entry is the skill's own official documentation. That is a deliberate
constraint: the previous stub returned invented links like
"https://coursera.org/..." for a course that does not exist, and an LLM asked
for course recommendations hallucinates titles and URLs just as readily.

Official docs are free, stable, authoritative, and verifiable. A skill with no
entry here returns **no** resource rather than a plausible-looking guess.
"""

from typing import Dict, List, Optional

# skill (canonical name) -> (title, url)
SKILL_RESOURCES: Dict[str, tuple] = {
    "Python": ("Python Official Tutorial", "https://docs.python.org/3/tutorial/"),
    "TypeScript": ("TypeScript Handbook", "https://www.typescriptlang.org/docs/handbook/intro.html"),
    "JavaScript": ("MDN JavaScript Guide", "https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide"),
    "Java": ("Java Tutorials", "https://docs.oracle.com/javase/tutorial/"),
    "Go": ("A Tour of Go", "https://go.dev/tour/"),
    "Scala": ("Scala Documentation", "https://docs.scala-lang.org/"),
    "SQL": ("PostgreSQL SQL Tutorial", "https://www.postgresql.org/docs/current/tutorial-sql.html"),

    "FastAPI": ("FastAPI Documentation", "https://fastapi.tiangolo.com/"),
    "Django": ("Django Documentation", "https://docs.djangoproject.com/en/stable/"),
    "Flask": ("Flask Documentation", "https://flask.palletsprojects.com/"),
    "Node.js": ("Node.js Learn", "https://nodejs.org/en/learn"),
    "Express.js": ("Express Guide", "https://expressjs.com/en/guide/routing.html"),

    "React": ("React Documentation", "https://react.dev/learn"),
    "Next.js": ("Next.js Documentation", "https://nextjs.org/docs"),
    "Redux": ("Redux Essentials", "https://redux.js.org/tutorials/essentials/part-1-overview-concepts"),
    "Tailwind CSS": ("Tailwind CSS Documentation", "https://tailwindcss.com/docs"),

    "PostgreSQL": ("PostgreSQL Documentation", "https://www.postgresql.org/docs/current/"),
    "MySQL": ("MySQL Reference Manual", "https://dev.mysql.com/doc/refman/8.0/en/"),
    "MongoDB": ("MongoDB Manual", "https://www.mongodb.com/docs/manual/"),
    "Redis": ("Redis Documentation", "https://redis.io/docs/latest/"),
    "Elasticsearch": ("Elasticsearch Guide", "https://www.elastic.co/guide/en/elasticsearch/reference/current/index.html"),
    "Snowflake": ("Snowflake Documentation", "https://docs.snowflake.com/"),

    "Docker": ("Docker Documentation", "https://docs.docker.com/"),
    "Kubernetes": ("Kubernetes Documentation", "https://kubernetes.io/docs/home/"),
    "Terraform": ("Terraform Documentation", "https://developer.hashicorp.com/terraform/docs"),
    "Jenkins": ("Jenkins User Documentation", "https://www.jenkins.io/doc/"),
    "CI/CD": ("GitHub Actions Documentation", "https://docs.github.com/en/actions"),
    "Git": ("Pro Git Book", "https://git-scm.com/book/en/v2"),
    "Linux": ("The Linux Documentation Project", "https://tldp.org/guides.html"),

    "AWS": ("AWS Documentation", "https://docs.aws.amazon.com/"),
    "Azure": ("Azure Documentation", "https://learn.microsoft.com/en-us/azure/"),
    "GCP": ("Google Cloud Documentation", "https://cloud.google.com/docs"),
    "Firebase": ("Firebase Documentation", "https://firebase.google.com/docs"),

    "Kafka": ("Apache Kafka Documentation", "https://kafka.apache.org/documentation/"),
    "RabbitMQ": ("RabbitMQ Tutorials", "https://www.rabbitmq.com/tutorials"),
    "Celery": ("Celery Documentation", "https://docs.celeryq.dev/en/stable/"),

    "Spark": ("Apache Spark Documentation", "https://spark.apache.org/docs/latest/"),
    "Airflow": ("Apache Airflow Documentation", "https://airflow.apache.org/docs/"),
    "Databricks": ("Databricks Documentation", "https://docs.databricks.com/"),
    "Pandas": ("pandas User Guide", "https://pandas.pydata.org/docs/user_guide/index.html"),
    "NumPy": ("NumPy Documentation", "https://numpy.org/doc/stable/"),
    "PyTorch": ("PyTorch Tutorials", "https://pytorch.org/tutorials/"),
    "TensorFlow": ("TensorFlow Tutorials", "https://www.tensorflow.org/tutorials"),

    "GraphQL": ("GraphQL Learn", "https://graphql.org/learn/"),
    "REST API": ("MDN HTTP Guide", "https://developer.mozilla.org/en-US/docs/Web/HTTP"),
}

# Human-readable module names for the vocabulary categories.
CATEGORY_MODULES: Dict[str, str] = {
    "containers": "Containerisation & Orchestration",
    "cloud": "Cloud Platforms",
    "infrastructure": "Infrastructure as Code",
    "devops": "CI/CD & Automation",
    "database": "Databases & Storage",
    "web-framework": "Backend Frameworks",
    "frontend": "Frontend Engineering",
    "language": "Programming Languages",
    "messaging": "Event Streaming & Messaging",
    "data": "Data Engineering",
    "ai-ml": "AI & Machine Learning",
    "api": "API Design",
    "architecture": "System Architecture",
    "tooling": "Developer Tooling",
    "discipline": "Engineering Breadth",
    "other": "Additional Skills",
}

# Learn the left skill before the right one. Used to order modules so a
# prerequisite never comes after the thing that depends on it.
PREREQUISITES: Dict[str, str] = {
    "FastAPI": "Python",
    "Django": "Python",
    "Flask": "Python",
    "Pandas": "Python",
    "NumPy": "Python",
    "PyTorch": "Python",
    "TensorFlow": "Python",
    "Kubernetes": "Docker",
    "Terraform": "AWS",
    "Next.js": "React",
    "Redux": "React",
    "Express.js": "Node.js",
}


def resource_for(skill: str) -> Optional[Dict[str, str]]:
    """The official documentation for a skill, or None if we have no entry."""
    entry = SKILL_RESOURCES.get(skill)
    if not entry:
        return None
    title, url = entry
    return {"skill": skill, "title": title, "url": url}


def resources_for(skills: List[str]) -> List[Dict[str, str]]:
    """Resources for the skills we know, silently skipping the ones we do not."""
    found = []
    seen = set()
    for skill in skills:
        resource = resource_for(skill)
        if resource and resource["url"] not in seen:
            seen.add(resource["url"])
            found.append(resource)
    return found


def module_name(category: Optional[str]) -> str:
    return CATEGORY_MODULES.get(category or "other", CATEGORY_MODULES["other"])


def prerequisite_of(skill: str) -> Optional[str]:
    return PREREQUISITES.get(skill)
