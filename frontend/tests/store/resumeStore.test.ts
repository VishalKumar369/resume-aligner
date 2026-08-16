import { beforeEach, describe, expect, it } from "vitest";

import { useResumeStore } from "@/store/resumeStore";

const resume = (id: string) => ({
    id,
    label: `Resume ${id}`,
    uploadedAt: "2026-01-01T00:00:00Z",
    atsScore: 70,
    alignmentScore: 65,
    versions: [],
});

describe("useResumeStore", () => {
    beforeEach(() => {
        useResumeStore.setState({ resumes: [], activeResumeId: null });
    });

    it("replaces the list on setResumes", () => {
        useResumeStore.getState().setResumes([resume("a"), resume("b")]);
        useResumeStore.getState().setResumes([resume("c")]);

        expect(useResumeStore.getState().resumes.map((r) => r.id)).toEqual(["c"]);
    });

    it("prepends a new upload so the newest resume shows first", () => {
        useResumeStore.getState().setResumes([resume("old")]);
        useResumeStore.getState().addResume(resume("new"));

        expect(useResumeStore.getState().resumes.map((r) => r.id)).toEqual(["new", "old"]);
    });

    it("tracks the active resume id", () => {
        useResumeStore.getState().setActiveResume("a");

        expect(useResumeStore.getState().activeResumeId).toBe("a");
    });
});
