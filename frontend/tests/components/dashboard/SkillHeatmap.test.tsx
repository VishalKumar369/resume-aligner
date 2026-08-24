import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { SkillHeatmap, type HeatmapSkill } from "@/components/dashboard/SkillHeatmap";

const skills: HeatmapSkill[] = [
    { name: "Python", status: "strong" },
    { name: "SQL", status: "partial", detail: "Mentioned once, no depth" },
    { name: "Airflow", status: "gap" },
    { name: "Kubernetes", status: "critical" },
];

describe("SkillHeatmap", () => {
    it("prompts for an analysis when there is nothing to plot", () => {
        render(<SkillHeatmap skills={[]} />);

        expect(screen.getByText(/Analyze a resume against a job description/)).toBeInTheDocument();
    });

    it("renders a tile per skill", () => {
        render(<SkillHeatmap skills={skills} />);

        for (const skill of skills) {
            expect(screen.getByText(skill.name)).toBeInTheDocument();
        }
    });

    it("colours each tile by status", () => {
        render(<SkillHeatmap skills={skills} />);

        expect(screen.getByText("Python")).toHaveClass("text-success");
        expect(screen.getByText("SQL")).toHaveClass("text-warning");
        expect(screen.getByText("Airflow")).toHaveClass("text-orange-400");
        expect(screen.getByText("Kubernetes")).toHaveClass("text-error");
    });

    it("puts the detail in the tooltip, falling back to the skill name", () => {
        render(<SkillHeatmap skills={skills} />);

        expect(screen.getByText("SQL")).toHaveAttribute("title", "Mentioned once, no depth");
        expect(screen.getByText("Python")).toHaveAttribute("title", "Python");
    });

    it("always shows the legend", () => {
        render(<SkillHeatmap skills={[]} />);

        expect(screen.getByText("You have it")).toBeInTheDocument();
        expect(screen.getByText("Partially covered")).toBeInTheDocument();
        expect(screen.getByText("Gap")).toBeInTheDocument();
        expect(screen.getByText("Critical gap")).toBeInTheDocument();
    });

    it("links each tile when linkForSkill is provided", () => {
        render(<SkillHeatmap skills={skills} linkForSkill={(s) => `/learning?skill=${s}`} />);

        const link = screen.getByText("Airflow").closest("a");
        expect(link).toHaveAttribute("href", "/learning?skill=Airflow");
    });

    it("renders plain, non-linked tiles by default", () => {
        render(<SkillHeatmap skills={skills} />);
        expect(screen.getByText("Python").closest("a")).toBeNull();
    });

    it("keeps the same skill listed twice when the statuses differ", () => {
        render(
            <SkillHeatmap
                skills={[
                    { name: "SQL", status: "strong" },
                    { name: "SQL", status: "gap" },
                ]}
            />
        );

        expect(screen.getAllByText("SQL")).toHaveLength(2);
    });
});
