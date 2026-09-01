import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { InterviewPrep } from "@/components/learning/InterviewPrep";
import { learningService } from "@/services/api";

vi.mock("@/services/api", () => ({
    learningService: { getQuestions: vi.fn() },
    apiErrorMessage: (e: any) => e?.message ?? "error",
}));

const bank = {
    skill: "LLM",
    total: 60,
    levels: [
        { level: "beginner", label: "Beginner", count: 2, questions: ["What is an LLM?", "What is a token?"] },
        { level: "advanced", label: "Advanced", count: 1, questions: ["Explain LoRA."] },
    ],
};

beforeEach(() => {
    vi.mocked(learningService.getQuestions).mockResolvedValue({ data: bank } as any);
});

describe("InterviewPrep", () => {
    it("shows the skill and question count, collapsed by default", () => {
        render(<InterviewPrep skill="LLM" total={60} />);

        expect(screen.getByText("LLM")).toBeInTheDocument();
        expect(screen.getByText("60 Qs")).toBeInTheDocument();
        // Nothing fetched until opened.
        expect(learningService.getQuestions).not.toHaveBeenCalled();
    });

    it("fetches and shows questions on first open, grouped by difficulty", async () => {
        render(<InterviewPrep skill="LLM" total={60} />);

        await userEvent.click(screen.getByRole("button", { expanded: false }));

        expect(learningService.getQuestions).toHaveBeenCalledWith("LLM");
        expect(await screen.findByText("What is an LLM?")).toBeInTheDocument();
        // Difficulty tabs are present.
        expect(screen.getByRole("button", { name: /Beginner/ })).toBeInTheDocument();
        expect(screen.getByRole("button", { name: /Advanced/ })).toBeInTheDocument();
    });

    it("switches the shown questions when a difficulty tab is clicked", async () => {
        render(<InterviewPrep skill="LLM" total={60} />);
        await userEvent.click(screen.getByRole("button", { expanded: false }));
        await screen.findByText("What is an LLM?");

        await userEvent.click(screen.getByRole("button", { name: /Advanced/ }));

        expect(screen.getByText("Explain LoRA.")).toBeInTheDocument();
        expect(screen.queryByText("What is an LLM?")).toBeNull();
    });

    it("does not refetch when toggled a second time", async () => {
        render(<InterviewPrep skill="LLM" total={60} />);
        const toggle = screen.getByRole("button", { expanded: false });

        await userEvent.click(toggle);
        await screen.findByText("What is an LLM?");
        await userEvent.click(screen.getByRole("button", { expanded: true }));
        await userEvent.click(screen.getByRole("button", { expanded: false }));

        expect(learningService.getQuestions).toHaveBeenCalledTimes(1);
    });

    it("surfaces an error if the questions fail to load", async () => {
        vi.mocked(learningService.getQuestions).mockRejectedValue({ message: "Boom" });
        render(<InterviewPrep skill="LLM" total={60} />);

        await userEvent.click(screen.getByRole("button", { expanded: false }));

        expect(await screen.findByText("Boom")).toBeInTheDocument();
    });
});
