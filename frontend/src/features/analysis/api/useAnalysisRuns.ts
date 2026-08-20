import { useQuery } from "@tanstack/react-query";
import type { AnalysisRun } from "../../../app/domain-types";
import { API_BASE, apiRequest } from "../../../services/api";

export const analysisKeys = { list: (organizationId?: string, page = 1, pageSize = 10) => ["analyses", organizationId, page, pageSize] as const };
export function useAnalysisRuns(token: string, organizationId?: string, page = 1, pageSize = 10) {
  return useQuery({ queryKey: analysisKeys.list(organizationId, page, pageSize), queryFn: () => apiRequest<AnalysisRun[]>(API_BASE, token, `/analyses?page=${page}&page_size=${pageSize}`), enabled: Boolean(token) });
}
