import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ExtractionReview } from "@/components/upload/ExtractionReview";

const resume = (overrides: Record<string, any> = {}) => ({
    extraction_meta: {
        method: "pdf_text_layer",
        page_count: 2,
        word_count: 640,
        confidence: 0.92,
        warnings: [],
    },
    structured_data: {
        personal_info: {
            name: "Ada Lovelace",
            title: "Senior Data Scientist",
            email: "ada@example.com",
            phone: "+1 555 0100",
            location: "Chicago, US",
        },
        total_experience_years: 4.5,
        skills: { categories: { Languages: ["Python", "SQL"], Cloud: ["AWS"] } },
        experience: [
            { role: "Data Scientist", company: "Acme", start_date: "2022", end_date: "2025" },
            { role: "Analyst", company: "Globex", start_date: "2021", end_date: "2022" },
        ],
        education: [{ degree: "B.Tech Computer Science", institution: "IIT", end_year: 2020 }],
        projects: [{ name: "Churn model" }],
    },
    ...overrides,
});

describe("ExtractionReview", () => {
    it("summarises how the file was parsed", () => {
        render(<ExtractionReview resume={resume()} onReplace={vi.fn()} />);

        expect(screen.getByText("Parsed successfully")).toBeInTheDocument();
        expect(
            screen.getByText("via pdf text layer · 2 pages · 640 words · confidence 0.92")
        ).toBeInTheDocument();
    });

    it("uses the singular for a one-page file and skips missing meta fields", () => {
        render(
            <ExtractionReview
                resume={resume({ extraction_meta: { method: "docx", page_count: 1 } })}
                onReplace={vi.fn()}
            />
        );

        expect(screen.getByText("via docx · 1 page")).toBeInTheDocument();
    });

    it("shows the extracted contact details", () => {
        render(<ExtractionReview resume={resume()} onReplace={vi.fn()} />);

        expect(screen.getByText("Ada Lovelace")).toBeInTheDocument();
        expect(screen.getByText("Senior Data Scientist")).toBeInTheDocument();
        expect(screen.getByText("ada@example.com")).toBeInTheDocument();
        expect(screen.getByText("+1 555 0100")).toBeInTheDocument();
        expect(screen.getByText("Chicago, US")).toBeInTheDocument();
    });

    it("flags a missing name rather than rendering a blank line", () => {
        render(
            <ExtractionReview
                resume={resume({ structured_data: { personal_info: {} } })}
                onReplace={vi.fn()}
            />
        );

        expect(screen.getByText("Name not found")).toHaveClass("text-error");
    });

    it("counts experience years, roles and projects", () => {
        render(<ExtractionReview resume={resume()} onReplace={vi.fn()} />);

        expect(screen.getByText("4.5 yrs")).toBeInTheDocument();
        expect(screen.getByText("Roles").previousElementSibling).toHaveTextContent("2");
        expect(screen.getByText("Projects").previousElementSibling).toHaveTextContent("1");
    });

    it("defaults the experience total to zero years when the parser found none", () => {
        render(<ExtractionReview resume={{ structured_data: {} }} onReplace={vi.fn()} />);

        expect(screen.getByText("0 yrs")).toBeInTheDocument();
    });

    it("lists skills grouped by category", () => {
        render(<ExtractionReview resume={resume()} onReplace={vi.fn()} />);

        expect(screen.getByText("Languages:")).toBeInTheDocument();
        expect(screen.getByText("Python, SQL")).toBeInTheDocument();
        expect(screen.getByText("AWS")).toBeInTheDocument();
    });

    it("shows at most the three most recent roles", () => {
        const experience = Array.from({ length: 5 }, (_, i) => ({
            role: `Role ${i}`,
            company: "Acme",
            start_date: "2020",
            end_date: "2021",
        }));
        render(
            <ExtractionReview
                resume={resume({ structured_data: { ...resume().structured_data, experience } })}
                onReplace={vi.fn()}
            />
        );

        expect(screen.getByText("Role 0")).toBeInTheDocument();
        expect(screen.getByText("Role 2")).toBeInTheDocument();
        expect(screen.queryByText("Role 3")).toBeNull();
    });

    it("marks an unknown end date and an internship", () => {
        render(
            <ExtractionReview
                resume={resume({
                    structured_data: {
                        ...resume().structured_data,
                        experience: [
                            { role: "Intern", company: "Acme", start_date: "2021", is_internship: true },
                        ],
                    },
                })}
                onReplace={vi.fn()}
            />
        );

        expect(screen.getByText("Acme · 2021 → ? · internship")).toBeInTheDocument();
    });

    it("says so when a role or a degree could not be read", () => {
        render(
            <ExtractionReview
                resume={{
                    structured_data: {
                        experience: [{ company: "Acme" }],
                        education: [{ institution: "IIT" }],
                    },
                }}
                onReplace={vi.fn()}
            />
        );

        expect(screen.getByText("Role not found")).toBeInTheDocument();
        expect(screen.getByText("Degree not found")).toBeInTheDocument();
    });

    it("shows the most recent education entry", () => {
        render(<ExtractionReview resume={resume()} onReplace={vi.fn()} />);

        expect(screen.getByText("B.Tech Computer Science")).toBeInTheDocument();
        expect(screen.getByText("IIT · 2020")).toBeInTheDocument();
    });

    it("warns when the parser flagged problems", () => {
        render(
            <ExtractionReview
                resume={resume({
                    extraction_meta: { confidence: 0.91, warnings: ["no_contact_section", "ocr_fallback"] },
                })}
                onReplace={vi.fn()}
            />
        );

        expect(screen.getByText("Extraction may be incomplete")).toBeInTheDocument();
        expect(screen.getByText("no contact section")).toBeInTheDocument();
        expect(screen.getByText("ocr fallback")).toBeInTheDocument();
    });

    it("warns on low confidence even without explicit warnings", () => {
        render(
            <ExtractionReview
                resume={resume({ extraction_meta: { confidence: 0.4, warnings: [] } })}
                onReplace={vi.fn()}
            />
        );

        expect(screen.getByText(/Low confidence/)).toBeInTheDocument();
    });

    it("stays quiet when confidence is high and nothing was flagged", () => {
        render(<ExtractionReview resume={resume()} onReplace={vi.fn()} />);

        expect(screen.queryByText("Extraction may be incomplete")).toBeNull();
    });

    it("tells the user when the upload reused an earlier analysis", () => {
        render(<ExtractionReview resume={resume({ duplicate_of_existing: true })} onReplace={vi.fn()} />);

        expect(screen.getByText(/uploaded this exact file before/)).toBeInTheDocument();
    });

    it("renders without crashing on an empty parse result", () => {
        render(<ExtractionReview resume={null} onReplace={vi.fn()} />);

        expect(screen.getByText("Name not found")).toBeInTheDocument();
        expect(screen.getByText("Parsed successfully")).toBeInTheDocument();
    });

    it("calls onReplace when the user wants a different file", async () => {
        const onReplace = vi.fn();
        render(<ExtractionReview resume={resume()} onReplace={onReplace} />);

        await userEvent.click(screen.getByRole("button", { name: /replace file/i }));

        expect(onReplace).toHaveBeenCalledTimes(1);
    });
});
