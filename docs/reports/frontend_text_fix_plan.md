# frontend_text_fix_plan

本计划基于 [frontend_text_encoding_audit_report.md](D:/workspace/123/docs/reports/frontend_text_encoding_audit_report.md) 和 [frontend_text_confirmation_sheet.md](D:/workspace/123/docs/reports/frontend_text_confirmation_sheet.md) 整理，只定义修复批次，不做任何代码修改。

## 第一批：可直接修复的低风险项

范围：

- 关闭符号
- 空状态图标
- 伪元素图标
- 纯 `console` 调试字符串
- 纯分隔符

建议处理对象：

- [PendingReview.vue](D:/workspace/123/ccc/astrobiology/astro_frontend/src/views/PendingReview.vue)
- [RecycleBinManagement.vue](D:/workspace/123/ccc/astrobiology/astro_frontend/src/views/RecycleBinManagement.vue)
- [UnifiedReview.vue](D:/workspace/123/ccc/astrobiology/astro_frontend/src/views/UnifiedReview.vue)
- [PendingReviewToolbar.vue](D:/workspace/123/ccc/astrobiology/astro_frontend/src/components/review/PendingReviewToolbar.vue)
- [RecycleBinToolbar.vue](D:/workspace/123/ccc/astrobiology/astro_frontend/src/components/review/RecycleBinToolbar.vue)
- [PendingReviewTable.vue](D:/workspace/123/ccc/astrobiology/astro_frontend/src/components/review/PendingReviewTable.vue)
- [RecycleBinTable.vue](D:/workspace/123/ccc/astrobiology/astro_frontend/src/components/review/RecycleBinTable.vue)
- [useDocumentList.js](D:/workspace/123/ccc/astrobiology/astro_frontend/src/composables/useDocumentList.js)
- [useDocumentUpload.js](D:/workspace/123/ccc/astrobiology/astro_frontend/src/composables/useDocumentUpload.js)
- [useProcessingStatus.js](D:/workspace/123/ccc/astrobiology/astro_frontend/src/composables/useProcessingStatus.js)
- [DocumentManagementTab.vue](D:/workspace/123/ccc/astrobiology/astro_frontend/src/components/workspace/tabs/DocumentManagementTab.vue)

建议规则：

- 只改纯装饰或纯调试文本。
- 不改任何按钮业务含义。
- 不改任何 `alert / confirm / prompt`。
- 不改任何 payload 内的 `message / notes / reviewer_notes / rejection_reason / current_file`。

验证重点：

- 前端构建通过。
- 相关页面仍能正常打开。
- 工具栏和表格按钮不受影响。

## 第二批：确认后可修复的页面级业务文案

范围：

- 页面标题
- 按钮文案
- 空状态文案
- 分页文案
- 工具栏文案
- 详情弹窗文案

建议优先顺序：

1. [PendingReview.vue](D:/workspace/123/ccc/astrobiology/astro_frontend/src/views/PendingReview.vue) + [PendingReviewToolbar.vue](D:/workspace/123/ccc/astrobiology/astro_frontend/src/components/review/PendingReviewToolbar.vue) + [PendingReviewTable.vue](D:/workspace/123/ccc/astrobiology/astro_frontend/src/components/review/PendingReviewTable.vue)
2. [RecycleBinManagement.vue](D:/workspace/123/ccc/astrobiology/astro_frontend/src/views/RecycleBinManagement.vue) + [RecycleBinToolbar.vue](D:/workspace/123/ccc/astrobiology/astro_frontend/src/components/review/RecycleBinToolbar.vue) + [RecycleBinTable.vue](D:/workspace/123/ccc/astrobiology/astro_frontend/src/components/review/RecycleBinTable.vue)
3. [DocumentManagementTab.vue](D:/workspace/123/ccc/astrobiology/astro_frontend/src/components/workspace/tabs/DocumentManagementTab.vue)

开始前必须确认：

- 过滤项标准写法
- 分页统一文案
- 详情弹窗字段名
- 审核、恢复、删除类按钮用语
- 页面说明和空状态语气

验证重点：

- 页面静态展示正确。
- 用户可见按钮文案与页面语义一致。
- 不发生路由、入口或事件流变化。

## 第三批：确认后单独修复的 composable 运行期提示

范围：

- `alert`
- `confirm`
- `prompt`
- 进度弹窗 `current_file`
- 错误/进度 `message`

建议处理对象：

- [useDocumentList.js](D:/workspace/123/ccc/astrobiology/astro_frontend/src/composables/useDocumentList.js)
- [useDocumentUpload.js](D:/workspace/123/ccc/astrobiology/astro_frontend/src/composables/useDocumentUpload.js)
- [useProcessingStatus.js](D:/workspace/123/ccc/astrobiology/astro_frontend/src/composables/useProcessingStatus.js)

开始前必须确认：

- 提示文案是偏技术说明还是偏用户导向
- 进度弹窗里的 `current_file` 是否允许简化
- 错误提示是否要保留原始后端错误拼接方式

验证重点：

- 上传流程
- 批量处理流程
- 增量修复/重新处理流程
- 删除/同步/下载确认框

## 第四批：单独审查后再决定是否修的后端备注类文本

范围：

- `reviewer_notes`
- `rejection_reason`
- `notes`
- 通过 payload 传递并可能跨层使用的 `message / current_file`

建议处理对象：

- [PendingReview.vue](D:/workspace/123/ccc/astrobiology/astro_frontend/src/views/PendingReview.vue)
- [RecycleBinManagement.vue](D:/workspace/123/ccc/astrobiology/astro_frontend/src/views/RecycleBinManagement.vue)
- [useDocumentUpload.js](D:/workspace/123/ccc/astrobiology/astro_frontend/src/composables/useDocumentUpload.js)
- [useProcessingStatus.js](D:/workspace/123/ccc/astrobiology/astro_frontend/src/composables/useProcessingStatus.js)

开始前必须确认：

- 这些字段是否被后端持久化
- 是否会在后台列表、日志、导出或审计记录中回显
- 是否已有历史数据依赖现有文案

验证重点：

- 提交请求 payload 不变，只改文本内容
- 后端回显和前端展示没有意外差异
- 审核、恢复、删除等历史记录未被破坏

## 推荐执行节奏

1. 先做第一批。
2. 第一批完成并验证后，再让人工确认第二批页面文案。
3. 第二批完成后，再单独处理第三批运行期提示。
4. 第四批最后做，且最好单开一次专门审查。

## 结论

**结论 A：现在可以直接进入第一批低风险文案修复**

原因：

- 第一批只涉及装饰符号、图标、纯调试串和分隔符。
- 这些项不改变业务语义，不写入后端，也不影响对外契约。
- 真正需要人工确认的是第二批及之后的业务文案，不应阻塞第一批低风险修复。
