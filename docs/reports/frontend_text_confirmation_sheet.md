# frontend_text_confirmation_sheet

本表基于 [frontend_text_encoding_audit_report.md](D:/workspace/123/docs/reports/frontend_text_encoding_audit_report.md) 整理，目标是供人工逐项确认后再进入后续修复。

## 低风险项

| 编号 | 风险分组 | 文件路径 | 位置 | 原始异常文本 | 推测语义 | 建议修复文本 | 是否需要人工确认 | 为什么需要或不需要确认 | 是否属于用户可见文本 | 是否可能写入后端或持久化记录 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| C1 | 低 | [PendingReview.vue](D:/workspace/123/ccc/astrobiology/astro_frontend/src/views/PendingReview.vue) | template | `脳` | 关闭按钮符号 | `×` | 否 | 纯关闭符号，不承载业务语义 | 是 | 否 |
| C2 | 低 | [RecycleBinManagement.vue](D:/workspace/123/ccc/astrobiology/astro_frontend/src/views/RecycleBinManagement.vue) | template | `脳` | 关闭按钮符号 | `×` | 否 | 纯关闭符号，不承载业务语义 | 是 | 否 |
| C3 | 低 | [UnifiedReview.vue](D:/workspace/123/ccc/astrobiology/astro_frontend/src/views/UnifiedReview.vue) | template | `馃搵` | 空状态装饰图标 | 使用明确 emoji 或 SVG 占位图标 | 否 | 仅装饰，不影响数据和流程 | 是 | 否 |
| C4 | 低 | [PendingReviewTable.vue](D:/workspace/123/ccc/astrobiology/astro_frontend/src/components/review/PendingReviewTable.vue) | template | `馃搵` | 空状态装饰图标 | 使用明确 emoji 或 SVG 占位图标 | 否 | 仅装饰，不影响业务语义 | 是 | 否 |
| C5 | 低 | [RecycleBinTable.vue](D:/workspace/123/ccc/astrobiology/astro_frontend/src/components/review/RecycleBinTable.vue) | template | `馃棏` | 空状态装饰图标 | 使用明确 emoji 或 SVG 占位图标 | 否 | 仅装饰，不影响业务语义 | 是 | 否 |
| C6 | 低 | [PendingReviewToolbar.vue](D:/workspace/123/ccc/astrobiology/astro_frontend/src/components/review/PendingReviewToolbar.vue) | style | `content: '鈫?`, `content: '鉁?`, `content: '鈱?`, `content: '鈽?` | 伪元素图标字符损坏 | 改为稳定符号或移除伪元素并使用现有图标方案 | 否 | 纯装饰性伪元素，不影响交互协议 | 是 | 否 |
| C7 | 低 | [RecycleBinToolbar.vue](D:/workspace/123/ccc/astrobiology/astro_frontend/src/components/review/RecycleBinToolbar.vue) | style | `content: '鈫?`, `content: '馃棏'`, `content: '鈱?`, `content: '鈽?` | 伪元素图标字符损坏 | 改为稳定符号或移除伪元素并使用现有图标方案 | 否 | 纯装饰性伪元素，不影响交互协议 | 是 | 否 |
| C8 | 低 | [UnifiedReview.vue](D:/workspace/123/ccc/astrobiology/astro_frontend/src/views/UnifiedReview.vue) | script | `showNotification('鎷掔粷澶辫触: ' + ...)` | “拒绝失败:” 类错误前缀 | `Rejection failed: ` | 否 | 同文件其余提示均为英文，语义可靠 | 是 | 否 |
| C9 | 低 | [useDocumentList.js](D:/workspace/123/ccc/astrobiology/astro_frontend/src/composables/useDocumentList.js) | composable | 多处 `console.log/error(...)` 乱码 | 调试日志 | 统一改为英文或可读中文调试串 | 否 | 仅开发调试输出，不面向用户 | 否 | 否 |
| C10 | 低 | [useDocumentUpload.js](D:/workspace/123/ccc/astrobiology/astro_frontend/src/composables/useDocumentUpload.js) | composable | 多处 `console.log/error(...)` 乱码 | 上传流程调试日志 | 统一改为英文或可读中文调试串 | 否 | 仅开发调试输出，不面向用户 | 否 | 否 |
| C11 | 低 | [useProcessingStatus.js](D:/workspace/123/ccc/astrobiology/astro_frontend/src/composables/useProcessingStatus.js) | composable | 多处 `console.log/warn(...)` 乱码 | 处理流程调试日志 | 统一改为英文或可读中文调试串 | 否 | 仅开发调试输出，不面向用户 | 否 | 否 |
| C12 | 低 | [DocumentManagementTab.vue](D:/workspace/123/ccc/astrobiology/astro_frontend/src/components/workspace/tabs/DocumentManagementTab.vue) | template | `{{ doc.size }} 鈥?{{ doc.date }}` | 文档大小与日期之间的分隔符 | `{{ doc.size }} - {{ doc.date }}` 或 `{{ doc.size }} · {{ doc.date }}` | 否 | 纯分隔符，不承载业务语义 | 是 | 否 |

## 中风险项

| 编号 | 风险分组 | 文件路径 | 位置 | 原始异常文本 | 推测语义 | 建议修复文本 | 是否需要人工确认 | 为什么需要或不需要确认 | 是否属于用户可见文本 | 是否可能写入后端或持久化记录 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| C13 | 中 | [PendingReview.vue](D:/workspace/123/ccc/astrobiology/astro_frontend/src/views/PendingReview.vue) | template | `鍒嗙被`、`鍏ㄩ儴鍒嗙被`、`鏉ユ簮`、`鍏ㄩ儴鏉ユ簮` | 很可能是“分类 / 全部分类 / 来源 / 全部来源” | 暂不直接定稿 | 是 | 虽然从字段名可推断，但属于用户筛选文案，建议统一确认 | 是 | 否 |
| C14 | 中 | [PendingReview.vue](D:/workspace/123/ccc/astrobiology/astro_frontend/src/views/PendingReview.vue) | template | `涓婁竴椤?`、`涓嬩竴椤?`、`绗?{{ currentPage }} 椤...` | 很可能是“上一页 / 下一页 / 第 x 页，共 y 页，总计 z 条记录” | 暂不直接定稿 | 是 | 分页文案较可靠，但建议与全站分页表述统一 | 是 | 否 |
| C15 | 中 | [PendingReview.vue](D:/workspace/123/ccc/astrobiology/astro_frontend/src/views/PendingReview.vue) | template | `闄ㄧ煶璇︽儏`、`鍩烘湰淇℃伅`、`鍚嶇О`、`鎻忚堪`、`鍏抽棴` | 很可能是“陨石详情 / 基本信息 / 名称 / 描述 / 关闭” | 暂不直接定稿 | 是 | 详情弹窗可推断，但仍属于用户可见业务文案 | 是 | 否 |
| C16 | 中 | [PendingReview.vue](D:/workspace/123/ccc/astrobiology/astro_frontend/src/views/PendingReview.vue) | template | `閫氳繃瀹℃牳`、`鎷掔粷瀹℃牳` | 很可能是“通过审核 / 拒绝审核” | 暂不直接定稿 | 是 | 涉及审核动作按钮，建议和审核页面整体文案一起确认 | 是 | 否 |
| C17 | 中 | [PendingReviewToolbar.vue](D:/workspace/123/ccc/astrobiology/astro_frontend/src/components/review/PendingReviewToolbar.vue) | template | `鍒锋柊`、`鎵归噺閫氳繃`、`涓€閿€氳繃鍏ㄩ儴`、`绛涢€?`、搜索占位文本 | 刷新、批量审核、筛选、搜索 | 暂不直接定稿 | 是 | 工具栏文案成组出现，适合整组确认后再修 | 是 | 否 |
| C18 | 中 | [PendingReviewTable.vue](D:/workspace/123/ccc/astrobiology/astro_frontend/src/components/review/PendingReviewTable.vue) | template | `鍔犺浇涓?..`、`鏆傛棤寰呭鏍告暟鎹?`、`鏌ョ湅璇︽儏` 等 | 加载中、空状态、查看详情等 | 暂不直接定稿 | 是 | 包含空状态、表头、行级操作，适合整组确认 | 是 | 否 |
| C19 | 中 | [PendingReview.vue](D:/workspace/123/ccc/astrobiology/astro_frontend/src/views/PendingReview.vue) | script | 多处 `alert/confirm/prompt` 乱码 | 审核成功/失败、批量确认、拒绝原因提示 | 暂不直接定稿 | 是 | 直接影响用户操作判断，必须确认语义和语气 | 是 | 否 |
| C20 | 中 | [RecycleBinManagement.vue](D:/workspace/123/ccc/astrobiology/astro_frontend/src/views/RecycleBinManagement.vue) | template | 页面说明、过滤面板、分页、详情弹窗、恢复/删除按钮乱码 | 回收站管理页面业务文案 | 暂不直接定稿 | 是 | 涉及恢复与永久删除，建议人工确认 | 是 | 否 |
| C21 | 中 | [RecycleBinToolbar.vue](D:/workspace/123/ccc/astrobiology/astro_frontend/src/components/review/RecycleBinToolbar.vue) | template | `鍒锋柊`、`鎵归噺鎭㈠`、`姘镐箙鍒犻櫎`、`杩斿洖绠＄悊`、搜索占位文本 | 刷新、批量恢复、永久删除、返回管理、搜索 | 暂不直接定稿 | 是 | 都是用户可见动作文案，建议整组确认 | 是 | 否 |
| C22 | 中 | [RecycleBinTable.vue](D:/workspace/123/ccc/astrobiology/astro_frontend/src/components/review/RecycleBinTable.vue) | template | `鍔犺浇涓?..`、`鍥炴敹绔欎负绌?`、`鎭㈠鍒板緟瀹℃牳`、`姘镐箙鍒犻櫎` | 加载中、回收站为空、恢复、永久删除 | 暂不直接定稿 | 是 | 涉及高影响动作，建议整组确认 | 是 | 否 |
| C23 | 中 | [RecycleBinManagement.vue](D:/workspace/123/ccc/astrobiology/astro_frontend/src/views/RecycleBinManagement.vue) | script | 多处 `alert/confirm` 乱码 | 恢复成功/失败、删除成功/失败、批量确认 | 暂不直接定稿 | 是 | 直接影响用户确认和结果理解 | 是 | 否 |
| C24 | 中 | [DocumentManagementTab.vue](D:/workspace/123/ccc/astrobiology/astro_frontend/src/components/workspace/tabs/DocumentManagementTab.vue) | template | 页面标题、统计卡、搜索、上传/查看/下载/删除、空状态、分页、进度标题等大面积乱码 | 文档管理主页面全部 UI 文案 | 暂不直接定稿 | 是 | 覆盖范围最大，文案量最多，最需要先出对照表 | 是 | 否 |
| C25 | 中 | [useDocumentList.js](D:/workspace/123/ccc/astrobiology/astro_frontend/src/composables/useDocumentList.js) | composable | `alert(...)`、`confirm(...)`、`return '閺堫亞鐓￠弬鍥ㄣ€?'` | 下载失败、删除确认、同步提示、默认标题占位 | 暂不直接定稿 | 是 | 会直接影响用户提示或默认显示文本 | 间接是 | 否 |
| C26 | 中 | [useDocumentUpload.js](D:/workspace/123/ccc/astrobiology/astro_frontend/src/composables/useDocumentUpload.js) | composable | `message: ...`、`current_file: ...`、`alert(...)` | 上传异常、上传跳过、批处理进度提示 | 暂不直接定稿 | 是 | 进入进度窗/错误处理路径，用户会看到 | 间接是 | 否 |
| C27 | 中 | [useProcessingStatus.js](D:/workspace/123/ccc/astrobiology/astro_frontend/src/composables/useProcessingStatus.js) | composable | `confirm(...)`、`current_file: ...`、`message: ...` | 批量处理确认、进度提示、失败提示 | 暂不直接定稿 | 是 | 处理流程提示较敏感，需先确认语义 | 间接是 | 否 |

## 高风险项

| 编号 | 风险分组 | 文件路径 | 位置 | 原始异常文本 | 推测语义 | 建议修复文本 | 是否需要人工确认 | 为什么需要或不需要确认 | 是否属于用户可见文本 | 是否可能写入后端或持久化记录 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| C28 | 高 | [PendingReview.vue](D:/workspace/123/ccc/astrobiology/astro_frontend/src/views/PendingReview.vue) | script | `reviewer_notes: '閫氳繃瀹℃牳'`、`reviewer_notes: '鎷掔粷瀹℃牳'` | 很可能是审核备注 | 不给最终替换文本 | 是 | 该字段会随请求发送到后端，可能被记录、回显或审计 | 否或间接是 | 是 |
| C29 | 高 | [PendingReview.vue](D:/workspace/123/ccc/astrobiology/astro_frontend/src/views/PendingReview.vue) | script | `rejection_reason: '鏁版嵁涓嶇鍚堣姹?'` | 很可能是默认拒绝原因 | 不给最终替换文本 | 是 | 会进入后端业务数据，不能按普通 UI 文案处理 | 否或间接是 | 是 |
| C30 | 高 | [PendingReview.vue](D:/workspace/123/ccc/astrobiology/astro_frontend/src/views/PendingReview.vue) | script | `approveAllMeteorite('涓€閿€氳繃鍏ㄩ儴瀹℃牳')`、`rejectAllMeteorite(..., '涓€閿嫆缁濆叏閮ㄥ鏍?')` | 一键操作备注或说明 | 不给最终替换文本 | 是 | 入参会离开前端，可能被后端持久化 | 否或间接是 | 是 |
| C31 | 高 | [RecycleBinManagement.vue](D:/workspace/123/ccc/astrobiology/astro_frontend/src/views/RecycleBinManagement.vue) | script | `notes: '浠庡洖鏀剁珯鎭㈠'`、`notes: '姘镐箙鍒犻櫎'`、`notes: '鎵归噺鎭㈠'`、`notes: '鎵归噺姘镐箙鍒犻櫎'` | 恢复/删除操作备注 | 不给最终替换文本 | 是 | 这些备注可能成为持久化记录的一部分 | 否或间接是 | 是 |
| C32 | 高 | [useProcessingStatus.js](D:/workspace/123/ccc/astrobiology/astro_frontend/src/composables/useProcessingStatus.js) | composable | `current_file`、`message` 字段中的乱码文本 | 进度弹窗和错误载荷文本 | 不给最终替换文本 | 是 | 虽看似展示文案，但以 payload 形式跨组件传递，建议单独审查 | 间接是 | 可能 |
| C33 | 高 | [useDocumentUpload.js](D:/workspace/123/ccc/astrobiology/astro_frontend/src/composables/useDocumentUpload.js) | composable | `handleProcessingError({ message: ... })` 里的乱码消息 | 上传阶段错误消息载荷 | 不给最终替换文本 | 是 | 通过组件接口传递，后续可能影响统一错误展示 | 间接是 | 可能 |

## 推荐修复批次计划

### 第一批

- C1-C12
- 目标：只修关闭符号、空状态图标、伪元素图标、纯 console 字符串、纯分隔符
- 预期特点：不涉及业务语义，不触碰后端，不改 service/composable 对外契约

### 第二批

- C13-C24
- 目标：页面级和子组件级用户可见业务文案
- 前提：先由人工确认页面标题、按钮、空状态、分页、工具栏、详情弹窗文案

### 第三批

- C25-C27
- 目标：composable 里的 `alert / confirm / prompt / current_file / message`
- 前提：先确认这些提示的语气、动作风险提示级别和展示场景

### 第四批

- C28-C33
- 目标：后端备注类文本与跨组件 payload 文本
- 前提：单独审查这些字段是否会进入数据库、审计日志、导出结果或后端回显

## 建议使用方式

- 先让人工在 C13-C33 中补齐“确认版最终文案”。
- 第一批可单独先做，不必等待全部确认完成。
- 第四批不要和普通 UI 文案混做。
