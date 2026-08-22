import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("axios", async () => {
    const { axiosCreate } = await import("../mocks/axios");
    return { default: { create: axiosCreate } };
});

import { axiosCreate, axiosInstance } from "../mocks/axios";
import {
    alignmentService,
    apiErrorMessage,
    authService,
    companyService,
    companySlug,
    dashboardService,
    jdService,
    learningService,
    resumeService,
    userService,
} from "@/services/api";
import { useAuthStore } from "@/store/authStore";

// services/api.ts wires the client up at import time. Capture what it registered
// before `restoreMocks` wipes the call history between tests.
const createArgs = axiosCreate.mock.calls[0]?.[0] as { baseURL: string; headers: Record<string, string> };
const [onRequest, onRequestError] = axiosInstance.interceptors.request.use.mock.calls[0] as [
    (config: any) => any,
    (error: any) => Promise<never>,
];
const [onResponse, onResponseError] = axiosInstance.interceptors.response.use.mock.calls[0] as [
    (response: any) => any,
    (error: any) => Promise<never>,
];

const API_URL = "http://api.test/api/v1";

describe("client setup", () => {
    it("points at the versioned API base from the environment", () => {
        expect(createArgs.baseURL).toBe(API_URL);
        expect(createArgs.headers["Content-Type"]).toBe("application/json");
    });
});

describe("request interceptor", () => {
    it("attaches the stored JWT as a bearer token", () => {
        useAuthStore.setState({ token: "jwt-123", user: null });

        const config = onRequest({ headers: {} });

        expect(config.headers.Authorization).toBe("Bearer jwt-123");
    });

    it("sends no Authorization header when signed out", () => {
        useAuthStore.setState({ token: null, user: null });

        const config = onRequest({ headers: {} });

        expect(config.headers.Authorization).toBeUndefined();
    });

    it("passes request errors straight through", async () => {
        const error = new Error("boom");
        await expect(onRequestError(error)).rejects.toBe(error);
    });
});

describe("response interceptor", () => {
    beforeEach(() => {
        useAuthStore.setState({
            token: "jwt-123",
            user: { id: "u-1", name: "Ada", email: "ada@example.com" },
        });
    });

    it("returns successful responses untouched", () => {
        const response = { status: 200, data: { ok: true } };

        expect(onResponse(response)).toBe(response);
    });

    it("clears the session on 401 so RouteGuard can bounce to login", async () => {
        const error = { response: { status: 401 } };

        await expect(onResponseError(error)).rejects.toBe(error);
        expect(useAuthStore.getState().token).toBeNull();
        expect(useAuthStore.getState().user).toBeNull();
    });

    it("keeps the session on other failures", async () => {
        const error = { response: { status: 500 } };

        await expect(onResponseError(error)).rejects.toBe(error);
        expect(useAuthStore.getState().token).toBe("jwt-123");
    });
});

describe("apiErrorMessage", () => {
    it("prefers a string detail from the backend", () => {
        expect(apiErrorMessage({ response: { data: { detail: "Email already registered" } } })).toBe(
            "Email already registered"
        );
    });

    it("reads the first message out of a FastAPI validation array", () => {
        const error = { response: { data: { detail: [{ msg: "field required", loc: ["body", "email"] }] } } };

        expect(apiErrorMessage(error)).toBe("field required");
    });

    it("explains a dead backend in plain language", () => {
        expect(apiErrorMessage({ message: "Network Error" })).toBe(
            "Cannot reach the server. Is the backend running?"
        );
    });

    it("falls back to the axios message, then to the supplied fallback", () => {
        expect(apiErrorMessage({ message: "Request failed with status code 500" })).toBe(
            "Request failed with status code 500"
        );
        expect(apiErrorMessage({}, "Upload failed")).toBe("Upload failed");
        expect(apiErrorMessage(null)).toBe("Something went wrong");
    });
});

describe("authService", () => {
    it("normalises the email before signing up", () => {
        authService.signup({ email: "  Ada@Example.COM ", password: "pw", full_name: "Ada" });

        expect(axiosInstance.post).toHaveBeenCalledWith("/auth/signup", {
            email: "ada@example.com",
            password: "pw",
            full_name: "Ada",
        });
    });

    it("posts login as form-encoded OAuth2 fields", () => {
        authService.login({ username: " Ada@Example.com ", password: "pw" });

        const [url, body, config] = axiosInstance.post.mock.calls[0];
        expect(url).toBe("/auth/login");
        expect((body as URLSearchParams).toString()).toBe("username=ada%40example.com&password=pw");
        expect(config.headers["Content-Type"]).toBe("application/x-www-form-urlencoded");
    });
});

describe("userService", () => {
    it("reads the signed-in account with no id in the path", () => {
        userService.getMe();

        expect(axiosInstance.get).toHaveBeenCalledWith("/me");
    });

    it("patches profile and notification settings separately", () => {
        userService.updateProfile({ full_name: "Ada L." });
        userService.updateNotifications({ weekly_career_readiness_report: false });

        expect(axiosInstance.patch).toHaveBeenNthCalledWith(1, "/me/profile", { full_name: "Ada L." });
        expect(axiosInstance.patch).toHaveBeenNthCalledWith(2, "/me/notifications", {
            weekly_career_readiness_report: false,
        });
    });

    it("requests the export as a blob so the auth header still applies", () => {
        userService.exportData();

        expect(axiosInstance.get).toHaveBeenCalledWith("/me/export", { responseType: "blob" });
    });

    it("sends the confirmation password in the delete body", () => {
        userService.deleteAccount("pw");

        expect(axiosInstance.delete).toHaveBeenCalledWith("/me", { data: { password: "pw" } });
    });
});

describe("resumeService", () => {
    const file = new File(["cv"], "resume.pdf", { type: "application/pdf" });

    it("uploads the file as multipart form data", () => {
        resumeService.upload(file);

        const [url, body, config] = axiosInstance.post.mock.calls[0];
        expect(url).toBe("/resume/upload");
        expect((body as FormData).get("file")).toBe(file);
        expect((body as FormData).has("label")).toBe(false);
        expect(config.headers["Content-Type"]).toBe("multipart/form-data");
    });

    it("trims the optional label and omits it when blank", () => {
        resumeService.upload(file, "  Data roles  ");
        resumeService.upload(file, "   ");

        expect((axiosInstance.post.mock.calls[0][1] as FormData).get("label")).toBe("Data roles");
        expect((axiosInstance.post.mock.calls[1][1] as FormData).has("label")).toBe(false);
    });

    it("sends optimize with a null focus area and single-page default", () => {
        resumeService.optimize("r-1", "j-1");

        expect(axiosInstance.post).toHaveBeenCalledWith("/resume/optimize", {
            resume_id: "r-1",
            jd_id: "j-1",
            focus_area: null,
            page_preference: "single",
        });
    });

    it("passes the chosen page preference and focus area", () => {
        resumeService.optimize("r-1", "j-1", { pagePreference: "multi", focusArea: "backend" });

        expect(axiosInstance.post).toHaveBeenCalledWith("/resume/optimize", {
            resume_id: "r-1",
            jd_id: "j-1",
            focus_area: "backend",
            page_preference: "multi",
        });
    });

    it("fetches lists, single resumes and versions", () => {
        resumeService.getAll({ skip: 10, limit: 5 });
        resumeService.getById("r-1");
        resumeService.getVersions("r-1");

        expect(axiosInstance.get).toHaveBeenNthCalledWith(1, "/resume/list", {
            params: { skip: 10, limit: 5 },
        });
        expect(axiosInstance.get).toHaveBeenNthCalledWith(2, "/resume/r-1");
        expect(axiosInstance.get).toHaveBeenNthCalledWith(3, "/resume/r-1/versions");
    });

    it("builds an absolute download URL and a blob download request", () => {
        expect(resumeService.downloadUrl("v-1", "docx")).toBe(
            `${API_URL}/resume/versions/v-1/download?format=docx`
        );

        resumeService.download("v-1", "pdf");
        expect(axiosInstance.get).toHaveBeenCalledWith("/resume/versions/v-1/download", {
            params: { format: "pdf" },
            responseType: "blob",
        });
    });
});

describe("jd, alignment, dashboard and learning services", () => {
    it("uploads a job description", () => {
        jdService.upload({ raw_text: "We need Python", title: "Data Scientist" });

        expect(axiosInstance.post).toHaveBeenCalledWith("/jd/upload", {
            raw_text: "We need Python",
            title: "Data Scientist",
        });
    });

    it("patches a JD with the verified role and company", () => {
        jdService.update("j-1", { title: "Backend Engineer", company_name: "Acme" });

        expect(axiosInstance.patch).toHaveBeenCalledWith("/jd/j-1", {
            title: "Backend Engineer",
            company_name: "Acme",
        });
    });

    it("generates an alignment from a resume and a jd", () => {
        alignmentService.generate("r-1", "j-1");

        expect(axiosInstance.post).toHaveBeenCalledWith("/alignment/generate", {
            resume_id: "r-1",
            jd_id: "j-1",
        });
    });

    it("passes alignment list filters as query params", () => {
        alignmentService.getAll({ resume_id: "r-1", latest_only: true, limit: 20 });

        expect(axiosInstance.get).toHaveBeenCalledWith("/alignment/list", {
            params: { resume_id: "r-1", latest_only: true, limit: 20 },
        });
    });

    it("lists every run for the dashboard tracker", () => {
        alignmentService.getAll({ limit: 100 });

        expect(axiosInstance.get).toHaveBeenCalledWith("/alignment/list", {
            params: { limit: 100 },
        });
    });

    it("hits the dashboard and learning endpoints", () => {
        dashboardService.getSummary();
        learningService.getRoadmap();

        expect(axiosInstance.get).toHaveBeenNthCalledWith(1, "/dashboard/summary");
        expect(axiosInstance.get).toHaveBeenNthCalledWith(2, "/learning/roadmap");
    });

    it("url-encodes the company id in the insights path", () => {
        companyService.getInsights("mathco & co");

        expect(axiosInstance.get).toHaveBeenCalledWith("/company/mathco%20%26%20co/insights");
    });
});

describe("companySlug", () => {
    it("lowercases and hyphenates, matching the backend slugify", () => {
        expect(companySlug("Goldman Sachs")).toBe("goldman-sachs");
        expect(companySlug("AT&T Inc.")).toBe("at-t-inc");
        expect(companySlug("  Acme  ")).toBe("acme");
    });

    it("trims leading and trailing separators", () => {
        expect(companySlug("!!Acme!!")).toBe("acme");
    });

    it("handles an empty or missing name", () => {
        expect(companySlug("")).toBe("");
        expect(companySlug(undefined as unknown as string)).toBe("");
    });
});
