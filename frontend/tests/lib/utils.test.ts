import { describe, expect, it } from "vitest";

import {
    PLATFORM_NAME,
    cn,
    formatScore,
    getScoreBg,
    getScoreColor,
    getScoreLabel,
    learningLinkForSkill,
    noteComposeLink,
} from "@/lib/utils";

describe("learningLinkForSkill", () => {
    it("deep-links to the roadmap with the skill encoded", () => {
        expect(learningLinkForSkill("Docker")).toBe("/learning?skill=Docker");
        expect(learningLinkForSkill("CI/CD")).toBe("/learning?skill=CI%2FCD");
        expect(learningLinkForSkill("C++")).toBe("/learning?skill=C%2B%2B");
    });
});

describe("noteComposeLink", () => {
    it("builds a pre-filled composer link", () => {
        expect(noteComposeLink({ title: "Learn Kafka", category: "Goal", color: "error" }))
            .toBe("/notes?compose=1&title=Learn+Kafka&category=Goal&color=error");
    });

    it("includes only the fields provided", () => {
        expect(noteComposeLink({})).toBe("/notes?compose=1");
    });
});

describe("cn", () => {
    it("joins class names and drops falsy values", () => {
        expect(cn("a", false && "b", undefined, "c")).toBe("a c");
    });

    it("lets the last tailwind class in a conflicting group win", () => {
        expect(cn("p-2", "p-5")).toBe("p-5");
        expect(cn("text-error", "text-success")).toBe("text-success");
    });

    it("supports conditional object and array syntax", () => {
        expect(cn(["rounded", { hidden: false, block: true }])).toBe("rounded block");
    });
});

describe("formatScore", () => {
    it("rounds to a whole percentage", () => {
        expect(formatScore(72.4)).toBe("72%");
        expect(formatScore(72.5)).toBe("73%");
        expect(formatScore(0)).toBe("0%");
        expect(formatScore(100)).toBe("100%");
    });
});

describe("getScoreColor", () => {
    it.each([
        [100, "text-success"],
        [75, "text-success"],
        [74.9, "text-warning"],
        [50, "text-warning"],
        [49.9, "text-error"],
        [0, "text-error"],
    ])("maps %s to %s", (score, expected) => {
        expect(getScoreColor(score)).toBe(expected);
    });
});

describe("getScoreBg", () => {
    it("uses the same 75 / 50 thresholds as the text colour", () => {
        expect(getScoreBg(75)).toContain("bg-success");
        expect(getScoreBg(50)).toContain("bg-warning");
        expect(getScoreBg(49)).toContain("bg-error");
    });
});

describe("getScoreLabel", () => {
    it.each([
        [92, "Excellent"],
        [85, "Excellent"],
        [84, "Good"],
        [70, "Good"],
        [69, "Fair"],
        [50, "Fair"],
        [49, "Needs Work"],
    ])("labels %s as %s", (score, expected) => {
        expect(getScoreLabel(score)).toBe(expected);
    });
});

describe("PLATFORM_NAME", () => {
    it("falls back to the default product name when the env var is unset", () => {
        expect(PLATFORM_NAME).toBe(process.env.NEXT_PUBLIC_PLATFORM_NAME || "Resume JD Aligner");
    });
});
