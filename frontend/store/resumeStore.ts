import { create } from "zustand";

interface Resume {
    id: string;
    label: string;
    uploadedAt: string;
    atsScore: number;
    alignmentScore: number;
    versions: { id: string; company: string; s3Path: string }[];
}

interface ResumeState {
    resumes: Resume[];
    activeResumeId: string | null;
    setResumes: (resumes: Resume[]) => void;
    setActiveResume: (id: string) => void;
    addResume: (resume: Resume) => void;
}

export const useResumeStore = create<ResumeState>((set) => ({
    resumes: [],
    activeResumeId: null,
    setResumes: (resumes) => set({ resumes }),
    setActiveResume: (id) => set({ activeResumeId: id }),
    addResume: (resume) => set((state) => ({ resumes: [resume, ...state.resumes] })),
}));
