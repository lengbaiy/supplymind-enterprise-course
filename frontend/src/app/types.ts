export type DashboardFilters = {
  factory: string;
  productLine: string;
  period: "7d" | "30d" | "90d";
};

export type Dashboard = {
  cards: { label: string; value: string; change: string }[];
  trend: { month: string; rate: number }[];
  cache_status?: string;
  refreshed_at?: string;
  refresh_interval_seconds?: number;
  filters?: { factory?: string | null; product_line?: string | null; period?: string | null };
};
