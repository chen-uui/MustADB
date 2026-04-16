# Review Pages Refactor Report

## 实际新增/修改了哪些文件

新增：

- `D:\workspace\123\ccc\astrobiology\astro_frontend\src\composables\useReviewFilters.js`
- `D:\workspace\123\ccc\astrobiology\astro_frontend\src\composables\useReviewSelection.js`
- `D:\workspace\123\ccc\astrobiology\astro_frontend\src\composables\useReviewActions.js`

修改：

- `D:\workspace\123\ccc\astrobiology\astro_frontend\src\views\PendingReview.vue`
- `D:\workspace\123\ccc\astrobiology\astro_frontend\src\views\RecycleBinManagement.vue`
- `D:\workspace\123\ccc\astrobiology\astro_frontend\src\views\UnifiedReview.vue`

本轮没有拆 UI 子组件，也没有改后端接口、service 对外契约、页面入口或路由。

## 从三个审核页面抽出了哪些共用 composables

### `useReviewFilters.js`

负责：

- 搜索关键字
- 分页状态
- 排序字段与排序方向
- 筛选条件对象
- 可见页码计算
- `handleSearch / sortBy / applyFilters / clearFilters / goToPage`

当前接入：

- `PendingReview.vue`
- `RecycleBinManagement.vue`

### `useReviewSelection.js`

负责：

- 选中项集合
- 全选状态计算
- 全选/取消全选
- 清空选择

当前接入：

- `PendingReview.vue`
- `RecycleBinManagement.vue`
- `UnifiedReview.vue`

### `useReviewActions.js`

负责：

- 批量动作的统一编排
- 批处理完成后的清空选择
- 成功后的统一 `afterSuccess` 回调

当前接入：

- `PendingReview.vue`
- `RecycleBinManagement.vue`
- `UnifiedReview.vue`

## 哪些逻辑成功合并

- `PendingReview.vue` 与 `RecycleBinManagement.vue` 的分页、排序、筛选、搜索重置逻辑已统一到 `useReviewFilters.js`。
- 三个页面的“选中项 + 全选”逻辑已统一到 `useReviewSelection.js`。
- 三个页面的批量动作执行模板已统一到 `useReviewActions.js`，不再在页面里重复写 `Promise.all + 清空选择 + 刷新` 的框架代码。
- `UnifiedReview.vue` 现在也通过共用 selection/action composable 处理批量 approve / batch reject 的骨架逻辑，但其混合数据加载仍保留在页面内。

## 哪些逻辑因语义差异暂时保留在各自页面

- `PendingReview.vue` 的单条通过/拒绝、一键通过/一键拒绝仍保留在页面内，因为它们直接绑定当前待审业务语义和提示文案。
- `RecycleBinManagement.vue` 的单条恢复、永久删除、导航回管理页仍保留在页面内，因为它们属于回收站特有动作。
- `UnifiedReview.vue` 的 `loadData`、PDF/meteorite 混合映射、拒绝弹窗状态、详情弹窗状态、通知呈现仍保留在页面内，因为这里混合了两类对象和额外 UI 状态，不适合这轮继续下沉。
- 本轮没有统一三个页面的提示文案、通知样式或详情弹窗结构，避免把“共用逻辑收敛”扩大成 UI 重构。

## 为什么这样拆分能降低复杂度

- 页面主体现在更偏向“把状态和动作接起来”，而不是自己维护整套分页、筛选、全选和批处理细节。
- `PendingReview.vue` 与 `RecycleBinManagement.vue` 去掉了大量同构状态与方法，后续修分页/排序/全选 bug 时不需要在两处同步改。
- `UnifiedReview.vue` 虽然仍然较重，但至少把选择与批量动作骨架抽离了，后续继续拆详情/拒绝工作流时边界更清晰。
- 本轮没有强行合并对象语义不同的动作，避免“为了复用而复用”引入回归。

## npm run build 的结果

执行命令：

```bash
npm run build
```

结果：

- 构建成功
- `vite build` 完成，`1644 modules transformed`
- 没有出现本轮新增的构建阻塞

仍存在的非阻塞 warning：

- `apiClient.js` 同时被动态和静态导入的 chunk 提示
- 主 bundle 体积超过 500 kB 的 chunk size 提示
- `baseline-browser-mapping` 数据过旧提示

这些 warning 不是本轮引入的回归。

## 静态 smoke 结论

- `PendingReview.vue` 仍然直接调用 `PDFService.getPendingMeteorites / getMeteoriteOptions / approveMeteorite / rejectMeteorite / approveAllMeteorite / rejectAllMeteorite`。
- `RecycleBinManagement.vue` 仍然直接调用 `PDFService.getRejectedMeteorites / getMeteoriteOptions / restoreMeteorite / permanentDeleteMeteorite`。
- `UnifiedReview.vue` 仍然直接调用现有 `/api/pdf/review/pending/`、`/approve/`、`/reject/` 接口，URL、HTTP method 和 payload 结构未改。
- 三个页面的全选、批量操作、搜索/筛选/分页接线都仍然存在。

## 下一步是否适合再拆 UI 子组件

适合，但建议只做展示层拆分，不要马上改状态流。

优先顺序建议：

1. 先拆 `UnifiedReview.vue` 的拒绝弹窗与详情弹窗展示层。
2. 再拆 `PendingReview.vue` / `RecycleBinManagement.vue` 的工具栏与表格展示层。
3. 暂时不要把三个页面合成一个“超级审核组件”。

这一步已经把状态和动作边界拉出来了，下一轮如果继续拆 UI 子组件，风险会明显低于直接从当前大页面里硬拆。
