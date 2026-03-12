# 变更操作手册（给大模型/开发者）

## 快速定位索引

- 数据模型：`backend/models.py`
- 请求模型：`backend/schemas.py`
- 后端API：`backend/app.py`（按 route 名称搜索）
- 前端请求封装：`frontend/src/services/api.js`
- 前端页面逻辑：`frontend/src/main.js`
- 样式：`frontend/src/styles.css`

## 改动模板

### A. 新增一个接口
1. 在 `schemas.py` 新增 payload
2. 在 `app.py` 新增 route
3. 在 `api.js` 新增函数
4. 在 `main.js` 接入按钮/事件

### B. 调整已有接口返回字段
1. 修改 `app.py` 返回 JSON
2. 修改 `main.js` 中对应渲染
3. 若有筛选字段，更新 `createStore` 的 computed

### C. 新增一个前端业务模块页签
1. `main.js` 的 `moduleTab` 增加 key
2. `module-tabs` 增加按钮
3. `module-body` 增加 `v-if` 区块
4. `styles.css` 按需补样式

## 不建议做法

- 不要在多个文件重复定义同一接口地址。
- 不要把业务逻辑写死在模板里（应放到 action 函数）。
- 不要在新增功能时改动所有模块的状态对象（只扩展必要字段）。
