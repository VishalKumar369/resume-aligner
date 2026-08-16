import { vi } from "vitest";

/**
 * Shared stand-in for the App Router. `next/navigation` is mocked once in
 * tests/setup.ts and reads from here, so a test can set the current path and
 * then assert on navigation without rendering a real router.
 */
export const routerMock = {
    push: vi.fn(),
    replace: vi.fn(),
    refresh: vi.fn(),
    back: vi.fn(),
    forward: vi.fn(),
    prefetch: vi.fn(),
};

let pathname = "/dashboard";

export const getPathname = () => pathname;

export const setPathname = (next: string) => {
    pathname = next;
};

export const resetRouter = () => {
    pathname = "/dashboard";
    Object.values(routerMock).forEach((fn) => fn.mockClear());
};
