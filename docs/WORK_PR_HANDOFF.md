<!-- Last Edited: 2026-03-12 -->
# Work 分支 PR 交接说明

你当前需要的是：把本地 `work` 的改动提交成 PR，目标合并到 GitHub 仓库。

## 1) 本地分支确认

```bash
git checkout work
git branch --show-current
```

确保输出是 `work`。

## 2) 推送 work 分支到 GitHub（首次）

```bash
git push -u origin work
```

如果远端还没有 `work`，这条命令会在 GitHub 自动创建 `work` 分支。

## 3) 在 GitHub 创建 PR

- Base branch: `main`（或你指定的主分支）
- Compare branch: `work`
- 点击 `Create pull request`

## 4) 命令行直接开 PR（可选）

如果你本地安装了 GitHub CLI：

```bash
gh pr create --base main --head work --title "merge work into main" --body "同步 work 分支功能变更"
```

## 5) 合并后同步

```bash
git checkout main
git pull
git checkout work
git merge main
```

这样 `work` 会和已合并后的 `main` 保持一致，减少下次冲突。
