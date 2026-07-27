"use client";

import { useEffect, useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import { useAuthStore } from "@/store/authStore";

export function RouteGuard({ children }: { children: React.ReactNode }) {
    const router = useRouter();
    const pathname = usePathname();
    const { token } = useAuthStore();
    const [mounted, setMounted] = useState(false);
    const [authorized, setAuthorized] = useState(false);

    useEffect(() => {
        setMounted(true);
    }, []);

    useEffect(() => {
        if (!mounted) return;

        // Paths that do not require authentication
        const publicPaths = ["/", "/auth/login", "/auth/signup"];
        const path = pathname.split("?")[0];
        const isPublicPath = publicPaths.includes(path);

        if (!token && !isPublicPath) {
            setAuthorized(false);
            router.replace("/auth/login");
        } else if (token && isPublicPath && path !== "/") {
            // Logged in users shouldn't access login/signup pages
            setAuthorized(true);
            router.replace("/dashboard");
        } else {
            setAuthorized(true);
        }
    }, [pathname, token, router, mounted]);

    // Prevent hydration mismatch by rendering nothing until mounted on the client
    if (!mounted) return null;

    return authorized ? <>{children}</> : null;
}
