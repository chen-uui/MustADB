# Unified Review UI Refactor Report

## 实际新增/修改了哪些文件

新增：

- `D:\workspace\123\ccc\astrobiology\astro_frontend\src\components\review\ReviewRejectDialog.vue`
- `D:\workspace\123\ccc\astrobiology\astro_frontend\src\components\review\ReviewDetailDialog.vue`

修改：

- `D:\workspace\123\ccc\astrobiology\astro_frontend\src\views\UnifiedReview.vue`

本轮没有修改后端代码、API URL、HTTP method、payload 结构或 service 对外契约。

## 从 UnifiedReview.vue 拆出了哪些展示层子组件

### `ReviewRejectDialog.vue`

职责：

- 展示拒绝确认弹窗
- 展示单条/批量拒绝提示文案
- 展示拒绝原因输入框
- 通过 props 接收 `visible / item / reason`
- 通过 emits 输出 `close / confirm / update:reason`

保留边界：

- 不直接调用接口
- 不负责通知
- 不负责批量拒绝编排

### `ReviewDetailDialog.vue`

职责：

- 展示 PDF / meteorite 详情弹窗
- 展示 approve / reject / close 按钮
- 通过 props 接收 `visible / item`
- 通过 emits 输出 `close / approve / reject`

保留边界：

- 不直接调用 approve / reject 接口
- 不负责页面级状态
- 不负责数据加载和映射

## 哪些逻辑仍保留在页面内，为什么

仍保留在 `UnifiedReview.vue`：

- `loadData` 和 PDF / meteorite 混合数据映射
- `approveItem / rejectItem / confirmReject`
- 批量 approve / batch reject 编排
- 通知呈现 `showNotification`
- 选择状态和批处理接线
- 弹窗显示状态 `showRejectDialog / showDetailDialog`
- 当前项状态 `currentRejectItem / selectedItem / rejectReason`

保留原因：

- 这些都不是纯展示层，而是页面级业务编排或状态流。
- 本轮目标只是把 DOM、按钮、输入框和展示字段抽出去，避免把 UI 拆分扩大成逻辑重构。

## 为什么这样拆分风险较低

- 新组件只通过 props / emits 与页面通信，没有直接接触接口层。
- `UnifiedReview.vue` 仍然保留所有业务动作、通知和状态流，页面语义没有被分散到多个组件里。
- 弹窗的关闭、确认、输入更新仍由页面统一控制，回归面主要集中在模板接线而不是业务逻辑。
- 这次顺手修掉了 `UnifiedReview.vue` 内原有的几处注释/字符串粘连语法噪音，但没有改变接口调用方式。

## props / emits 接线核验

`ReviewRejectDialog.vue`：

- props: `visible`, `item`, `reason`
- emits: `close`, `confirm`, `update:reason`
- 页面接线：`showRejectDialog`, `currentRejectItem`, `rejectReason`, `closeRejectDialog`, `confirmReject`

`ReviewDetailDialog.vue`：

- props: `visible`, `item`
- emits: `close`, `approve`, `reject`
- 页面接线：`showDetailDialog`, `selectedItem`, `closeDetailDialog`, `approveItem(selectedItem)`, `rejectItem(selectedItem)`

## npm run build 的结果

执行命令：

```bash
npm run build
```

结果：

- 构建成功
- `vite build` 完成，`1648 modules transformed`

本轮过程中暴露并修复了两个同文件内的历史语法问题：

- `loadData` 中注释与 `pdfs.value = ...` 粘连
- `batchReject / confirmReject / handleSearch` 一带的注释与代码粘连

这些问题都位于 `UnifiedReview.vue` 本身，不是新子组件的 props / emits 接线问题。

仍存在的非阻塞 warning：

- `apiClient.js` 动态/静态混合导入提示
- chunk size 超过 500 kB 提示
- `baseline-browser-mapping` 数据过旧提示

这些都不是本轮引入的新阻塞。

## 下一步是否适合再拆 PendingReview.vue / RecycleBinManagement.vue 的工具栏与表格展示层

适合。

建议顺序：

1. 先拆 `PendingReview.vue` / `RecycleBinManagement.vue` 的工具栏展示层。
2. 再拆列表表头和表格展示层。
3. 仍然不要在下一轮就尝试把多个审核页合成一个超级组件。

原因：

- 这轮已经验证“页面保留状态流，子组件只做展示”的模式可行。
- 下一轮沿用同样边界去拆工具栏和表格，风险会比较低。
