import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import NotesPage from "@/app/notes/page";
import { noteService } from "@/services/api";

vi.mock("@/services/api", () => ({
    noteService: { getAll: vi.fn(), create: vi.fn(), update: vi.fn(), remove: vi.fn() },
    apiErrorMessage: (e: any) => e?.message ?? "error",
}));

const notes = [
    {
        id: "n1", title: "Learn Kafka", content: "cover the basics", category: "Goal", color: "primary",
        target_date: null, is_pinned: false, is_completed: false, created_at: "2026-09-01T00:00:00Z",
    },
    {
        id: "n2", title: "Weekly journal", content: "reflections", category: "Journal", color: "success",
        target_date: "2026-12-01T00:00:00Z", is_pinned: true, is_completed: false, created_at: "2026-09-02T00:00:00Z",
    },
];

beforeEach(() => {
    vi.mocked(noteService.getAll).mockResolvedValue({ data: notes } as any);
    vi.mocked(noteService.create).mockResolvedValue({ data: {} } as any);
    vi.mocked(noteService.update).mockResolvedValue({ data: {} } as any);
    vi.mocked(noteService.remove).mockResolvedValue({ data: {} } as any);
});

describe("NotesPage", () => {
    it("renders the user's notes", async () => {
        render(<NotesPage />);
        expect(await screen.findByText("Learn Kafka")).toBeInTheDocument();
        expect(screen.getByText("Weekly journal")).toBeInTheDocument();
    });

    it("creates a note from the composer", async () => {
        render(<NotesPage />);
        await screen.findByText("Learn Kafka");

        await userEvent.click(screen.getByRole("button", { name: /New note/i }));
        await userEvent.type(screen.getByPlaceholderText(/Land a backend role/i), "Finish the portfolio");
        await userEvent.click(screen.getByRole("button", { name: /Create note/i }));

        expect(noteService.create).toHaveBeenCalledWith(
            expect.objectContaining({ title: "Finish the portfolio", category: "Goal", color: "primary" })
        );
    });

    it("requires a title before saving", async () => {
        render(<NotesPage />);
        await screen.findByText("Learn Kafka");

        await userEvent.click(screen.getByRole("button", { name: /New note/i }));
        await userEvent.click(screen.getByRole("button", { name: /Create note/i }));

        expect(noteService.create).not.toHaveBeenCalled();
        expect(screen.getByText(/Give your note a title/i)).toBeInTheDocument();
    });

    it("edits an existing note", async () => {
        render(<NotesPage />);
        await screen.findByText("Learn Kafka");

        await userEvent.click(screen.getAllByLabelText("Edit")[0]);
        expect(screen.getByRole("heading", { name: "Edit note" })).toBeInTheDocument();
        expect(screen.getByDisplayValue("Learn Kafka")).toBeInTheDocument();

        await userEvent.click(screen.getByRole("button", { name: /Save changes/i }));
        expect(noteService.update).toHaveBeenCalledWith("n1", expect.objectContaining({ title: "Learn Kafka" }));
    });

    it("toggles completion", async () => {
        render(<NotesPage />);
        await screen.findByText("Learn Kafka");

        await userEvent.click(screen.getAllByRole("button", { name: /Mark done/i })[0]);
        expect(noteService.update).toHaveBeenCalledWith("n1", { is_completed: true });
    });

    it("pins a note", async () => {
        render(<NotesPage />);
        await screen.findByText("Learn Kafka");

        await userEvent.click(screen.getByLabelText("Pin"));
        expect(noteService.update).toHaveBeenCalledWith("n1", { is_pinned: true });
    });

    it("deletes a note", async () => {
        render(<NotesPage />);
        await screen.findByText("Learn Kafka");

        await userEvent.click(screen.getAllByLabelText("Delete")[0]);
        expect(noteService.remove).toHaveBeenCalledWith("n1");
    });

    it("shows an empty state that opens the composer", async () => {
        vi.mocked(noteService.getAll).mockResolvedValue({ data: [] } as any);
        render(<NotesPage />);

        expect(await screen.findByText("No notes yet")).toBeInTheDocument();
        await userEvent.click(screen.getByRole("button", { name: /Create a note/i }));
        expect(screen.getByRole("heading", { name: "New note" })).toBeInTheDocument();
    });
});
