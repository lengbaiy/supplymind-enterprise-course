import type { AuditEvent } from "../features/audit/AuditPanel";

export type Source = {
  id: string;
  name: string;
  engine: string;
  host: string;
  port: number;
  database_name: string;
  allowed_tables: string[];
  tls_required?: boolean;
  status?: string;
  last_tested_at?: string;
  last_synced_at?: string;
};

export type KnowledgeBase = { id: string; name: string; description: string };
export type Report = {
  id: string; title: string; markdown?: string; citations?: Record<string, unknown>[];
  status: string; created_at: string; analysis_status?: string; analysis_sql?: string;
  analysis_sql_draft?: string; analysis_result?: Record<string, unknown>;
  data_source_id?: string; knowledge_base_id?: string;
};
export type ReportExport = { id: string; format: string; status: string; error_message?: string; created_at: string; updated_at: string };
export type AnalysisRun = {
  id: string; status: string; question: string; data_source_id?: string; knowledge_base_id?: string;
  sql?: string; sql_draft?: string; guard_error?: string; result?: Record<string, unknown>; created_at: string;
};
export type AgentStep = {
  id: string; name: string; status: string; input_summary: string; output: Record<string, unknown>;
  elapsed_ms?: number; error_message?: string; created_at: string;
};
export type Member = { user_id: string; email: string; display_name: string; role: string; is_active: boolean };
export type Invitation = { id: string; email: string; role: string; status: string; expires_at: string; created_at: string; token?: string };
export type Document = {
  id: string; knowledge_base_id: string; filename: string; status: string; is_archived?: boolean;
  category?: string; embedding_model?: string; embedding_dimension?: number; error_message?: string;
  chunk_count: number; ingestion_task_id?: string; created_at: string;
};
export type KnowledgeDetail = KnowledgeBase & { is_archived: boolean; archived_at?: string };
export type Citation = { document_name?: string; document_id?: string; text?: string; score?: number; location?: Record<string, unknown> };
export type DocumentSource = { document_id: string; filename: string; version: number; category?: string; status: string; chunks: { id: string; ordinal: number; text: string; location?: Record<string, unknown> }[] };
export type AnalysisResult = {
  run_id?: string; trace_id?: string; sql?: string; sql_draft?: string; guard_error?: string;
  result?: { rows?: Record<string, unknown>[]; insight?: string; insights?: { facts?: string[]; risks?: string[]; recommendations?: string[]; evidence?: Record<string, unknown>[] }; chart?: Record<string, unknown>; citations?: Record<string, unknown>[]; report_id?: string };
  report_id?: string;
};
export type OrganizationSummary = {
  id: string; slug: string; name: string; owner_user_id?: string | null; owner_name?: string | null;
  role: string; member_count: number; active_member_count: number; data_source_count: number;
  knowledge_base_count: number; report_count: number; dashboard_count: number; quota: Record<string, number>; quota_usage: Record<string, number>;
};
export type OrganizationAccess = { id: string; slug: string; name: string; role: string };
export type PermissionMatrix = { roles: Record<string, Record<string, boolean>> };
export type SystemStatus = { status: string; dependencies: Record<string, { status: string; error?: string; node_count?: string; active_tasks?: string }>; data_sources: { id: string; name: string; host: string; status: string; last_tested_at?: string }[] };
export type SchemaTable = {
  name?: string; table_name?: string; columns?: { name: string; type: string; nullable?: boolean; comment?: string | null }[];
  primary_key?: string[]; foreign_keys?: { constrained_columns?: string[]; referred_table?: string; referred_columns?: string[] }[];
  indexes?: { name?: string; column_names?: string[]; unique?: boolean }[]; comment?: string | null; sample_limit?: number;
};
export type AuditEventView = AuditEvent;
