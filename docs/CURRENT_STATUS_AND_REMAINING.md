# SupplyMind 当前项目状态与剩余需求

更新时间：2026-08-20

## 一、当前运行状态

当前项目使用 Docker Compose 运行，核心服务正常：

- API：`http://localhost:8000`
- 前端：`http://localhost:5173`
- Worker：Celery Worker
- PostgreSQL/pgvector：健康
- Redis：健康
- MinIO：健康
- 演示 PostgreSQL：健康
- 演示 MySQL：健康
- Alembic 当前版本：`0022_ai_governance_pgvector`

最近一次统一校验结果：

- Docker 内 pytest：`25 passed`
- 后端 `compileall`：通过
- 前端生产构建：通过
- `docker compose config --quiet`：通过
- API `/api/v1/health/live`：`ok`
- API `/api/v1/health/ready`：`ready`
- Helm `lint`：通过
- Helm `template`：通过
- 前端首页：HTTP `200`
- 真实模型链路：使用已配置的 Chat/Embedding Provider 对“近30天各工厂生产达成率与缺料风险”完成端到端分析；返回受 Guard 约束 SQL、3 行聚合结果、4 条 RAG 引用、图表规格和报告 ID。

## 二、已实现功能

### 身份、组织和权限

- 两个组织和四类角色。
- 登录、退出、刷新令牌轮换。
- 刷新令牌重放拒绝。
- 组织列表和组织切换。
- 成员邀请、接受、重发、角色修改、启用/停用。
- 跨组织资源隔离，跨组织资源统一返回 `404`。
- 前端登录支持邮箱、密码和组织标识输入。
- 前端按角色隐藏审计入口。
- 无权限、资源不存在、登录过期提示。

### 数据源和 Schema

- PostgreSQL/MySQL 数据源。
- 真实连接测试。
- Schema 同步任务和快照。
- 表、列、主键、外键、索引、注释展示。
- 白名单管理。
- SQL Guard 只读查询。
- 查询耗时、行数和脱敏状态。
- 数据源停用后禁止查询。
- TLS 要求可由组织管理员独立更新并审计。

### 知识库和向量检索

- Markdown、TXT、PDF 上传。
- 文本提取、分类、分块。
- 真实 Embedding API。
- Embedding 失败时 fail-closed。
- 摄取任务状态、重试、取消和死信。
- 文档归档、删除和原文查看。
- 引用位置、相似度和文档版本信息。
- 指标名称、定义、公式、单位、适用工厂、适用产品线、生效时间。
- 文档元数据前端编辑。
- 重复文件标记。
- 文档版本记录、版本列表和管理员回滚并重新摄取。

### 分析会话

- 明确选择数据源和知识库。
- 真实 SQL 查询。
- 八阶段 Agent 轨迹。
- SQL 草案、最终 SQL 和 SQL Guard 结果。
- SSE 流式执行。
- 分析重试、取消、幂等键。
- 查询行、图表、洞察和引用。
- 分析运行事件恢复接口。

### 报告中心

- Markdown 报告。
- SQL、图表、洞察、引用和运行元数据。
- PDF 导出状态。
- MinIO/S3 对象存储。
- checksum。
- 导出失败重试。
- 报告筛选和导出历史。
- 下载失败 Trace ID。

### 供应链大屏

- 采购交付。
- 生产达成。
- 库存健康度。
- 质量合格率。
- 订单履约。
- 真实 SQL 聚合。
- 工厂、供应商、产品线筛选。
- 趋势、排行和异常项。
- 刷新任务状态。
- 组织级刷新间隔和布局配置。

### 审计、系统状态和交付

- 审计分页、筛选、详情和 Trace ID。
- 失败/死信摄取任务支持分页查看和管理员重新入队。
- 敏感字段脱敏。
- API、Worker、数据库、Redis、模型、MinIO、MCP 和数据源状态。
- 独立系统状态导航页面。
- GitHub Actions CI。
- Helm lint/template 检查。
- Docker 空环境运行手册。

## 三、外部验收结果

已通过：

- Helm lint。
- Helm template。
- Docker Compose 服务健康检查。
- 登录、组织切换和刷新令牌轮换。
- 刷新令牌重放拒绝，返回 `401`。
- 跨组织数据源访问，返回 `404`。
- 真实数据源查询，返回真实查询行和 Guard 表信息。
- 供应链大屏五类指标。
- 当前环境知识库检索。
- 无效登录返回 `401`。
- 只读成员访问成员管理返回 `403`。

发现的问题：

- 分析请求的前置条件已增加结构化错误码，会明确返回数据源、知识库、归档状态或白名单缺失原因。

## 四、尚未完全完成的需求

### 高优先级

1. 浏览器完整主路径：登录、组织切换、角色权限、数据源、知识库、分析、报告、大屏。

### 中优先级

1. 文档版本替换上传、历史和回滚接口及前端入口已完成；仍需浏览器端完整回归。
2. 数据源 TLS/网络向导前端仍需补齐；TLS 后端配置接口已完成。
3. 查询超时和脱敏配置页面。
4. PDF 下载成功、MinIO 故障和文件未就绪页面。
5. 大屏独立配置页面、导航入口和组件显隐已完成；仍需浏览器端完整回归。
6. Worker 失败任务和死信任务后端入口及系统状态页操作面板已完成；仍需浏览器端完整回归。

### 交付和工程化

1. CI 实际运行记录。
2. SAST、依赖漏洞扫描和镜像扫描已加入 CI，仍需 CI 平台实际运行记录。
3. PostgreSQL RLS 空库验证。
4. Alembic 回滚实测。
5. Helm lint/template 已通过；集群部署和回滚实测受当前机器无 Kubernetes context 阻塞。
6. 空环境从零部署复现。
7. 课程材料、讲师稿、作业和评分标准。

## 五、建议的新窗口开发顺序

### 第一批

1. 定位分析接口 `422`。
2. 修正分析前置条件和错误展示。
3. 完成分析 SSE 浏览器恢复。

### 第二批

1. 完整浏览器主路径。
2. OIDC Mock Provider 集成。
3. 报告 PDF/MinIO 故障路径。

### 第三批

1. 文档版本生命周期。
2. 大屏显隐和配置页。
3. CI、SAST、镜像扫描、Helm 部署和回滚。

每完成三个大模块后，再统一执行：

```powershell
docker compose up -d --build
docker compose exec -T api alembic upgrade head
docker compose exec -T api pytest -q
docker compose exec -T api python -m compileall -q /app/app
npm --prefix frontend run build
docker compose config --quiet
docker run --rm -v "${PWD}/infra/helm/supplymind:/chart:ro" alpine/helm:3.16.4 lint /chart
docker run --rm -v "${PWD}/infra/helm/supplymind:/chart:ro" alpine/helm:3.16.4 template supplymind /chart
```

## 六、当前开发约束

- 不使用静态分析答案、假向量、静态图表或伪造报告。
- Chat/Embedding/数据源不可用时必须明确失败并记录 Trace ID 与审计。
- 保持 `/api/v1`、Docker Compose 服务名和多租户隔离兼容。
- 任何模块只有在 API、数据库、前端、Worker、权限隔离和验收证据齐全后才标记完成。
