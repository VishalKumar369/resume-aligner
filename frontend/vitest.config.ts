/// <reference types="vitest" />
import path from "node:path";
import { defineConfig } from "vitest/config";

// Vitest 3 + React 18. Tests live in ./tests, mirroring the source tree, so the
// app directories stay free of test files (Next would otherwise try to route them).
export default defineConfig({
    // Tests only need the JSX transform, not Fast Refresh, so esbuild handles it
    // directly — tsconfig.json's "jsx": "preserve" is for Next's compiler and
    // would otherwise leave JSX untransformed here.
    esbuild: { jsx: "automatic", jsxImportSource: "react" },
    resolve: {
        // Same "@/..." alias the app uses (see tsconfig.json paths).
        alias: { "@": path.resolve(__dirname, "./") },
    },
    test: {
        environment: "jsdom",
        globals: false,
        setupFiles: ["./tests/setup.ts"],
        include: ["tests/**/*.test.{ts,tsx}"],
        // Next injects NEXT_PUBLIC_* at build time; pin them here so assertions
        // don't depend on whatever .env.local or the shell happens to hold.
        env: {
            NEXT_PUBLIC_API_URL: "http://api.test",
        },
        restoreMocks: true,
        coverage: {
            provider: "v8",
            reporter: ["text", "html"],
            include: ["lib/**", "services/**", "store/**", "hooks/**", "components/**"],
        },
    },
});
