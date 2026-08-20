# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

制造业供应链组织的组织管理员、分析师、只读成员和平台管理员。用户在日常运营中需要安全地连接只读数据源、管理知识口径、分析供应链风险并交付报告。

## Product Purpose

SupplyMind 是一个多租户、只读的制造供应链 AI 数据分析控制台。它将真实数据源、知识库检索、可审计分析、报告交付和运营监控连接为连续工作流。

## Positioning

平台以组织隔离、SQL Guard、真实数据查询、审计追踪和可恢复异步任务为边界，不能以模拟结论替代不可用的生产能力。

## Capabilities and Constraints

- 保持 `/api/v1`、Docker Compose 服务名、多租户隔离和跨组织 `404` 语义兼容。
- 仅支持只读外部数据源；密钥不返回前端；模型或依赖故障必须明确失败并保留 Trace ID。
- 前端使用 React、Vite、TypeScript、ECharts，并逐步迁移为按领域组织的可维护界面。

## Brand Commitments

保留 SupplyMind 名称、中文业务语言和制造供应链场景。界面为浅色现代工业运营台，使用深墨绿作为主强调色，强调信息密度、可信赖性和可操作性。

## Evidence on Hand

现有 Docker 环境、演示 PostgreSQL/MySQL 数据库、后端接口契约、测试以及供应链知识库内容均在仓库中。不得编造客户、生产指标或模型结果。

## Product Principles

- 真实能力优先，失败明确可追踪。
- 高风险操作必须受权限、确认和审计保护。
- 数据密集页面首先服务于扫描、判断和行动。
- 每个领域可独立测试、演进和回滚。
