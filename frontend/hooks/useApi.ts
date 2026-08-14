"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { apiErrorMessage } from "@/services/api";

interface ApiState<T> {
    data: T | null;
    loading: boolean;
    error: string | null;
    reload: () => void;
}

/**
 * Fetch on mount with loading and error state.
 *
 * Every page in this app shows real data or says why it cannot, so the three
 * states are handled in one place rather than re-implemented per page.
 */
export function useApi<T>(
    fetcher: () => Promise<{ data: T }>,
    deps: unknown[] = [],
    options: { skip?: boolean } = {}
): ApiState<T> {
    const [data, setData] = useState<T | null>(null);
    const [loading, setLoading] = useState(!options.skip);
    const [error, setError] = useState<string | null>(null);
    const [nonce, setNonce] = useState(0);

    // Keeping the fetcher in a ref lets callers pass an inline arrow function
    // without re-running the effect on every render.
    const fetcherRef = useRef(fetcher);
    fetcherRef.current = fetcher;

    useEffect(() => {
        if (options.skip) {
            setLoading(false);
            return;
        }

        let cancelled = false;
        setLoading(true);
        setError(null);

        fetcherRef
            .current()
            .then((response) => {
                if (!cancelled) setData(response.data);
            })
            .catch((err) => {
                if (!cancelled) setError(apiErrorMessage(err));
            })
            .finally(() => {
                if (!cancelled) setLoading(false);
            });

        return () => {
            cancelled = true;
        };
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [...deps, nonce, options.skip]);

    const reload = useCallback(() => setNonce((value) => value + 1), []);

    return { data, loading, error, reload };
}
