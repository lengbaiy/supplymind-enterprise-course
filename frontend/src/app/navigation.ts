export const NAV_ITEMS = ["运营总览", "项目管理", "分析会话", "数据源", "知识库", "报告中心", "组织与审计"] as const;

export type NavItem = (typeof NAV_ITEMS)[number];
