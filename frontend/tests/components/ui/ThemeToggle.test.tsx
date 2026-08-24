import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it } from "vitest";

import { ThemeToggle } from "@/components/ui/ThemeToggle";

afterEach(() => {
    document.documentElement.classList.remove("light", "dark");
});

describe("ThemeToggle", () => {
    it("defaults to dark and offers switching to light", async () => {
        render(<ThemeToggle />);

        expect(await screen.findByRole("button", { name: /switch to light mode/i })).toBeInTheDocument();
    });

    it("flips the html theme class and persists the choice", async () => {
        render(<ThemeToggle />);

        await userEvent.click(screen.getByRole("button"));
        expect(document.documentElement.classList.contains("light")).toBe(true);
        expect(localStorage.getItem("theme")).toBe("light");
        expect(screen.getByRole("button", { name: /switch to dark mode/i })).toBeInTheDocument();

        await userEvent.click(screen.getByRole("button"));
        expect(document.documentElement.classList.contains("dark")).toBe(true);
        expect(localStorage.getItem("theme")).toBe("dark");
    });

    it("reflects a light theme already set on the html element", async () => {
        document.documentElement.classList.add("light");
        render(<ThemeToggle />);

        expect(await screen.findByRole("button", { name: /switch to dark mode/i })).toBeInTheDocument();
    });
});
