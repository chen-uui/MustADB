# document_management_tab_refactor_report

## 实际新增/修改了哪些文件

本轮只处理了 `DocumentManagementTab.vue` 及其直接拆分出的 composables：

- 修改 [DocumentManagementTab.vue](D:/workspace/123/ccc/astrobiology/astro_frontend/src/components/workspace/tabs/DocumentManagementTab.vue)
- 新增 [useDocumentList.js](D:/workspace/123/ccc/astrobiology/astro_frontend/src/composables/useDocumentList.js)
- 新增 [useDocumentUpload.js](D:/workspace/123/ccc/astrobiology/astro_frontend/src/composables/useDocumentUpload.js)
- 新增 [useProcessingStatus.js](D:/workspace/123/ccc/astrobiology/astro_frontend/src/composables/useProcessingStatus.js)

本轮未修改：

- 后端任何代码、配置、脚本、数据库、接口
- `pdfService.js` 及其子 service 的对外契约
- `PendingReview.vue`
- `RecycleBinManagement.vue`
- `UnifiedReview.vue`
- `DocumentManagementTab.vue` 的路由入口和页面名称

## 从 DocumentManagementTab.vue 抽出了哪些 composables

### `useDocumentList`

文件：[useDocumentList.js](D:/workspace/123/ccc/astrobiology/astro_frontend/src/composables/useDocumentList.js#L15)

负责：

- 列表加载 `loadDocuments`
- 统计加载 `loadStats`
- 单文档下载 `downloadPDF`
- 单文档删除 `deleteDocument`
- 单文档处理 `processDocument`
- 文件夹同步 `syncFiles`
- 文档标题清洗 `cleanDocumentTitle`

对应主组件接线点：

- [DocumentManagementTab.vue](D:/workspace/123/ccc/astrobiology/astro_frontend/src/components/workspace/tabs/DocumentManagementTab.vue#L372)
- [DocumentManagementTab.vue](D:/workspace/123/ccc/astrobiology/astro_frontend/src/components/workspace/tabs/DocumentManagementTab.vue#L424)
- [DocumentManagementTab.vue](D:/workspace/123/ccc/astrobiology/astro_frontend/src/components/workspace/tabs/DocumentManagementTab.vue#L434)

### `useDocumentUpload`

文件：[useDocumentUpload.js](D:/workspace/123/ccc/astrobiology/astro_frontend/src/composables/useDocumentUpload.js#L3)

负责：

- 文件选择触发 `triggerFileUpload`
- 上传批处理 `handleFileUpload`
- 上传后调用既有 `processPending` 流程
- 上传结果与进度弹窗接线

对应主组件接线点：

- [DocumentManagementTab.vue](D:/workspace/123/ccc/astrobiology/astro_frontend/src/components/workspace/tabs/DocumentManagementTab.vue#L398)
- [DocumentManagementTab.vue](D:/workspace/123/ccc/astrobiology/astro_frontend/src/components/workspace/tabs/DocumentManagementTab.vue#L427)

### `useProcessingStatus`

文件：[useProcessingStatus.js](D:/workspace/123/ccc/astrobiology/astro_frontend/src/composables/useProcessingStatus.js#L3)

负责：

- 批量处理 `processAllDocuments`
- 增量修复 `processStale`
- 全量重处理 `reprocessAllDocuments`
- 处理完成回调 `onProcessingComplete`
- 进度弹窗关闭与清理
- 轮询与定时器清理 `cleanup`

对应主组件接线点：

- [DocumentManagementTab.vue](D:/workspace/123/ccc/astrobiology/astro_frontend/src/components/workspace/tabs/DocumentManagementTab.vue#L386)
- [DocumentManagementTab.vue](D:/workspace/123/ccc/astrobiology/astro_frontend/src/components/workspace/tabs/DocumentManagementTab.vue#L431)
- [DocumentManagementTab.vue](D:/workspace/123/ccc/astrobiology/astro_frontend/src/components/workspace/tabs/DocumentManagementTab.vue#L437)

## 是否拆了 UI 子组件，分别负责什么

没有。

本轮只做了 composables 拆分，没有继续拆 `UploadPanel.vue`、`DocumentToolbar.vue`、`DocumentTable.vue` 或 `ProcessingStatusPanel.vue` 之类的展示组件。这样可以把风险集中在“逻辑下沉”，避免同时引入新的 props/emits 复杂度。

## 哪些逻辑因风险原因暂时没有拆

以下逻辑仍保留在 [DocumentManagementTab.vue](D:/workspace/123/ccc/astrobiology/astro_frontend/src/components/workspace/tabs/DocumentManagementTab.vue) 主组件内：

- 搜索 debounce 与本地过滤缓存
- 预览弹窗状态 `previewPDFId` / `showPreviewModal`
- `onMounted` 初始化加载、自动同步触发、统计刷新定时器
- 全局错误监听器注册与注销
- `selectDocument` 事件桥接

保留原因：

- 这些逻辑直接依赖当前页面入口和父层事件语义
- 它们与服务层契约耦合较弱，但和页面生命周期耦合较强
- 先抽异步动作和轮询逻辑，收益更高、回归风险更低

## 为什么这样拆分可以降低复杂度

本轮的复杂度下降主要体现在三点：

1. `DocumentManagementTab.vue` 不再直接承载上传、列表操作、批量处理三大块异步流程的实现细节，而是变成“页面入口 + 接线层”。
2. 轮询、进度条更新、上传后处理、删除/同步/单文档处理等副作用逻辑有了明确边界，不再全部混在一个 setup 中。
3. 后续若继续拆 UI 子组件，可以直接复用这些 composables，而不需要先从 1000+ 行页面里二次抽逻辑。

## 静态 smoke 结论

上传相关逻辑仍接线：

- [DocumentManagementTab.vue](D:/workspace/123/ccc/astrobiology/astro_frontend/src/components/workspace/tabs/DocumentManagementTab.vue#L398) 初始化 `useDocumentUpload`
- [DocumentManagementTab.vue](D:/workspace/123/ccc/astrobiology/astro_frontend/src/components/workspace/tabs/DocumentManagementTab.vue#L427) 保留 `triggerFileUpload`
- [DocumentManagementTab.vue](D:/workspace/123/ccc/astrobiology/astro_frontend/src/components/workspace/tabs/DocumentManagementTab.vue#L428) 保留 `handleFileUpload`

列表加载逻辑仍接线：

- [DocumentManagementTab.vue](D:/workspace/123/ccc/astrobiology/astro_frontend/src/components/workspace/tabs/DocumentManagementTab.vue#L372) 初始化 `useDocumentList`
- [DocumentManagementTab.vue](D:/workspace/123/ccc/astrobiology/astro_frontend/src/components/workspace/tabs/DocumentManagementTab.vue#L424) 保留 `loadDocuments`
- [DocumentManagementTab.vue](D:/workspace/123/ccc/astrobiology/astro_frontend/src/components/workspace/tabs/DocumentManagementTab.vue#L425) 保留 `loadStats`
- [DocumentManagementTab.vue](D:/workspace/123/ccc/astrobiology/astro_frontend/src/components/workspace/tabs/DocumentManagementTab.vue#L434) 保留 `syncFiles`

处理状态轮询逻辑仍接线：

- [DocumentManagementTab.vue](D:/workspace/123/ccc/astrobiology/astro_frontend/src/components/workspace/tabs/DocumentManagementTab.vue#L386) 初始化 `useProcessingStatus`
- [DocumentManagementTab.vue](D:/workspace/123/ccc/astrobiology/astro_frontend/src/components/workspace/tabs/DocumentManagementTab.vue#L431) 保留 `processAllDocuments`
- [DocumentManagementTab.vue](D:/workspace/123/ccc/astrobiology/astro_frontend/src/components/workspace/tabs/DocumentManagementTab.vue#L432) 保留 `processStale`
- [DocumentManagementTab.vue](D:/workspace/123/ccc/astrobiology/astro_frontend/src/components/workspace/tabs/DocumentManagementTab.vue#L433) 保留 `reprocessAllDocuments`
- [DocumentManagementTab.vue](D:/workspace/123/ccc/astrobiology/astro_frontend/src/components/workspace/tabs/DocumentManagementTab.vue#L437) 保留 `onProcessingComplete`

## npm run build 的结果

结果：通过。

执行的轻量验证：

- `npm run build`

结果说明：

- Vite 构建成功
- `DocumentManagementTab` 新构建产物已生成
- 没有暴露新的构建阻塞

仍然存在的只是非阻塞 warning：

- `apiClient.js` 同时被动态和静态导入
- 部分 chunk 体积超过 500 kB

这些 warning 与本轮 `DocumentManagementTab.vue` composable 拆分无直接冲突。

## 下一步是否适合继续处理审核页面集群

适合。

当前前端已经具备继续做 `PendingReview.vue`、`RecycleBinManagement.vue`、`UnifiedReview.vue` 集群收敛的前提，原因是：

- 服务层已经先行拆分
- 构建基线已恢复
- `DocumentManagementTab.vue` 的高噪声异步逻辑已先被抽到 composables

更稳妥的下一步顺序仍然建议是：

1. 先抽审核页面共用 composable，例如列表加载、批量操作、选中状态与搜索条件
2. 再考虑表格/工具栏类展示组件的复用
3. 继续保持 API 契约不变，不与后端改动混做
