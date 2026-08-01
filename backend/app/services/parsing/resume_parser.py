import re
from typing import Any, Dict, List


class ResumeParserService:
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
            "personal_info": {
                "name": self._extract_name(text),
                "email": self._extract_email(text),
            },
            "skills": {
                "hard_skills": skills,
                "soft_skills": ["communication", "leadership", "problem solving"],
            },
            "experience": self._extract_experience(text),
            "education": self._extract_education(normalized),
            "projects": self._extract_projects(text),
            "certifications": self._extract_certifications(text),
            "experience_years": self._extract_experience_years(normalized),
        }

    async def parse_bytes(self, file_bytes: bytes) -> Dict[str, Any]:
        try:
            text = file_bytes.decode("utf-8")
        except UnicodeDecodeError:
            text = file_bytes.decode("latin-1", errors="ignore")
        return await self.parse(text)

    def _normalize(self, text: str) -> str:
        return re.sub(r"\s+", " ", text or "").strip().lower()

    def _extract_name(self, text: str) -> str:
        lines = [line.strip() for line in (text or "").splitlines() if line.strip()]
        return lines[0] if lines else ""

    def _extract_email(self, text: str) -> str:
        match = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text or "")
        return match.group(0) if match else ""

    def _extract_skills(self, text: str) -> List[str]:
        found = []
        for skill in self.TECH_SKILLS:
            if re.search(rf"\b{re.escape(skill)}\b", text):
                found.append(skill.capitalize() if skill not in {"ci/cd", "nodejs", "api"} else skill)
        return found

    def _extract_experience(self, text: str) -> List[Dict[str, Any]]:
        lines = [line.strip() for line in (text or "").splitlines() if line.strip()]
        roles = []
        for line in lines:
            if line.lower().startswith(("experience", "work", "professional")):
                continue
            if re.search(r"engineer|developer|manager|lead|analyst|architect", line, re.I):
                roles.append({
                    "role": line,
                    "company": "",
                    "highlights": [],
                })
        return roles[:3]

    def _extract_education(self, text: str) -> List[str]:
        education_terms = ["bachelor", "master", "phd", "university", "college"]
        return [term for term in education_terms if term in text]

    def _extract_projects(self, text: str) -> List[str]:
        return [line for line in (text or "").splitlines() if line.strip() and len(line.split()) >= 3][:3]

    def _extract_certifications(self, text: str) -> List[str]:
        cert_terms = ["certified", "aws", "azure", "google"]
        return [term for term in cert_terms if term in (text or "").lower()]

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
