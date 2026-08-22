import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import UploadPage from "@/app/upload/page";
import { alignmentService, jdService, resumeService } from "@/services/api";

// The page pulls in the api service (and axios). Nothing here reaches the
// network — the service is stubbed so tests drive the flow with canned
// responses and an accidental call can't hit a real host.
vi.mock("@/services/api", () => ({
    resumeService: { upload: vi.fn(), optimize: vi.fn(), download: vi.fn() },
    jdService: { upload: vi.fn(), update: vi.fn() },
    alignmentService: { generate: vi.fn() },
    dashboardService: { getSummary: vi.fn() },
    apiErrorMessage: (e: any) => e?.message ?? "error",
}));

/** The hidden <input type="file"> react-dropzone renders inside the drop area. */
const fileInput = () => document.querySelector('input[type="file"]') as HTMLInputElement;

/**
 * Drive a selection through react-dropzone. It reads files from the change
 * event and runs them through the same accept/maxSize filter as a real drop,
 * routing anything rejected to onDrop's rejections argument.
 */
const selectFile = (file: File) => {
    fireEvent.change(fileInput(), { target: { files: [file] } });
};

const pdf = (name = "resume.pdf", sizeBytes = 1024) =>
    new File([new Uint8Array(sizeBytes)], name, { type: "application/pdf" });

describe("UploadPage — unsupported file handling", () => {
    it("shows a format-specific message when an image is selected", async () => {
        render(<UploadPage />);

        selectFile(new File(["fake"], "headshot.png", { type: "image/png" }));

        const message = await screen.findByText(/can't read \.png files/i);
        expect(message).toBeInTheDocument();
        expect(message).toHaveTextContent(/PDF or DOCX/i);
    });

    it("names whatever unsupported extension the user picked", async () => {
        render(<UploadPage />);

        selectFile(new File(["plain"], "resume.txt", { type: "text/plain" }));

        expect(await screen.findByText(/can't read \.txt files/i)).toBeInTheDocument();
    });

    it("explains the size limit when the file is over 5MB", async () => {
        render(<UploadPage />);

        selectFile(pdf("huge.pdf", 6 * 1024 * 1024));

        const message = await screen.findByText(/over the 5MB limit/i);
        expect(message).toHaveTextContent("huge.pdf");
    });

    it("accepts a valid PDF and shows it as ready, with no error", async () => {
        render(<UploadPage />);

        selectFile(pdf("resume.pdf"));

        expect(await screen.findByText("resume.pdf")).toBeInTheDocument();
        expect(screen.getByText(/Ready to parse/i)).toBeInTheDocument();
        expect(screen.queryByText(/can't read/i)).toBeNull();
    });

    it("clears a prior error once a valid file is chosen", async () => {
        render(<UploadPage />);

        selectFile(new File(["fake"], "headshot.png", { type: "image/png" }));
        await screen.findByText(/can't read \.png files/i);

        selectFile(pdf("resume.pdf"));

        await waitFor(() => expect(screen.queryByText(/can't read \.png files/i)).toBeNull());
        expect(screen.getByText("resume.pdf")).toBeInTheDocument();
    });
});

describe("UploadPage — single vs multi page length", () => {
    const alignment = {
        alignment_score: 60,
        ats_score: 55,
        breakdown: {},
        feedback: "Reasonable match.",
        matched_skills: [],
        partial_skills: [],
        missing_skills: [],
    };

    const optimization = (overrides: Record<string, any> = {}) => ({
        label: "v1 — Acme",
        baseline_ats_score: 55,
        ats_score: 60,
        ats_delta: 5,
        baseline_alignment_score: 55,
        alignment_score: 60,
        alignment_delta: 5,
        changes: [],
        suggestions: [],
        blocked_rewrites: [],
        single_page: true,
        page_count: 1,
        trimmed_bullets: 2,
        single_page_fit: true,
        length_note: "Condensed to a single page by trimming 2 lower-impact bullet(s).",
        ...overrides,
    });

    beforeEach(() => {
        vi.mocked(resumeService.upload).mockResolvedValue({
            data: { id: "r-1", structured_data: { personal_info: { name: "Ada" } }, extraction_meta: {} },
        } as any);
        vi.mocked(jdService.upload).mockResolvedValue({
            data: {
                id: "j-1", title: "Backend Engineer", company_name: "Acme",
                structured_data: { seniority: "senior", requirements: { mandatory_skills: ["Python"] }, responsibilities: [] },
            },
        } as any);
        vi.mocked(jdService.update).mockResolvedValue({ data: {} } as any);
        vi.mocked(alignmentService.generate).mockResolvedValue({ data: alignment } as any);
        vi.mocked(resumeService.optimize).mockResolvedValue({ data: optimization() } as any);
    });

    const clickPrimary = async (name: RegExp) =>
        userEvent.click(await screen.findByRole("button", { name }));

    /** Upload → parse resume → continue → paste JD → parse → verify → alignment. */
    const advanceToAlignment = async () => {
        render(<UploadPage />);
        selectFile(pdf("resume.pdf"));
        await clickPrimary(/Upload & Parse/i);
        await clickPrimary(/Continue/i);

        const textarea = document.querySelector("textarea") as HTMLTextAreaElement;
        fireEvent.change(textarea, { target: { value: "We need a Python and FastAPI engineer." } });

        await clickPrimary(/Parse Job Description/i);
        await clickPrimary(/Analyze Alignment/i);
        await screen.findByRole("heading", { name: "Alignment" });
    };

    it("offers a single/multi page choice on the alignment step", async () => {
        await advanceToAlignment();

        expect(screen.getByText("Optimized resume length")).toBeInTheDocument();
        expect(screen.getByRole("button", { name: /Single page/i })).toHaveAttribute("aria-pressed", "true");
        expect(screen.getByRole("button", { name: /Multiple pages/i })).toHaveAttribute("aria-pressed", "false");
    });

    it("optimizes as single page by default", async () => {
        await advanceToAlignment();

        await clickPrimary(/Optimize Resume/i);

        expect(resumeService.optimize).toHaveBeenCalledWith("r-1", "j-1", { pagePreference: "single" });
    });

    it("switches to multi page when the user picks it", async () => {
        await advanceToAlignment();

        await userEvent.click(screen.getByRole("button", { name: /Multiple pages/i }));
        expect(screen.getByRole("button", { name: /Multiple pages/i })).toHaveAttribute("aria-pressed", "true");

        await clickPrimary(/Optimize Resume/i);

        expect(resumeService.optimize).toHaveBeenCalledWith("r-1", "j-1", { pagePreference: "multi" });
    });

    it("reports what condensing did on the result step", async () => {
        await advanceToAlignment();
        await clickPrimary(/Optimize Resume/i);

        expect(await screen.findByText(/Condensed to a single page by trimming 2/i)).toBeInTheDocument();
    });

    it("warns honestly on the rare resume that still overflows after condensing", async () => {
        vi.mocked(resumeService.optimize).mockResolvedValue({
            data: optimization({
                single_page_fit: false,
                page_count: 2,
                length_note: "Even after condensing, the core content still needs 2 pages. Every section was kept because cutting more would remove work history or education.",
            }),
        } as any);

        await advanceToAlignment();
        await clickPrimary(/Optimize Resume/i);

        expect(await screen.findByText(/still needs 2 pages/i)).toBeInTheDocument();
    });
});

describe("UploadPage — verify JD role & company", () => {
    const clickPrimary = async (name: RegExp) =>
        userEvent.click(await screen.findByRole("button", { name }));

    const toVerifyStep = async (jdData: Record<string, any>) => {
        vi.mocked(resumeService.upload).mockResolvedValue({
            data: { id: "r-1", structured_data: { personal_info: { name: "Ada" } }, extraction_meta: {} },
        } as any);
        vi.mocked(jdService.upload).mockResolvedValue({ data: jdData } as any);
        vi.mocked(jdService.update).mockResolvedValue({ data: {} } as any);
        vi.mocked(alignmentService.generate).mockResolvedValue({
            data: { alignment_score: 60, ats_score: 55, breakdown: {}, feedback: "ok", matched_skills: [], partial_skills: [], missing_skills: [] },
        } as any);

        render(<UploadPage />);
        selectFile(pdf("resume.pdf"));
        await clickPrimary(/Upload & Parse/i);
        await clickPrimary(/Continue/i);
        fireEvent.change(document.querySelector("textarea") as HTMLTextAreaElement, {
            target: { value: "Some job description text." },
        });
        await clickPrimary(/Parse Job Description/i);
    };

    const parsed = {
        id: "j-1", title: "Backend Engineer", company_name: "Acme",
        structured_data: { seniority: "senior", requirements: { mandatory_skills: ["Python"] }, responsibilities: ["Build services"] },
    };

    it("prefills the parsed role and company for the user to verify", async () => {
        await toVerifyStep(parsed);

        expect(await screen.findByText("Verify the role & company")).toBeInTheDocument();
        expect(screen.getByDisplayValue("Backend Engineer")).toBeInTheDocument();
        expect(screen.getByDisplayValue("Acme")).toBeInTheDocument();
    });

    it("analyzes without a JD update when nothing is corrected", async () => {
        await toVerifyStep(parsed);
        await clickPrimary(/Analyze Alignment/i);

        await screen.findByRole("heading", { name: "Alignment" });
        expect(jdService.update).not.toHaveBeenCalled();
        expect(alignmentService.generate).toHaveBeenCalledWith("r-1", "j-1");
    });

    it("saves the user's corrections before analyzing", async () => {
        await toVerifyStep(parsed);

        const roleInput = screen.getByDisplayValue("Backend Engineer");
        await userEvent.clear(roleInput);
        await userEvent.type(roleInput, "Senior Backend Engineer");
        const companyInput = screen.getByDisplayValue("Acme");
        await userEvent.clear(companyInput);
        await userEvent.type(companyInput, "Acme Corp");

        await clickPrimary(/Analyze Alignment/i);
        await screen.findByRole("heading", { name: "Alignment" });

        expect(jdService.update).toHaveBeenCalledWith("j-1", {
            title: "Senior Backend Engineer",
            company_name: "Acme Corp",
        });
    });

    it("warns and leaves the fields blank when the parser found nothing", async () => {
        await toVerifyStep({
            id: "j-2", title: "Untitled role", company_name: null,
            structured_data: { requirements: { mandatory_skills: [] }, responsibilities: [] },
        });

        expect(await screen.findByText(/couldn't find a role or a company/i)).toBeInTheDocument();
        expect(screen.getByPlaceholderText(/Senior Backend Engineer/i)).toHaveValue("");
        expect(screen.getByPlaceholderText(/Acme Technologies/i)).toHaveValue("");
    });

    it("lets the user re-paste a different posting", async () => {
        await toVerifyStep(parsed);
        expect(await screen.findByText("Verify the role & company")).toBeInTheDocument();

        await userEvent.click(screen.getByRole("button", { name: /Re-paste/i }));

        expect(screen.getByRole("heading", { name: "Add the job description" })).toBeInTheDocument();
    });
});
