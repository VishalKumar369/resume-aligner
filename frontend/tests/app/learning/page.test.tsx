import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import LearningPage from "@/app/learning/page";
import { learningService } from "@/services/api";

// Controllable search params for the deep-link tests.
let mockSearch = new URLSearchParams();

vi.mock("next/navigation", () => ({
    useSearchParams: () => mockSearch,
    useRouter: () => ({ push: vi.fn(), replace: vi.fn(), prefetch: vi.fn() }),
    usePathname: () => "/learning",
}));

vi.mock("@/services/api", () => ({
    learningService: { getRoadmap: vi.fn(), getQuestions: vi.fn() },
    apiErrorMessage: (e: any) => e?.message ?? "error",
}));

const roadmap = {
    jds_considered: 2,
    total_modules: 2,
    total_duration: "5 weeks",
    modules: [
        {
            module: "Backend Frameworks", priority: "P1", week: "Week 1-2", jd_demand: 2,
            skills: ["FastAPI"], resources: [{ skill: "FastAPI", title: "FastAPI Docs", url: "https://fastapi.tiangolo.com" }],
        },
        {
            module: "Containerisation & Orchestration", priority: "P2", week: "Week 3-4", jd_demand: 1,
            skills: ["Docker", "Kubernetes"],
            resources: [{ skill: "Docker", title: "Docker Docs", url: "https://docs.docker.com" }],
        },
    ],
    partial_skills: [
        { skill: "Kafka", covered_by: "RabbitMQ", jd_count: 1, resource: { title: "Kafka Docs", url: "https://kafka.apache.org" } },
    ],
    question_banks: { Docker: { total: 60, beginner: 20, intermediate: 15, advanced: 15, practical: 10 } },
};

// jsdom has no scrollIntoView.
beforeEach(() => {
    mockSearch = new URLSearchParams();
    (Element.prototype as any).scrollIntoView = vi.fn();
    vi.mocked(learningService.getRoadmap).mockResolvedValue({ data: roadmap } as any);
});

describe("LearningPage deep-link", () => {
    it("renders the roadmap normally with no skill param", async () => {
        render(<LearningPage />);
        expect(await screen.findByRole("heading", { name: "Learning Roadmap" })).toBeInTheDocument();
    });

    it("filters modules by priority via the tabs", async () => {
        render(<LearningPage />);
        await screen.findByRole("heading", { name: "Learning Roadmap" });

        // Critical (P1) → only the Backend Frameworks module remains. Anchor the
        // name so the tab isn't confused with a module's "Critical" priority badge.
        await userEvent.click(screen.getByRole("button", { name: /^Critical/ }));
        expect(screen.getByText("Backend Frameworks")).toBeInTheDocument();
        expect(screen.queryByText("Containerisation & Orchestration")).toBeNull();
    });

    it("the Partially covered tab shows only partial skills", async () => {
        render(<LearningPage />);
        await screen.findByRole("heading", { name: "Learning Roadmap" });

        await userEvent.click(screen.getByRole("button", { name: /Partially covered/ }));
        expect(screen.getByText("Kafka")).toBeInTheDocument();
        expect(screen.queryByText("Backend Frameworks")).toBeNull();
    });

    it("links a module's skill to its docs", async () => {
        render(<LearningPage />);
        await screen.findByRole("heading", { name: "Learning Roadmap" });
        // First module (Backend Frameworks) is expanded by default; the FastAPI
        // chip links out (exact name avoids matching the "FastAPI Docs" resource).
        expect(screen.getByRole("link", { name: "FastAPI" })).toHaveAttribute("href", "https://fastapi.tiangolo.com");
    });

    it("highlights and reveals the focused skill from ?skill=", async () => {
        mockSearch = new URLSearchParams("skill=Docker");
        render(<LearningPage />);
        await screen.findByRole("heading", { name: "Learning Roadmap" });

        // Docker lives in the second module, which must auto-expand to show it.
        await waitFor(() => expect(screen.getAllByText("Docker").length).toBeGreaterThan(0));
        await waitFor(() => expect((Element.prototype as any).scrollIntoView).toHaveBeenCalled());
    });

    it("surfaces a focused partial skill", async () => {
        mockSearch = new URLSearchParams("skill=Kafka");
        render(<LearningPage />);

        expect(await screen.findByText("Kafka")).toBeInTheDocument();
        expect(screen.getByRole("heading", { name: /Partially covered/i })).toBeInTheDocument();
    });

    it("offers interview prep for a skill that has a question bank", async () => {
        // Docker lives in the second module and has a bank; focus it so it expands.
        mockSearch = new URLSearchParams("skill=Docker");
        render(<LearningPage />);
        await screen.findByRole("heading", { name: "Learning Roadmap" });

        await waitFor(() => expect(screen.getByText("Interview preparation")).toBeInTheDocument());
        expect(screen.getByText("60 Qs")).toBeInTheDocument();
    });
});
