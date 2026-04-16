# Pending / Recycle UI Refactor Report

## 实际新增/修改了哪些文件

新增：

- `D:\workspace\123\ccc\astrobiology\astro_frontend\src\components\review\PendingReviewToolbar.vue`
- `D:\workspace\123\ccc\astrobiology\astro_frontend\src\components\review\PendingReviewTable.vue`
- `D:\workspace\123\ccc\astrobiology\astro_frontend\src\components\review\RecycleBinToolbar.vue`
- `D:\workspace\123\ccc\astrobiology\astro_frontend\src\components\review\RecycleBinTable.vue`

修改：

- `D:\workspace\123\ccc\astrobiology\astro_frontend\src\views\PendingReview.vue`
- `D:\workspace\123\ccc\astrobiology\astro_frontend\src\views\RecycleBinManagement.vue`

## 从 PendingReview.vue / RecycleBinManagement.vue 拆出了哪些展示层子组件

`PendingReview.vue`：

- `PendingReviewToolbar.vue`
  - 负责刷新、批量通过、批量拒绝、一键通过、一键拒绝、搜索输入、筛选按钮的展示和事件抛出
- `PendingReviewTable.vue`
  - 负责待审核列表表格、全选/单选 UI、排序点击、查看/通过/拒绝按钮的展示和事件抛出

`RecycleBinManagement.vue`：

- `RecycleBinToolbar.vue`
  - 负责刷新、批量恢复、批量删除、返回管理、搜索输入、筛选按钮的展示和事件抛出
- `RecycleBinTable.vue`
  - 负责回收站列表表格、全选/单选 UI、排序点击、查看/恢复/删除按钮的展示和事件抛出

## 哪些展示层成功共用，哪些因语义差异保持独立

本轮没有强行共用工具栏或表格组件，四个组件保持独立。

原因：

- `PendingReview` 有“一键通过 / 一键拒绝”语义，`RecycleBinManagement` 没有。
- `RecycleBinManagement` 有“返回管理 / 恢复 / 永久删除”语义，`PendingReview` 没有。
- 两个表格的操作列、空状态文案、时间字段和行级动作不同。

这次优先保证 props / emits 边界清晰，而不是为了复用把两个页面拉成一个语义混杂的组件。

## 哪些逻辑仍保留在页面内，为什么

仍保留在页面内：

- 列表加载与刷新
- 分页状态与翻页
- 搜索、筛选、排序状态
- 选中状态与批量动作编排
- 详情弹窗状态
- `PDFService` 调用
- 通知 / `alert` / `confirm`

保留原因：

- 这些都是页面级状态流或业务动作编排，不属于纯展示层。
- 本轮目标只是拆工具栏和表格展示层，避免把业务逻辑继续发散到 UI 组件里。

## 为什么这样拆分风险较低

- 页面入口、路由、service 调用方式都没变。
- 新子组件只通过 props / emits 和页面通信，没有引入新的全局状态。
- `PendingReview.vue` 直接切换到新展示组件。
- `RecycleBinManagement.vue` 也已切到新展示组件；旧展示 DOM 仍保留在页内并用 `v-if="false"` 隔离，作为短期回退参考，避免在同一轮里继续大范围删除受历史编码噪音影响的旧模板。
- 为了恢复构建，本轮还顺带修复了这两个目标页面里原本就存在的模板/脚本/CSS 乱码语法问题；没有扩大到其他页面。

## npm run build 的结果

执行目录：

- `D:\workspace\123\ccc\astrobiology\astro_frontend`

结果：

- `npm run build` 通过

本轮构建过程中先后暴露并修复了以下历史问题，均位于这两个目标页面内部：

- 损坏的模板闭合标签
- 损坏的 `placeholder` / 按钮文案标签
- 损坏的 `confirm(...)` 字符串
- 损坏的 CSS `content:` 字符串

最终构建完成，仍有项目既有 warning：

- `baseline-browser-mapping` 过旧提示
- 大 chunk 警告
- `apiClient.js` 动态/静态混合导入提示

这些不是本轮拆分引入的阻塞。

## 静态 smoke 结论

- 上传、后端接口、service 契约未改。
- `PendingReview.vue` 仍把筛选/分页/批量审核逻辑接在原页面内，再通过新 toolbar/table 触发。
- `RecycleBinManagement.vue` 仍把筛选/分页/批量恢复/批量删除逻辑接在原页面内，再通过新 toolbar/table 触发。
- 两个页面都仍接线到现有 composables / `PDFService`。

## 下一步是否适合做一次前端重构阶段总结与收口

适合。

当前状态已经满足做阶段总结的条件：

- `pdfService.js` 已拆成子 service 并保留兼容入口
- `DocumentManagementTab.vue` 已做 composable 下沉
- 审核页面集群的共用逻辑已收敛
- `UnifiedReview.vue` 的弹窗展示层已拆出
- `PendingReview.vue` / `RecycleBinManagement.vue` 的工具栏与表格展示层已拆出
- 前端构建基线当前为绿色

如果继续下一轮代码工作，建议先做“阶段总结与收口”，而不是马上再扩大重构面。

特别注意：

- `RecycleBinManagement.vue` 页内还保留了一份不渲染的旧展示 DOM，后续若要彻底删掉，建议先做一次更窄的清理轮次。
