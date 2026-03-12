<!-- Last Edited: 2026-03-12 -->
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
- X 采集接口：`POST /api/collect`（支持反向时间线去重、自动打标、可选图片本地化）
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


## Collect 接口鉴权

- 环境变量：`COLLECT_AUTH_TOKEN`（默认 `1`）
- 请求体：`{ auth, data[] }`，其中 `data` 支持 `id/full_text/user_handle/url/media_urls/extra`。


## YouTube 独立流水线（已拆分模块）

- 模块目录：`backend/services/youtube/`
  - `fetcher.py`（频道视频抓取）
  - `downloader.py`（yt-dlp 下载）
  - `transcriber.py`（faster-whisper 转写）
  - `pipeline.py`（主调度）
- 独立运行：

```bash
python scripts/youtube_pipeline.py --start-date 2026-02-27T00:00:00Z --channel-id UCxxxx
```

说明：下载与转写依赖是可选加载，未安装时会跳过对应步骤并返回状态。
## Environment

Create a local `.env` from `.env.example` and keep the real file out of git.

See [docs/ENVIRONMENT.md](/C:/Users/Dell/Documents/my_test/trace-demo/docs/ENVIRONMENT.md) for the current variable list.
