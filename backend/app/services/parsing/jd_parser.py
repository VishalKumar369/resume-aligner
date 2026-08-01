import re
from typing import Any, Dict, List


class JDParserService:
    TECH_SKILLS = [
        "python", "fastapi", "postgresql", "docker", "kubernetes", "aws", "react",
        "typescript", "javascript", "nodejs", "node", "sql", "redis", "graphql",
        "ci/cd", "git", "linux", "elasticsearch", "spark", "machine learning",
        "data engineering", "backend", "api", "microservices"
    ]

    async def parse(self, text: str) -> Dict[str, Any]:
        normalized = self._normalize(text)
        skills = self._extract_skills(normalized)
        return {
            "role": self._extract_role(text),
            "company": self._extract_company(text),
            "experience_level": self._extract_experience_level(text),
            "requirements": {
                "mandatory": skills,
                "preferred": self._extract_optional_skills(normalized),
            },
            "responsibilities": self._extract_responsibilities(text),
            "keywords": skills,
            "experience_years": self._extract_experience_years(normalized),
        }

    def _normalize(self, text: str) -> str:
        return re.sub(r"\s+", " ", text or "").strip().lower()

    def _extract_role(self, text: str) -> str:
        lines = [line.strip() for line in (text or "").splitlines() if line.strip()]
        for line in lines:
            if re.search(r"engineer|developer|manager|lead|analyst|architect", line, re.I):
                return line
        return ""

    def _extract_company(self, text: str) -> str:
        match = re.search(r"company\s*[:\-]\s*(.+)", (text or ""), re.I)
        return match.group(1).strip() if match else ""

    def _extract_optional_skills(self, text: str) -> List[str]:
        optional_terms = ["plus", "bonus", "preferred", "nice to have"]
        return [term for term in optional_terms if term in text]

    def _extract_responsibilities(self, text: str) -> List[str]:
        parts = [part.strip() for part in re.split(r"(?<=[.?!])\s+", text) if part.strip()]
        return [part for part in parts if len(part.split()) >= 4][:6]

    def _extract_experience_level(self, text: str) -> str:
        if re.search(r"5\+\s*years?|senior", text, re.I):
            return "Senior (5+ years)"
        if re.search(r"3\+\s*years?|mid", text, re.I):
            return "Mid (3+ years)"
        return "Entry"

    def _extract_experience_years(self, text: str) -> int:
        patterns = [
            r"(\d+)\s*\+?\s*years?",
            r"(\d+)\s*years?\s*of\s*experience",
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return int(match.group(1))
        return 0

    def _extract_skills(self, text: str) -> List[str]:
        found = []
        for skill in self.TECH_SKILLS:
            if re.search(rf"\b{re.escape(skill)}\b", text):
                found.append(skill.capitalize() if skill not in {"ci/cd", "nodejs", "api"} else skill)
        return found
