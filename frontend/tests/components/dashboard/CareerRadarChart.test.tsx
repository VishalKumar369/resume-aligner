import { render, screen } from "@testing-library/react";
import React from "react";
import { describe, expect, it, vi } from "vitest";

// recharts measures its container, which jsdom reports as 0×0, so the real
// chart would render nothing. Stub it to something assertable instead.
vi.mock("recharts", () => ({
    ResponsiveContainer: ({ children }: { children: React.ReactNode }) => (
        <div data-testid="responsive-container">{children}</div>
    ),
    RadarChart: ({ data, children }: { data: unknown[]; children: React.ReactNode }) => (
        <div data-testid="radar-chart" data-axes={data.length}>
            {children}
        </div>
    ),
    PolarGrid: () => <div data-testid="polar-grid" />,
    PolarAngleAxis: ({ dataKey }: { dataKey: string }) => <div data-testid="angle-axis">{dataKey}</div>,
    Radar: ({ dataKey }: { dataKey: string }) => <div data-testid="radar">{dataKey}</div>,
    // Render the chart's own tooltip component in both states so its formatting
    // is covered without driving real hover events through recharts.
    Tooltip: ({ content }: { content: React.ReactElement }) => (
        <div data-testid="tooltip">
            <div data-testid="tooltip-hovered">
                {React.cloneElement(content, {
                    active: true,
                    payload: [{ value: 78.6, payload: { skill: "Skills" } }],
                })}
            </div>
            <div data-testid="tooltip-idle">
                {React.cloneElement(content, { active: false, payload: [] })}
            </div>
        </div>
    ),
}));

import { CareerRadarChart } from "@/components/dashboard/CareerRadarChart";

const axes = [
    { skill: "Skills", score: 78 },
    { skill: "Experience", score: 64 },
    { skill: "Education", score: 90 },
];

describe("CareerRadarChart", () => {
    it("always shows the section heading", () => {
        render(<CareerRadarChart axes={[]} />);

        expect(screen.getByRole("heading", { name: "Alignment Breakdown" })).toBeInTheDocument();
    });

    it("draws a radar once there are three or more axes", () => {
        render(<CareerRadarChart axes={axes} />);

        expect(screen.getByTestId("radar-chart")).toHaveAttribute("data-axes", "3");
        expect(screen.getByTestId("radar")).toHaveTextContent("score");
    });

    it("shows the hovered axis and its rounded score in the tooltip", () => {
        render(<CareerRadarChart axes={axes} />);

        const hovered = screen.getByTestId("tooltip-hovered");
        expect(hovered).toHaveTextContent("Skills");
        expect(hovered).toHaveTextContent("79%");
        // Nothing hovered, nothing rendered.
        expect(screen.getByTestId("tooltip-idle")).toBeEmptyDOMElement();
    });

    it("falls back to bars when a radar would collapse to a line", () => {
        render(<CareerRadarChart axes={axes.slice(0, 2)} />);

        expect(screen.queryByTestId("radar-chart")).toBeNull();
        expect(screen.getByText("Skills")).toBeInTheDocument();
        expect(screen.getByText("78%")).toBeInTheDocument();
        expect(screen.getByText("64%")).toBeInTheDocument();
    });

    it("sizes each fallback bar to its rounded score", () => {
        const { container } = render(<CareerRadarChart axes={[{ skill: "Skills", score: 78.6 }]} />);

        expect(screen.getByText("79%")).toBeInTheDocument();
        expect(container.querySelector<HTMLElement>(".bg-primary")!.style.width).toBe("79%");
    });

    it("says so when there is nothing to break down", () => {
        render(<CareerRadarChart axes={[]} />);

        expect(screen.getByText("No alignment components to show yet.")).toBeInTheDocument();
    });
});
