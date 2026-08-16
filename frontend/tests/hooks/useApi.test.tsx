import { act, renderHook, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { useApi } from "@/hooks/useApi";

describe("useApi", () => {
    it("starts in the loading state and then exposes the payload", async () => {
        const fetcher = vi.fn().mockResolvedValue({ data: { score: 82 } });

        const { result } = renderHook(() => useApi(fetcher));

        expect(result.current.loading).toBe(true);
        expect(result.current.data).toBeNull();

        await waitFor(() => expect(result.current.loading).toBe(false));
        expect(result.current.data).toEqual({ score: 82 });
        expect(result.current.error).toBeNull();
        expect(fetcher).toHaveBeenCalledTimes(1);
    });

    it("surfaces a readable message when the request fails", async () => {
        const fetcher = vi
            .fn()
            .mockRejectedValue({ response: { data: { detail: "Resume not found" } } });

        const { result } = renderHook(() => useApi(fetcher));

        await waitFor(() => expect(result.current.loading).toBe(false));
        expect(result.current.error).toBe("Resume not found");
        expect(result.current.data).toBeNull();
    });

    it("reports an unreachable backend rather than a raw axios message", async () => {
        const fetcher = vi.fn().mockRejectedValue({ message: "Network Error" });

        const { result } = renderHook(() => useApi(fetcher));

        await waitFor(() =>
            expect(result.current.error).toBe("Cannot reach the server. Is the backend running?")
        );
    });

    it("does not fetch while skipped, and stops loading", async () => {
        const fetcher = vi.fn().mockResolvedValue({ data: {} });

        const { result } = renderHook(() => useApi(fetcher, [], { skip: true }));

        await waitFor(() => expect(result.current.loading).toBe(false));
        expect(fetcher).not.toHaveBeenCalled();
        expect(result.current.data).toBeNull();
    });

    it("fetches once the skip flag clears", async () => {
        const fetcher = vi.fn().mockResolvedValue({ data: { ok: true } });

        const { result, rerender } = renderHook(({ skip }) => useApi(fetcher, [], { skip }), {
            initialProps: { skip: true },
        });

        expect(fetcher).not.toHaveBeenCalled();

        rerender({ skip: false });

        await waitFor(() => expect(result.current.data).toEqual({ ok: true }));
        expect(fetcher).toHaveBeenCalledTimes(1);
    });

    it("refetches when reload is called", async () => {
        const fetcher = vi
            .fn()
            .mockResolvedValueOnce({ data: { n: 1 } })
            .mockResolvedValueOnce({ data: { n: 2 } });

        const { result } = renderHook(() => useApi(fetcher));
        await waitFor(() => expect(result.current.data).toEqual({ n: 1 }));

        act(() => result.current.reload());

        await waitFor(() => expect(result.current.data).toEqual({ n: 2 }));
        expect(fetcher).toHaveBeenCalledTimes(2);
    });

    it("refetches when a dependency changes", async () => {
        const fetcher = vi.fn().mockResolvedValue({ data: { ok: true } });

        const { rerender } = renderHook(({ id }) => useApi(fetcher, [id]), {
            initialProps: { id: "r-1" },
        });
        await waitFor(() => expect(fetcher).toHaveBeenCalledTimes(1));

        rerender({ id: "r-2" });
        await waitFor(() => expect(fetcher).toHaveBeenCalledTimes(2));

        // Same dependency, no extra request.
        rerender({ id: "r-2" });
        expect(fetcher).toHaveBeenCalledTimes(2);
    });

    it("does not re-run when the caller passes a fresh inline fetcher each render", async () => {
        const call = vi.fn().mockResolvedValue({ data: { ok: true } });

        const { rerender } = renderHook(() => useApi(() => call()));
        await waitFor(() => expect(call).toHaveBeenCalledTimes(1));

        rerender();
        rerender();

        expect(call).toHaveBeenCalledTimes(1);
    });

    it("ignores a response that lands after unmount", async () => {
        let resolve!: (value: { data: unknown }) => void;
        const fetcher = vi.fn(() => new Promise<{ data: unknown }>((r) => (resolve = r)));
        const errorSpy = vi.spyOn(console, "error").mockImplementation(() => {});

        const { unmount } = renderHook(() => useApi(fetcher));
        unmount();

        await act(async () => {
            resolve({ data: { late: true } });
        });

        expect(errorSpy).not.toHaveBeenCalled();
    });
});
