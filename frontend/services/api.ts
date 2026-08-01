import axios from "axios";
import { useAuthStore } from "@/store/authStore";

const API_URL = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000") + "/api/v1";
const api = axios.create({ baseURL: API_URL, headers: { "Content-Type": "application/json" } });

const normalizeEmail = (email: string) => email.trim().toLowerCase();

// Add request interceptor to inject JWT token
api.interceptors.request.use(
    (config) => {
        const token = useAuthStore.getState().token;
        if (token) {
            config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
    },
    (error) => {
        return Promise.reject(error);
    }
);

// Auth Service
export const authService = {
    signup: (data: { email: string; password: string; full_name: string }) =>
        api.post("/auth/signup", { ...data, email: normalizeEmail(data.email) }),
    login: (data: { username: string; password: string }) => {
        const params = new URLSearchParams();
        params.append("username", normalizeEmail(data.username));
        params.append("password", data.password);
        return api.post("/auth/login", params, {
            headers: {
                "Content-Type": "application/x-www-form-urlencoded"
            }
        });
    }
};

// Resume Service
export const resumeService = {
    upload: (file: File, label: string) => {
        const form = new FormData();
        form.append("file", file);
        form.append("label", label);
        return api.post("/resume/upload", form, { headers: { "Content-Type": "multipart/form-data" } });
    },
    getAll: () => api.get("/resume/list"),
    optimize: (resumeId: string, jdId: string) => api.post("/resume/optimize", { resume_id: resumeId, jd_id: jdId }),
};

// JD Service
export const jdService = {
    upload: (data: { raw_text: string; title: string; url?: string; company_name?: string }) => api.post("/jd/upload", data),
};

// Alignment Service
export const alignmentService = {
    generate: (resumeId: string, jdId: string) =>
        api.post("/alignment/generate", { resume_id: resumeId, jd_id: jdId }),
};

// Dashboard Service
export const dashboardService = {
    getSummary: () => api.get("/dashboard/summary"),
};

// Learning Service
export const learningService = {
    getRoadmap: () => api.get("/learning/roadmap"),
};

// Company Service
export const companyService = {
    getInsights: (companyId: string) => api.get(`/company/${companyId}/insights`),
};
