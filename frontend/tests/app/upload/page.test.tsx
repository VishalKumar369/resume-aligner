import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import UploadPage from "@/app/upload/page";

// The page pulls in the api service (and axios). Nothing here reaches the
// network — we only exercise the client-side dropzone validation — but the
// service is stubbed so an accidental call can't hit a real host.
vi.mock("@/services/api", () => ({
    resumeService: { upload: vi.fn(), download: vi.fn() },
    jdService: { upload: vi.fn() },
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
