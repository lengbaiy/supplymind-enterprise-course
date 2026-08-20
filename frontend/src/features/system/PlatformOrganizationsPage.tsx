import { DataView } from "../../components/DataView";
import { OrganizationAdminPanel, type PlatformOrganization } from "./OrganizationAdminPanel";

export function PlatformOrganizationsPage({ organizations, busy, onToggle, onRename }: { organizations: PlatformOrganization[]; busy: boolean; onToggle: (item: PlatformOrganization) => void; onRename: (item: PlatformOrganization, name: string) => void }) {
  return <DataView kicker="PLATFORM / TENANTS" title="企业管理" copy="集中管理企业组织与平台级访问状态。"><OrganizationAdminPanel organizations={organizations} busy={busy} onToggle={onToggle} onRename={onRename} /></DataView>;
}
