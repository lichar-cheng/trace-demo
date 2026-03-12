<!-- Last Edited: 2026-03-12 -->
# 全量代码交付清单

本文件用于你“删空 GitHub 后重新上传”的场景，确保你拿到的是完整可运行的一套。

## 必要文件

### 后端
- `backend/app.py`
- `backend/models.py`
- `backend/schemas.py`
- `backend/requirements.txt`

### 前端
- `frontend/index.html`
- `frontend/src/main.js`
- `frontend/src/services/api.js`
- `frontend/src/styles.css`

### 文档
- `README.md`
- `docs/ARCHITECTURE.md`
- `docs/CHANGE_PLAYBOOK.md`
- `docs/WORK_PR_HANDOFF.md`
- `docs/FULL_DELIVERY.md`

### 脚本
- `scripts/bootstrap.sh`
- `scripts/run_backend.sh`
- `scripts/run_frontend.sh`
- `scripts/verify_repo.sh`

## 新仓库导入建议

1. 复制全部文件到新仓库根目录
2. 提交一次初始提交
3. 运行 `bash scripts/verify_repo.sh` 确认关键文件存在
4. 执行启动脚本

## 版本确认

执行：

```bash
git log --oneline -n 5
```

确认包含本次“full-delivery”提交。
