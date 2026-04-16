# Frontend Refactor Phase 1 Summary

## 一、本阶段完成了什么

### 1. service 层拆分

- `D:\workspace\123\ccc\astrobiology\astro_frontend\src\services\pdfService.js`
  - 已从“大而全”服务收敛为薄兼容层，继续保留原有 `PDFService` 方法入口。
- 新增并承接职责的子 service：
  - `D:\workspace\123\ccc\astrobiology\astro_frontend\src\services\documentService.js`
  - `D:\workspace\123\ccc\astrobiology\astro_frontend\src\services\reviewService.js`
  - `D:\workspace\123\ccc\astrobiology\astro_frontend\src\services\qaService.js`
  - `D:\workspace\123\ccc\astrobiology\astro_frontend\src\services\directProcessingService.js`

### 2. DocumentManagementTab 的 composable 下沉

- `D:\workspace\123\ccc\astrobiology\astro_frontend\src\components\workspace\tabs\DocumentManagementTab.vue`
  - 已把文档列表、上传编排、处理进度轮询三类逻辑下沉到 composable。
- 新增：
  - `D:\workspace\123\ccc\astrobiology\astro_frontend\src\composables\useDocumentList.js`
  - `D:\workspace\123\ccc\astrobiology\astro_frontend\src\composables\useDocumentUpload.js`
  - `D:\workspace\123\ccc\astrobiology\astro_frontend\src\composables\useProcessingStatus.js`

### 3. 审核页面共用逻辑收敛

- 新增：
  - `D:\workspace\123\ccc\astrobiology\astro_frontend\src\composables\useReviewFilters.js`
  - `D:\workspace\123\ccc\astrobiology\astro_frontend\src\composables\useReviewSelection.js`
  - `D:\workspace\123\ccc\astrobiology\astro_frontend\src\composables\useReviewActions.js`
- 这些 composable 已被以下页面接入：
  - `D:\workspace\123\ccc\astrobiology\astro_frontend\src\views\PendingReview.vue`
  - `D:\workspace\123\ccc\astrobiology\astro_frontend\src\views\RecycleBinManagement.vue`
  - `D:\workspace\123\ccc\astrobiology\astro_frontend\src\views\UnifiedReview.vue`

### 4. 展示层子组件拆分

- `UnifiedReview.vue`
  - 已拆出：
    - `D:\workspace\123\ccc\astrobiology\astro_frontend\src\components\review\ReviewRejectDialog.vue`
    - `D:\workspace\123\ccc\astrobiology\astro_frontend\src\components\review\ReviewDetailDialog.vue`
- `PendingReview.vue`
  - 已拆出：
    - `D:\workspace\123\ccc\astrobiology\astro_frontend\src\components\review\PendingReviewToolbar.vue`
    - `D:\workspace\123\ccc\astrobiology\astro_frontend\src\components\review\PendingReviewTable.vue`
- `RecycleBinManagement.vue`
  - 已拆出：
    - `D:\workspace\123\ccc\astrobiology\astro_frontend\src\components\review\RecycleBinToolbar.vue`
    - `D:\workspace\123\ccc\astrobiology\astro_frontend\src\components\review\RecycleBinTable.vue`

### 5. 构建基线恢复

- `MeteoriteSearchTabNew.vue` 缺失导致的构建阻塞已在前序轮次修复。
- 最近一轮前端构建结果为绿色：
  - `npm run build` 已通过
- 本阶段同时顺带暴露并修复了目标页面中的历史模板/脚本/CSS 乱码语法问题，使当前基线可继续维护。

## 二、当前代码结构相比之前改善了什么

- `pdfService.js` 不再承担所有前端 PDF/审核/问答/直接处理职责，入口保留但内部职责已清晰分区。
- `DocumentManagementTab.vue` 不再把“列表加载 + 上传编排 + 处理轮询”全部堆在主组件内，页面主体复杂度下降。
- 审核页集群不再各自重复维护筛选、选择、批量动作骨架，共用逻辑已经下沉到 review composables。
- `UnifiedReview.vue`、`PendingReview.vue`、`RecycleBinManagement.vue` 的展示层和页面级状态流边界更清楚。
- 新增的 review 展示组件都采用 props / emits 边界，没有把 service 调用再次塞回子组件。

## 三、仍残留的兼容层 / 旧代码 / 旧 DOM

### 1. `pdfService.js` 薄兼容层

- 路径：
  - `D:\workspace\123\ccc\astrobiology\astro_frontend\src\services\pdfService.js`
- 当前状态：
  - 仍保留全部原有入口方法，内部转发到子 service。
- 判断：
  - 这是刻意保留的兼容层，不是坏味道本身。
- 分级：
  - 暂时建议保留

### 2. 子 service 内的历史别名 / 双命名方法

- 典型例子：
  - `documentService.js` 中 `uploadPDF` / `uploadDocument`
  - `documentService.js` 中 `listPDFs` / `getDocuments`
  - `directProcessingService.js` 中 `getExtractionTasksList` / `getExtractionTasks`
  - `directProcessingService.js` 中 `startExtraction` / `startFromDB`
- 判断：
  - 这些更像兼容历史调用面留下的双入口。
- 分级：
  - 需要下一轮窄范围清理

### 3. `RecycleBinManagement.vue` 内未渲染的旧展示 DOM

- 路径：
  - `D:\workspace\123\ccc\astrobiology\astro_frontend\src\views\RecycleBinManagement.vue`
- 现状：
  - 新的 `RecycleBinToolbar` / `RecycleBinTable` 已在页面顶部作为当前实际渲染入口。
  - 旧工具栏和旧表格 DOM 仍保留在页内，并以 `v-if="false"` 隔离。
- 判断：
  - 这是本阶段最明确的临时残留物。
- 分级：
  - 可立即单独清理

### 4. 页面级状态逻辑仍较重

- 路径：
  - `D:\workspace\123\ccc\astrobiology\astro_frontend\src\views\PendingReview.vue`
  - `D:\workspace\123\ccc\astrobiology\astro_frontend\src\views\RecycleBinManagement.vue`
  - `D:\workspace\123\ccc\astrobiology\astro_frontend\src\views\UnifiedReview.vue`
  - `D:\workspace\123\ccc\astrobiology\astro_frontend\src\components\workspace\tabs\DocumentManagementTab.vue`
- 现状：
  - 列表加载、分页、通知、确认弹窗、批量动作编排仍在页面内。
- 判断：
  - 这是当前阶段“故意留在页面里”的部分，不是遗漏。
- 分级：
  - 暂时建议保留

### 5. 历史编码噪音 / 文案噪音

- 典型位置：
  - `useDocumentList.js`
  - `useDocumentUpload.js`
  - `useProcessingStatus.js`
  - `PendingReviewToolbar.vue`
  - `RecycleBinTable.vue`
  - `PendingReview.vue`
  - `RecycleBinManagement.vue`
- 表现：
  - 控制台日志、确认文案、注释、局部 UI 文案中仍有乱码或旧命名。
- 判断：
  - 不影响当前构建和主要行为，但影响可维护性和阅读质量。
- 分级：
  - 需要下一轮窄范围清理

## 四、哪些对象适合下一轮窄范围清理

### 可立即单独清理

- `D:\workspace\123\ccc\astrobiology\astro_frontend\src\views\RecycleBinManagement.vue`
  - 删除 `v-if="false"` 隔离的旧工具栏 DOM
  - 删除 `v-if="false"` 隔离的旧表格 DOM

### 需要下一轮窄范围清理

- `D:\workspace\123\ccc\astrobiology\astro_frontend\src\services\documentService.js`
  - 评估双命名入口是否都仍必要
- `D:\workspace\123\ccc\astrobiology\astro_frontend\src\services\directProcessingService.js`
  - 评估重复别名方法是否都仍必要
- `D:\workspace\123\ccc\astrobiology\astro_frontend\src\components\review\PendingReviewToolbar.vue`
- `D:\workspace\123\ccc\astrobiology\astro_frontend\src\components\review\RecycleBinTable.vue`
- `D:\workspace\123\ccc\astrobiology\astro_frontend\src\composables\useDocumentList.js`
- `D:\workspace\123\ccc\astrobiology\astro_frontend\src\composables\useDocumentUpload.js`
- `D:\workspace\123\ccc\astrobiology\astro_frontend\src\composables\useProcessingStatus.js`
  - 以上对象适合做“只清理命名 / 文案 / 注释 / 重复别名”的窄范围整理

### 关于 RecycleBinManagement.vue 旧 DOM 的专项判断

1. 是否已经完全不再被使用：
   - 是。当前实际渲染的是 `RecycleBinToolbar` 和 `RecycleBinTable`，旧 DOM 只作为不渲染的保留块存在。
2. 是否可以在下一轮单独删除：
   - 可以，而且很适合作为单独一轮极小清理。
3. 删除它需要什么最小验证：
   - 只改这一文件
   - 重新执行 `npm run build`
   - 手工核验 4 个点：
     - 页面能正常展示工具栏和表格
     - 搜索 / 筛选面板仍能工作
     - 选择 / 批量恢复 / 批量删除仍能触发
     - 行级查看 / 恢复 / 删除按钮仍能触发

## 五、哪些对象暂时不要动

- `D:\workspace\123\ccc\astrobiology\astro_frontend\src\views\UnifiedReview.vue`
  - 当前仍承担混合数据加载、批量动作、标签切换与页面级状态流，不适合继续在收口阶段深挖。
- `D:\workspace\123\ccc\astrobiology\astro_frontend\src\components\workspace\tabs\DocumentManagementTab.vue`
  - 已经做过一轮 composable 下沉，但上传/进度/同步链路仍比较重，当前更适合先稳定。
- `D:\workspace\123\ccc\astrobiology\astro_frontend\src\services\pdfService.js`
  - 当前兼容层价值仍大，不建议在收口前移除。
- 所有 review / document composables 对外契约
  - 现阶段已经接入多页，不建议继续改签名。

## 六、建议的下一阶段顺序

1. 单独做一轮极小清理：
   - 只删除 `RecycleBinManagement.vue` 中已不渲染的旧 DOM
   - 保持 service / composable / 业务逻辑不动
2. 如果还想继续收口，再做一轮“文本与命名噪音清理”：
   - 只处理 review 组件和 document composables 中的乱码日志、旧注释、局部文案
3. 到这一步后提交本阶段
4. 下一阶段若继续重构，应重新开题，不建议在当前链路里继续扩大页面拆分范围

## 明确结论

**结论 B：现在适合先做一轮很小的清理，再提交**

理由：

- 结构性重构目标已经基本达成
- 构建基线已经恢复
- 当前最主要的残留物非常集中：`RecycleBinManagement.vue` 中未渲染旧 DOM
- 这类残留适合用一轮极小清理收口，再提交会更干净
