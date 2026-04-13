# Development Roadmap

## Phase 1: Foundation (MVP)
**Goals**: Core parsing and semantic alignment.
- **Deliverables**: Resume/JD Parser, Cosine Similarity Engine, Basic Web UI.
- **APIs**: `/resume/upload`, `/jd/upload`, `/alignment/generate`.
- **Database**: `users`, `resumes`, `job_descriptions`.

## Phase 2: Intelligence & Optimization
**Goals**: ATS scoring and generative resume versions.
- **Deliverables**: ATS Scoring Engine, Resume Optimizer (LLM), PDF Generator.
- **APIs**: `/resume/optimize`, `/ats/score`.
- **Database**: `resume_versions`, `ats_reports`.

## Phase 3: Career Planning & Analytics
**Goals**: Skill gap detection and roadmap generation.
- **Deliverables**: Skill Gap Engine, Learning Roadmap, Dashboard V1.
- **APIs**: `/learning/roadmap`, `/dashboard/summary`.
- **Database**: `skill_gaps`, `learning_paths`, `dashboard_snapshots`.

## Phase 4: Enterprise & Predictive Insights
**Goals**: Predictive interview modeling and company deep-dives.
- **Deliverables**: Company Intelligence Engine, Interview Probability Model.
- **APIs**: `/company/{id}/insights`, `/predict/interview`.
- **Database**: `company_profiles`, `prediction_models`.

## Future Vision
- Chrome Extension for 1-click optimization on LinkedIn.
- AI-driven video interview practice integration.
- Recruiting API for direct submission to ATS partners.
