# pdf_service_refactor_report

## 实际新增/修改了哪些文件

本轮只修改了前端 service 层文件：

- 新增 [documentService.js](D:/workspace/123/ccc/astrobiology/astro_frontend/src/services/documentService.js)
- 新增 [reviewService.js](D:/workspace/123/ccc/astrobiology/astro_frontend/src/services/reviewService.js)
- 新增 [qaService.js](D:/workspace/123/ccc/astrobiology/astro_frontend/src/services/qaService.js)
- 新增 [directProcessingService.js](D:/workspace/123/ccc/astrobiology/astro_frontend/src/services/directProcessingService.js)
- 修改 [pdfService.js](D:/workspace/123/ccc/astrobiology/astro_frontend/src/services/pdfService.js)

本轮未修改：

- 后端任何代码、配置、脚本、接口
- 任何页面组件
- 任何 API URL、HTTP method、payload 结构、调用方返回值用法

## pdfService.js 原有职责是如何拆分的

原始 `pdfService.js` 同时承担了文档管理、审核、问答、提取/直接处理、系统健康检查等多类职责。现在按领域拆为 4 个子服务：

- `documentService`
  - 负责文档上传、下载、删除、列表、统计、同步、处理状态
- `reviewService`
  - 负责审核看板、陨石审核、回收站、批量审核、搜索结果标准化
- `qaService`
  - 负责问答、流式问答、系统健康检查
- `directProcessingService`
  - 负责提取任务、单任务提取、批量提取、预览搜索、任务清理、直接处理相关接口

`pdfService.js` 现在只保留为“薄兼容层”，把原有方法名原样转发到对应子服务，避免页面侧同步改造。

## 哪些方法被转移到了哪个新服务

### documentService

迁入的方法：

- `uploadPDF`
- `listPDFs`
- `searchPDFs`
- `downloadPDF`
- `deletePDF`
- `processPDF`
- `getDocumentChunks`
- `getDocuments`
- `getStats`
- `getDownloadUrl`
- `syncFiles`
- `uploadDocument`
- `processPending`
- `processStale`
- `getProcessingStatus`
- `reprocessAll`
- `cancelProcessing`

对应实现入口见 [documentService.js](D:/workspace/123/ccc/astrobiology/astro_frontend/src/services/documentService.js#L4)。

### reviewService

迁入的方法：

- `reviewDocument`
- `getMeteoriteData`
- `getReviewDashboard`
- `getApprovedMeteorites`
- `getPendingMeteorites`
- `getRejectedMeteorites`
- `getMeteoriteOptions`
- `approveMeteorite`
- `rejectMeteorite`
- `batchApproveMeteorite`
- `batchRejectMeteorite`
- `approveAllMeteorite`
- `rejectAllMeteorite`
- `restoreMeteorite`
- `permanentDeleteMeteorite`
- `getApprovedMeteoriteDetail`
- `deleteApprovedMeteorite`
- `updateMeteorite`
- `searchMeteorites`

对应实现入口见 [reviewService.js](D:/workspace/123/ccc/astrobiology/astro_frontend/src/services/reviewService.js#L4)。

### qaService

迁入的方法：

- `askQuestion`
- `askQuestionStream`
- `getSystemHealth`

对应实现入口见 [qaService.js](D:/workspace/123/ccc/astrobiology/astro_frontend/src/services/qaService.js#L6)。

### directProcessingService

迁入的方法：

- `extractContent`
- `stopTask`
- `confirmSave`
- `resumeTask`
- `pauseTask`
- `startBatchExtraction`
- `getExtractionProgress`
- `resetBatchExtractionState`
- `searchMeteoriteSegments`
- `singleTaskSearch`
- `singleTaskEnqueue`
- `singleTaskStatus`
- `singleTaskCancel`
- `singleTaskSegments`
- `extractFromSelectedSegments`
- `getExtractionTasksList`
- `getExtractionTasks`
- `startExtraction`
- `getTaskDetails`
- `deleteTask`
- `previewSearch`
- `startFromDB`
- `cleanupStaleTasks`
- `forceCleanupAllRunningTasks`
- `getRunningTasksStatus`

对应实现入口见 [directProcessingService.js](D:/workspace/123/ccc/astrobiology/astro_frontend/src/services/directProcessingService.js#L4)。

## 哪些兼容层仍然保留在 pdfService.js

[pdfService.js](D:/workspace/123/ccc/astrobiology/astro_frontend/src/services/pdfService.js#L1) 仍然保留以下兼容职责：

- 继续导出默认实例和命名导出 `PDFService`
- 保留全部原有方法名
- 维持旧调用方式：`PDFService.someMethod(...)`
- 不要求页面改 import 或改调用签名

兼容层本身不再实现业务请求，只做显式转发，例如：

- `uploadPDF` 转发到 `documentService`
- `askQuestion` 转发到 `qaService`
- `getReviewDashboard` 转发到 `reviewService`
- `startExtraction` 转发到 `directProcessingService`
- `cancelProcessing` 转发到 `documentService`

## 是否有任何方法因为风险原因暂时未拆

没有把原有方法继续留在 `pdfService.js` 内部直接实现；方法职责已经全部拆到子服务。

但有几类“高风险历史行为”被刻意原样保留，没有顺手修：

- `askQuestionStream` 仍使用 `fetch`
  - 原因：它需要保留当前的流式响应语义和 `ReadableStream` 返回方式，直接改成统一 axios 流程会改变使用方式和错误边界。
- `downloadPDF`、`deletePDF`、`processPDF` 的历史 endpoint 拼接方式被保留
  - 原因：本轮目标是拆分，不是修正 URL 语义；避免在“重构”名义下混入行为修改。
- `getMeteoriteData` 对 `API_CONFIG.ENDPOINTS.METEORITE_DATA` 的依赖被保留
  - 原因：该方法当前调用面不清晰，贸然修正会变成功能性改动。

这三类都适合在单独的“服务层行为修复”轮次里处理，而不是混在本轮兼容拆分中。

## 轻量验证结果

已完成的验证：

- 兼容层方法清单静态检查通过
  - [pdfService.js](D:/workspace/123/ccc/astrobiology/astro_frontend/src/services/pdfService.js#L7) 到 [pdfService.js](D:/workspace/123/ccc/astrobiology/astro_frontend/src/services/pdfService.js#L70) 仍暴露原有方法名。
- 子服务导入导出结构已检查
  - `documentService`、`reviewService`、`qaService`、`directProcessingService` 都提供默认实例导出，并被 `pdfService.js` 正常引用。
- 进行了前端构建级 smoke check
  - 命令：`npm run build`
  - 结果：构建流程进入 Vite transform 阶段并完成 `373 modules transformed`，说明本轮服务文件的语法与导入链没有立即报错。
  - 最终失败原因与本轮无关：`src/views/MeteoriteSearch.vue` 依赖的 `src/components/workspace/tabs/MeteoriteSearchTabNew.vue` 缺失，导致 Vite 在后续加载阶段中断。

结论：

- 本轮拆分本身通过了静态导入级检查。
- 当前无法把 `npm run build` 记为“完全通过”，但阻塞项不是本轮 service 拆分引入的。

## 下一步是否适合继续拆 DocumentManagementTab.vue

适合，但建议分两步做，不要直接大拆：

1. 先只抽 `useDocumentList`、`useUploads`、`useProcessingPoller` 这类 composable。
2. 等前端构建缺失文件问题先处理掉，再拆表格、工具栏、统计卡片和进度弹窗组件。

原因：

- 本轮已把 service 层边界收清，`DocumentManagementTab.vue` 下一步再拆状态与 UI 会更安全。
- 但当前前端工程还存在与本轮无关的构建阻塞项，先补齐构建基线，再做页面层重构更稳。
