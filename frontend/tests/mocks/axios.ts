import { vi } from "vitest";

/**
 * Fake axios instance. services/api.ts builds one instance at import time, so
 * tests can assert on the exact URL, body and headers each service sends
 * without a network layer in between.
 */
export const axiosInstance = {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
    interceptors: {
        request: { use: vi.fn() },
        response: { use: vi.fn() },
    },
};

export const axiosCreate = vi.fn((..._config: any[]) => axiosInstance);
