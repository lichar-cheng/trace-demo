# 多知识库平台架构说明（Flask + Vue）

## 1. 技术栈与分层

- 前端：`HTML + Vue3 + Axios + CSS`（无打包，直接静态部署）
- 后端：`Flask + SQLAlchemy + Pydantic`
- 存储：`SQLite`（`backend/data.db`）

### 后端分层（单文件内按区域组织，后续可平移成多文件）

1. **基础层**（数据库和输入校验）
   - `backend/models.txt`：SQLAlchemy 模型
   - `backend/schemas.txt`：Pydantic 入参模型
2. **API层**
   - `backend/app.txt` 中 `api Blueprint`
3. **系统层**
   - `health`、`proxy/x`、`backup`

### 前端分层

1. `store`：`frontend/src/main.js` 中 `createStore()`，集中管理状态
2. `actions`：`sync/load/compare/topic/youtube/crypto/chart/backup`
3. `view`：顶部工具条、左侧列表、中间详情、右侧模块面板
4. `api`：`frontend/src/services/api.js` 唯一网络出口

---

## 2. 核心数据模型

- `KolPost`：X 抓取原始帖子
- `BrowseLog`：浏览行为日志
- `KnowledgeItem`：统一知识项主表（支持 x/youtube/crypto/chart）
- `Topic`：主题聚合结果（短中长期观点）
- `EntityProfile`：人物画像

> 调整字段时优先改 `models.txt` + `schemas.txt`，然后改对应 API，最后改 `api.js` 和 `main.js` 的 UI 映射。

---

## 3. API 模块边界

- `X采集`: `/api/posts/*`, `/api/browse-log/*`
- `对比`: `/api/compare/urls`
- `主题`: `/api/topics/*`
- `多源导入`: `/api/youtube/*`, `/api/crypto/*`, `/api/charts/*`
- `备份`: `/api/backup/run`

建议后续拆分为：
- `routes/x_routes.py`
- `routes/topic_routes.py`
- `routes/source_routes.py`
- `services/*.py`（业务逻辑）

---

## 4. 开发原则（保证“改局部不动全局”）

1. **改接口**：只动 `app.txt` 对应路由和 `schemas.txt`。
2. **改数据结构**：只动 `models.txt` + 映射响应结构。
3. **改页面交互**：只动 `main.js` 对应模块区块模板和 action。
4. **改请求地址或参数**：只动 `services/api.js`。
5. **改视觉样式**：只动 `styles.css`。

---

## 5. 典型需求改动路径

### 例1：新增“人物可靠度筛选”
- 后端：`GET /api/entities` 增加过滤参数
- 前端：右侧主题页增加过滤输入
- 文档：在本文件 API 边界追加参数说明

### 例2：新增“图表快照状态（待分析/已分析）”
- 模型：`KnowledgeItem.analysis_status`
- 接口：`/api/charts/capture` 写默认状态；`/api/charts/analyze` 更新状态
- 前端：多源导入面板增加状态显示

### 例3：YouTube 批量导入加时间范围
- schema：`YoutubeImportPayload`
- route：`/api/youtube/import` 使用 `start_time/end_time`
- frontend：新增时间输入框并传参
