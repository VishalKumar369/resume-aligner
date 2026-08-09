import re
from typing import Any, Dict, List, Optional

from app.services.extraction.pipeline import extract_document
from app.services.extraction.types import ExtractionResult
from app.services.parsing.skill_vocabulary import find_skills


class ResumeParserService:

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

    async def parse_bytes(
        self,
        file_bytes: bytes,
        filename: Optional[str] = None,
        content_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        extraction = self.extract(file_bytes, filename=filename, content_type=content_type)
        return await self.parse(extraction.text)

    def extract(
        self,
        file_bytes: bytes,
        filename: Optional[str] = None,
        content_type: Optional[str] = None,
    ) -> ExtractionResult:
        """Turn an uploaded file into text via the shared extraction pipeline.

        Handles PDF and DOCX properly; callers must check `result.ok` before
        trusting the text.
        """
        return extract_document(file_bytes, filename=filename, content_type=content_type)

    def _normalize(self, text: str) -> str:
        return re.sub(r"\s+", " ", text or "").strip().lower()

    def _extract_name(self, text: str) -> str:
        lines = [line.strip() for line in (text or "").splitlines() if line.strip()]
        return lines[0] if lines else ""

    def _extract_email(self, text: str) -> str:
        match = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text or "")
        return match.group(0) if match else ""

    def _extract_skills(self, text: str) -> List[str]:
        return find_skills(text)

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
