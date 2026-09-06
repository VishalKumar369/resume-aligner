import axios from "axios";
import { useAuthStore } from "@/store/authStore";

const API_URL = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000") + "/api/v1";
const api = axios.create({ baseURL: API_URL, headers: { "Content-Type": "application/json" } });

const normalizeEmail = (email: string) => email.trim().toLowerCase();

// Attach the JWT. Every data endpoint is scoped to the token's owner, so a
// request without one is rejected rather than served the wrong user's data.
api.interceptors.request.use(
    (config) => {
        const token = useAuthStore.getState().token;
        if (token) {
            config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
    },
    (error) => Promise.reject(error)
);

// An expired or invalid token means the session is over; clear it so RouteGuard
// sends the user to login instead of looping on 401s.
api.interceptors.response.use(
    (response) => response,
    (error) => {
        if (error?.response?.status === 401 && typeof window !== "undefined") {
            useAuthStore.getState().clearAuth();
        }
        return Promise.reject(error);
    }
);

/** Pull a readable message out of an axios error. */
export const apiErrorMessage = (error: any, fallback = "Something went wrong"): string => {
    const detail = error?.response?.data?.detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail) && detail[0]?.msg) return detail[0].msg;
    if (error?.message === "Network Error") return "Cannot reach the server. Is the backend running?";
    return error?.message || fallback;
};

// ---------------------------------------------------------------------- auth

export const authService = {
    signup: (data: { email: string; password: string; full_name: string }) =>
        api.post("/auth/signup", { ...data, email: normalizeEmail(data.email) }),
    login: (data: { username: string; password: string }) => {
        const params = new URLSearchParams();
        params.append("username", normalizeEmail(data.username));
        params.append("password", data.password);
        return api.post("/auth/login", params, {
            headers: { "Content-Type": "application/x-www-form-urlencoded" },
        });
    },
};

// ------------------------------------------------------------------ account

export interface MeResponse {
    profile: { full_name: string | null; email: string; target_role: string | null };
    notifications: {
        email_alerts_on_new_matches: boolean;
        weekly_career_readiness_report: boolean;
    };
    account: { id: string; created_at: string };
}

/** Account settings, all scoped to the signed-in user by the JWT (no ids in the path). */
export const userService = {
    getMe: () => api.get<MeResponse>("/me"),
    updateProfile: (data: { full_name?: string; target_role?: string }) =>
        api.patch<MeResponse["profile"]>("/me/profile", data),
    updateNotifications: (data: Partial<MeResponse["notifications"]>) =>
        api.patch<MeResponse["notifications"]>("/me/notifications", data),
    /** Blob so the JSON download flows through axios with the auth header attached. */
    exportData: () => api.get("/me/export", { responseType: "blob" }),
    deleteAccount: (password: string) => api.delete("/me", { data: { password } }),
};

// -------------------------------------------------------------------- resume

export const resumeService = {
    upload: (file: File, label?: string) => {
        const form = new FormData();
        form.append("file", file);
        if (label && label.trim()) form.append("label", label.trim());
        return api.post("/resume/upload", form, {
            headers: { "Content-Type": "multipart/form-data" },
        });
    },
    getAll: (params?: { skip?: number; limit?: number }) => api.get("/resume/list", { params }),
    getById: (resumeId: string) => api.get(`/resume/${resumeId}`),
    optimize: (
        resumeId: string,
        jdId: string,
        options: { focusArea?: string; pagePreference?: "single" | "multi" } = {}
    ) =>
        api.post("/resume/optimize", {
            resume_id: resumeId,
            jd_id: jdId,
            focus_area: options.focusArea || null,
            page_preference: options.pagePreference || "single",
        }),
    getVersions: (resumeId: string) => api.get(`/resume/${resumeId}/versions`),
    downloadUrl: (versionId: string, format: "docx" | "pdf") =>
        `${API_URL}/resume/versions/${versionId}/download?format=${format}`,
    /** Downloads go through axios so the Authorization header is sent. */
    download: (versionId: string, format: "docx" | "pdf") =>
        api.get(`/resume/versions/${versionId}/download`, {
            params: { format },
            responseType: "blob",
        }),
};

// ------------------------------------------------------------------------ jd

export const jdService = {
    upload: (data: { raw_text: string; title: string; url?: string; company_name?: string }) =>
        api.post("/jd/upload", data),
    getAll: (params?: { skip?: number; limit?: number }) => api.get("/jd/list", { params }),
    getById: (jdId: string) => api.get(`/jd/${jdId}`),
    /** Persist the user's verified role/company from the review step. */
    update: (jdId: string, data: { title?: string; company_name?: string }) =>
        api.patch(`/jd/${jdId}`, data),
};

// ----------------------------------------------------------------- alignment

export const alignmentService = {
    generate: (resumeId: string, jdId: string) =>
        api.post("/alignment/generate", { resume_id: resumeId, jd_id: jdId }),
    getAll: (params?: { resume_id?: string; jd_id?: string; latest_only?: boolean; limit?: number }) =>
        api.get("/alignment/list", { params }),
    getById: (alignmentId: string) => api.get(`/alignment/${alignmentId}`),
    // Deletes the run; if it was the JD's last analysis, its posting and
    // tailored versions go too (see the backend delete endpoint).
    remove: (alignmentId: string) => api.delete(`/alignment/${alignmentId}`),
};

// ------------------------------------------------------- dashboard & learning

export const dashboardService = {
    getSummary: () => api.get("/dashboard/summary"),
};

export const learningService = {
    getRoadmap: () => api.get("/learning/roadmap"),
    /** Interview question bank for a skill (grouped by difficulty). */
    getQuestions: (skill: string) => api.get("/learning/questions", { params: { skill } }),
};

export const companyService = {
    getAll: () => api.get("/company/list"),
    getInsights: (companyId: string) => api.get(`/company/${encodeURIComponent(companyId)}/insights`),
};

export interface NoteInput {
    title?: string;
    content?: string;
    category?: string;
    color?: string;
    target_date?: string | null;
    is_pinned?: boolean;
    is_completed?: boolean;
}

/** Personal planner notes, all scoped to the signed-in user by the JWT. */
export const noteService = {
    getAll: () => api.get("/notes"),
    create: (data: NoteInput) => api.post("/notes", data),
    update: (id: string, data: NoteInput) => api.patch(`/notes/${id}`, data),
    remove: (id: string) => api.delete(`/notes/${id}`),
};

/** Matches the backend's slugify, so links built here resolve server-side. */
export const companySlug = (name: string) =>
    (name || "").toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "");

export default api;
