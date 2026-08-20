import { useQuery } from "@tanstack/react-query";
import type { KnowledgeBase } from "../../../app/domain-types";
import { API_BASE, apiRequest } from "../../../services/api";

export const knowledgeKeys = { list: (organizationId?: string, filters?: { name?: string; status?: string }) => ["knowledge-bases", organizationId, filters] as const };
export function useKnowledgeBases(token: string, organizationId?: string, filters: { name?: string; status?: string } = {}) {
  const query = new URLSearchParams({ page: "1", page_size: "50", ...(filters.name ? { name: filters.name } : {}), ...(filters.status ? { status: filters.status } : {}) });
  return useQuery({ queryKey: knowledgeKeys.list(organizationId, filters), queryFn: () => apiRequest<KnowledgeBase[]>(API_BASE, token, `/knowledge-bases?${query}`), enabled: Boolean(token) });
}
