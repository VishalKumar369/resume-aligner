import { render, screen, waitFor } from "@testing-library/react";
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
    learningService: { getRoadmap: vi.fn() },
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
        await waitFor(() => expect(screen.getByText("Docker")).toBeInTheDocument());
        await waitFor(() => expect((Element.prototype as any).scrollIntoView).toHaveBeenCalled());
    });

    it("surfaces a focused partial skill", async () => {
        mockSearch = new URLSearchParams("skill=Kafka");
        render(<LearningPage />);

        expect(await screen.findByText("Kafka")).toBeInTheDocument();
        expect(screen.getByText("Partially covered")).toBeInTheDocument();
    });
});
