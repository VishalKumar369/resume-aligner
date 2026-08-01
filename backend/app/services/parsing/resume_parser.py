import re
from typing import Any, Dict, List, Optional


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
        text = self._decode_text(file_bytes)
        return await self.parse(text)

    def _decode_text(self, file_bytes: bytes, filename: Optional[str] = None, content_type: Optional[str] = None) -> str:
        if self._looks_like_binary(file_bytes, filename=filename, content_type=content_type):
            fallback_name = filename or "uploaded file"
            return f"[Binary or non-text content stored as file reference only for {fallback_name}]"

        for encoding in ("utf-8", "utf-8-sig", "utf-16", "utf-16-le", "utf-16-be", "cp1252"):
            try:
                decoded = file_bytes.decode(encoding)
                return self._sanitize_text(decoded)
            except UnicodeDecodeError:
                continue
        return self._sanitize_text(file_bytes.decode("latin-1", errors="ignore"))

    def _looks_like_binary(self, file_bytes: bytes, filename: Optional[str] = None, content_type: Optional[str] = None) -> bool:
        if content_type and "text" in content_type.lower():
            return False

        name = (filename or "").lower()
        if name.endswith((".txt", ".md", ".csv", ".json", ".xml", ".html", ".css", ".js", ".ts", ".py", ".yaml", ".yml")):
            return False

        if file_bytes.startswith(b"%PDF"):
            return True
        if file_bytes.startswith((b"\x89PNG", b"\xff\xd8\xff", b"PK\x03\x04", b"GIF87a", b"GIF89a", b"RIFF")):
            return True
        if b"\x00" in file_bytes:
            return True
        return False

    def _sanitize_text(self, text: str) -> str:
        text = text.replace("\x00", "")
        text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", text)
        return text

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
