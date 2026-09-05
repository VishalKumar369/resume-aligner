import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import NotesPage from "@/app/notes/page";
import { noteService } from "@/services/api";

// Controllable search params for the compose-from-URL flow.
let mockSearch = new URLSearchParams();

vi.mock("next/navigation", () => ({
    useSearchParams: () => mockSearch,
    useRouter: () => ({ push: vi.fn(), replace: vi.fn(), prefetch: vi.fn() }),
    usePathname: () => "/notes",
}));

vi.mock("@/services/api", () => ({
    noteService: { getAll: vi.fn(), create: vi.fn(), update: vi.fn(), remove: vi.fn() },
    apiErrorMessage: (e: any) => e?.message ?? "error",
}));

beforeEach(() => {
    mockSearch = new URLSearchParams();
});

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

    it("opens the composer pre-filled from an 'Add as goal' link", async () => {
        mockSearch = new URLSearchParams("compose=1&title=Learn+Kafka&category=Goal&color=error");
        render(<NotesPage />);

        expect(await screen.findByRole("heading", { name: "New note" })).toBeInTheDocument();
        expect(screen.getByDisplayValue("Learn Kafka")).toBeInTheDocument();
        expect(screen.getByDisplayValue("Goal")).toBeInTheDocument();
    });
});

describe("NotesPage — search, filters & summary", () => {
    const rich = [
        { id: "n1", title: "Learn Kafka", content: "streaming", category: "Goal", color: "primary", target_date: null, is_pinned: false, is_completed: false, created_at: "2026-09-01T00:00:00Z" },
        { id: "n2", title: "Weekly journal", content: "reflections", category: "Journal", color: "success", target_date: "2026-12-01T00:00:00Z", is_pinned: false, is_completed: false, created_at: "2026-09-02T00:00:00Z" },
        { id: "n3", title: "Old target", content: "overdue one", category: "Goal", color: "warning", target_date: "2025-01-01T00:00:00Z", is_pinned: false, is_completed: false, created_at: "2026-08-01T00:00:00Z" },
        { id: "n4", title: "Finished task", content: "shipped", category: "Task", color: "success", target_date: null, is_pinned: false, is_completed: true, created_at: "2026-08-15T00:00:00Z" },
    ];

    beforeEach(() => {
        vi.mocked(noteService.getAll).mockResolvedValue({ data: rich } as any);
    });

    it("summarizes total, completed, upcoming and overdue targets", async () => {
        render(<NotesPage />);
        await screen.findByText("Learn Kafka");

        expect(screen.getByText("Total")).toBeInTheDocument();
        expect(screen.getByText("Completed")).toBeInTheDocument();
        expect(screen.getByText("Upcoming")).toBeInTheDocument();
        expect(screen.getByText("Overdue")).toBeInTheDocument();
        expect(screen.getByText("4")).toBeInTheDocument(); // total
    });

    it("filters notes by the search box", async () => {
        render(<NotesPage />);
        await screen.findByText("Learn Kafka");

        await userEvent.type(screen.getByPlaceholderText(/Search notes/i), "journal");
        expect(screen.getByText("Weekly journal")).toBeInTheDocument();
        expect(screen.queryByText("Learn Kafka")).toBeNull();
    });

    it("hides completed notes when toggled", async () => {
        render(<NotesPage />);
        await screen.findByText("Finished task");

        await userEvent.click(screen.getByRole("button", { name: /Hide completed/i }));
        expect(screen.queryByText("Finished task")).toBeNull();
        expect(screen.getByText("Learn Kafka")).toBeInTheDocument();
    });
});
