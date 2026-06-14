import { QueryClient } from "@tanstack/react-query";
import { ApiClientError } from "./apiClient";

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: (failureCount, error) => {
        // Don't retry auth/permission errors.
        if (error instanceof ApiClientError && [401, 403, 404].includes(error.status)) {
          return false;
        }
        return failureCount < 2;
      },
      refetchOnWindowFocus: false,
    },
  },
});
