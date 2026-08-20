import { useQuery } from "@tanstack/react-query";
import type { Source } from "../../../app/domain-types";
import { API_BASE, apiRequest } from "../../../services/api";

export const dataSourceKeys = { all: (organizationId?: string) => ["data-sources", organizationId] as const };
export function useDataSources(token: string, organizationId?: string) {
  return useQuery({ queryKey: dataSourceKeys.all(organizationId), queryFn: () => apiRequest<Source[]>(API_BASE, token, "/data-sources"), enabled: Boolean(token) });
}
