# trace-demo 全量交付版本

这是一个可本地部署的多知识库可视化分析项目（Flask + Vue）。

## 一键启动（推荐）

```bash
bash scripts/bootstrap.sh
bash scripts/run_backend.sh
# 新终端
bash scripts/run_frontend.sh
```

打开：`http://localhost:4173`

## 目录说明

- `backend/`：Flask API、SQLAlchemy 模型、Pydantic 请求模型
- `frontend/`：纯静态 HTML + Vue3 + Axios
- `docs/`：架构与变更说明
- `scripts/`：启动和自检脚本

## 关键能力

- X Library：列表、详情、链接对比、删除、推送 TG（状态标记）
- YouTube Library：导入、列表、分析
- Crypto Metrics：拉取、历史回补、列表
- Chart Snapshots：采集、分析、列表
- Topic Intelligence：主题创建、主题分析、实体查看
- 备份：本地 DB 备份

## 后端接口总入口

- 健康检查：`GET /health`
- API：`/api/*`

## 注意

- 数据库为 SQLite：`backend/data.db`
- 前端默认请求 `http://localhost:8000`
- 如端口冲突，改 `frontend/src/services/api.js` 中 `apiBase`
