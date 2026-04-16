# frontend_text_encoding_audit_report

## 一、审计范围

本轮只读审计了以下前端文件：

- [DocumentManagementTab.vue](D:/workspace/123/ccc/astrobiology/astro_frontend/src/components/workspace/tabs/DocumentManagementTab.vue)
- [PendingReview.vue](D:/workspace/123/ccc/astrobiology/astro_frontend/src/views/PendingReview.vue)
- [RecycleBinManagement.vue](D:/workspace/123/ccc/astrobiology/astro_frontend/src/views/RecycleBinManagement.vue)
- [UnifiedReview.vue](D:/workspace/123/ccc/astrobiology/astro_frontend/src/views/UnifiedReview.vue)
- [useDocumentList.js](D:/workspace/123/ccc/astrobiology/astro_frontend/src/composables/useDocumentList.js)
- [useDocumentUpload.js](D:/workspace/123/ccc/astrobiology/astro_frontend/src/composables/useDocumentUpload.js)
- [useProcessingStatus.js](D:/workspace/123/ccc/astrobiology/astro_frontend/src/composables/useProcessingStatus.js)
- [src/components/review/](D:/workspace/123/ccc/astrobiology/astro_frontend/src/components/review/)

识别到的异常主要分为 5 类：

- 真正的编码损坏/乱码
- 用户可见 UI 文案异常
- 运行期提示/错误提示异常
- 调试输出字符串异常
- 装饰性图标/占位文本损坏

未发现需要按“历史兼容占位文本”保留的乱码候选；相反，`UnifiedReview.vue` 与 [ReviewDetailDialog.vue](D:/workspace/123/ccc/astrobiology/astro_frontend/src/components/review/ReviewDetailDialog.vue)、[ReviewRejectDialog.vue](D:/workspace/123/ccc/astrobiology/astro_frontend/src/components/review/ReviewRejectDialog.vue) 中的英文文案看起来是当前刻意保留的正常文本，不属于编码问题。

## 二、低风险可直接修复项

这些项的共同特点是：不改变业务语义，不影响接口契约，不写入后端，只影响展示或调试可读性。

| 编号 | 文件路径 | 位置 | 原始异常文本 | 问题类型 | 是否用户可见 | 是否影响用户理解 | 是否可直接安全修复 | 是否需人工确认 | 风险 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| L1 | [PendingReview.vue](D:/workspace/123/ccc/astrobiology/astro_frontend/src/views/PendingReview.vue) | template | `脳` | 装饰性关闭符号损坏 | 是 | 中 | 是 | 否 | 低 |
| L2 | [RecycleBinManagement.vue](D:/workspace/123/ccc/astrobiology/astro_frontend/src/views/RecycleBinManagement.vue) | template | `脳` | 装饰性关闭符号损坏 | 是 | 中 | 是 | 否 | 低 |
| L3 | [UnifiedReview.vue](D:/workspace/123/ccc/astrobiology/astro_frontend/src/views/UnifiedReview.vue) | template | `馃搵` | 装饰性空状态图标损坏 | 是 | 低 | 是 | 否 | 低 |
| L4 | [PendingReviewTable.vue](D:/workspace/123/ccc/astrobiology/astro_frontend/src/components/review/PendingReviewTable.vue) | template | `馃搵` | 装饰性空状态图标损坏 | 是 | 低 | 是 | 否 | 低 |
| L5 | [RecycleBinTable.vue](D:/workspace/123/ccc/astrobiology/astro_frontend/src/components/review/RecycleBinTable.vue) | template | `馃棏` | 装饰性空状态图标损坏 | 是 | 低 | 是 | 否 | 低 |
| L6 | [PendingReviewToolbar.vue](D:/workspace/123/ccc/astrobiology/astro_frontend/src/components/review/PendingReviewToolbar.vue) | style | `content: '鈫?`, `content: '鉁?`, `content: '鈱?`, `content: '鈽?` | 装饰性伪元素图标损坏 | 是 | 中 | 是 | 否 | 低 |
| L7 | [RecycleBinToolbar.vue](D:/workspace/123/ccc/astrobiology/astro_frontend/src/components/review/RecycleBinToolbar.vue) | style | `content: '鈫?`, `content: '馃棏'`, `content: '鈱?`, `content: '鈽?` | 装饰性伪元素图标损坏 | 是 | 中 | 是 | 否 | 低 |
| L8 | [UnifiedReview.vue](D:/workspace/123/ccc/astrobiology/astro_frontend/src/views/UnifiedReview.vue) | script | `showNotification('鎷掔粷澶辫触: ' + ...)` | 运行期提示前缀损坏 | 是 | 中 | 是 | 否 | 低 |
| L9 | [useDocumentList.js](D:/workspace/123/ccc/astrobiology/astro_frontend/src/composables/useDocumentList.js) | composable/script | `console.error('鍔犺浇鏂囨。澶辫触:'...)`、`console.log('鏂囨。鍔犺浇鑰楁椂...' )` 等 | 调试输出字符串异常 | 否 | 低 | 是 | 否 | 低 |
| L10 | [useDocumentUpload.js](D:/workspace/123/ccc/astrobiology/astro_frontend/src/composables/useDocumentUpload.js) | composable/script | `console.log('鏂囦欢宸插瓨鍦...' )`、`console.error('...涓婁紶澶辫触')` | 调试输出字符串异常 | 否 | 低 | 是 | 否 | 低 |
| L11 | [useProcessingStatus.js](D:/workspace/123/ccc/astrobiology/astro_frontend/src/composables/useProcessingStatus.js) | composable/script | `console.log('澶勭悊瀹屾垚:'...)`、`console.warn('杞澶勭悊杩涘害澶辫触'...)` | 调试输出字符串异常 | 否 | 低 | 是 | 否 | 低 |
| L12 | [DocumentManagementTab.vue](D:/workspace/123/ccc/astrobiology/astro_frontend/src/components/workspace/tabs/DocumentManagementTab.vue) | template | `{{ doc.size }} 鈥?{{ doc.date }}` | 分隔符编码损坏 | 是 | 低 | 是 | 否 | 低 |

说明：

- L1-L7 是纯展示层符号/图标损坏，修复不会影响数据流。
- L8 语义可从同文件英文错误处理上下文可靠推断。
- L9-L11 仅影响开发调试可读性。
- L12 只是视觉分隔符，不涉及业务语义。

## 三、需要人工确认的文案项

这些项大多是用户可见业务文案，虽然很多从上下文看“可能”能猜回原意，但它们直接参与审核、删除、上传、处理等操作提示；为了避免误修，建议先人工确认一批关键文案。

| 编号 | 文件路径 | 位置 | 原始异常文本 | 问题类型 | 是否用户可见 | 是否影响用户理解 | 是否可直接安全修复 | 是否需人工确认 | 风险 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| M1 | [PendingReview.vue](D:/workspace/123/ccc/astrobiology/astro_frontend/src/views/PendingReview.vue) | template | `鍒嗙被`、`鍏ㄩ儴鍒嗙被`、`鏉ユ簮`、`鍏ㄩ儴鏉ユ簮` | 过滤面板 UI 文案乱码 | 是 | 高 | 否 | 是 | 中 |
| M2 | [PendingReview.vue](D:/workspace/123/ccc/astrobiology/astro_frontend/src/views/PendingReview.vue) | template | `涓婁竴椤?`、`涓嬩竴椤?`、`绗?{{ currentPage }} 椤...` | 分页文案乱码 | 是 | 中 | 否 | 是 | 中 |
| M3 | [PendingReview.vue](D:/workspace/123/ccc/astrobiology/astro_frontend/src/views/PendingReview.vue) | template | `闄ㄧ煶璇︽儏`、`鍩烘湰淇℃伅`、`鍚嶇О`、`鎻忚堪`、`鍏抽棴` | 详情弹窗 UI 文案乱码 | 是 | 高 | 否 | 是 | 中 |
| M4 | [PendingReview.vue](D:/workspace/123/ccc/astrobiology/astro_frontend/src/views/PendingReview.vue) | template | `閫氳繃瀹℃牳`、`鎷掔粷瀹℃牳` | 审核动作按钮文案乱码 | 是 | 高 | 否 | 是 | 中 |
| M5 | [PendingReviewToolbar.vue](D:/workspace/123/ccc/astrobiology/astro_frontend/src/components/review/PendingReviewToolbar.vue) | 子组件/template | `鍒锋柊`、`鎵归噺閫氳繃`、`涓€閿€氳繃鍏ㄩ儴`、`绛涢€?`、搜索占位文本 | 工具栏业务文案乱码 | 是 | 高 | 否 | 是 | 中 |
| M6 | [PendingReviewTable.vue](D:/workspace/123/ccc/astrobiology/astro_frontend/src/components/review/PendingReviewTable.vue) | 子组件/template | `鍔犺浇涓?..`、`鏆傛棤寰呭鏍告暟鎹?`、表头和按钮 `鏌ョ湅璇︽儏` 等 | 表格与空状态文案乱码 | 是 | 高 | 否 | 是 | 中 |
| M7 | [PendingReview.vue](D:/workspace/123/ccc/astrobiology/astro_frontend/src/views/PendingReview.vue) | script | `alert('瀹℃牳鎷掔粷鎴愬姛')`、`confirm(...)`、`prompt('璇疯緭鍏ユ嫆缁濆師鍥?'...)` | 运行期提示/确认文案乱码 | 是 | 高 | 否 | 是 | 中 |
| M8 | [RecycleBinManagement.vue](D:/workspace/123/ccc/astrobiology/astro_frontend/src/views/RecycleBinManagement.vue) | template | `绠＄悊琚嫆缁濈殑闄ㄧ煶...`、过滤面板、分页、`鍩烘湰淇℃伅`、`鎻忚堪` | 页面级 UI 文案乱码 | 是 | 高 | 否 | 是 | 中 |
| M9 | [RecycleBinToolbar.vue](D:/workspace/123/ccc/astrobiology/astro_frontend/src/components/review/RecycleBinToolbar.vue) | 子组件/template | `鍒锋柊`、`鎵归噺鎭㈠`、`姘镐箙鍒犻櫎`、`杩斿洖绠＄悊`、搜索占位文本 | 工具栏业务文案乱码 | 是 | 高 | 否 | 是 | 中 |
| M10 | [RecycleBinTable.vue](D:/workspace/123/ccc/astrobiology/astro_frontend/src/components/review/RecycleBinTable.vue) | 子组件/template | `鍔犺浇涓?..`、`鍥炴敹绔欎负绌?`、`鎭㈠鍒板緟瀹℃牳`、`姘镐箙鍒犻櫎` | 表格与空状态文案乱码 | 是 | 高 | 否 | 是 | 中 |
| M11 | [RecycleBinManagement.vue](D:/workspace/123/ccc/astrobiology/astro_frontend/src/views/RecycleBinManagement.vue) | script | `alert('鎭㈠鎴愬姛')`、`alert('姘镐箙鍒犻櫎鎴愬姛')`、批量操作 `confirm/alert` | 运行期提示/确认文案乱码 | 是 | 高 | 否 | 是 | 中 |
| M12 | [DocumentManagementTab.vue](D:/workspace/123/ccc/astrobiology/astro_frontend/src/components/workspace/tabs/DocumentManagementTab.vue) | template | 页面标题、统计卡、搜索占位、`涓婁紶PDF`、`鏌ョ湅`、`涓嬭浇`、`鍒犻櫎`、空状态、分页、`PDF鏂囨。澶勭悊杩涘害` | 文档管理主界面大量 UI 文案乱码 | 是 | 高 | 否 | 是 | 中 |
| M13 | [useDocumentList.js](D:/workspace/123/ccc/astrobiology/astro_frontend/src/composables/useDocumentList.js) | composable | `alert('涓嬭浇澶辫触...')`、`confirm('纭畾瑕佸垹闄...' )`、`alert('鍚屾澶辫触...' )`、`return '閺堫亞鐓￠弬鍥ㄣ€?'` | 用户提示/确认/默认标题文本乱码 | 否或间接是 | 中 | 否 | 是 | 中 |
| M14 | [useDocumentUpload.js](D:/workspace/123/ccc/astrobiology/astro_frontend/src/composables/useDocumentUpload.js) | composable | `message: '鏂囦欢宸插瓨鍦...'`、`current_file: '鍑嗗鎵归噺澶勭悊...'`、`alert('鎵€鏈夋枃浠朵笂浼犲け璐...' )` | 上传进度/错误提示乱码 | 间接是 | 高 | 否 | 是 | 中 |
| M15 | [useProcessingStatus.js](D:/workspace/123/ccc/astrobiology/astro_frontend/src/composables/useProcessingStatus.js) | composable | `confirm('纭畾瑕佸鐞嗘墍鏈夋湭澶勭悊...' )`、`current_file: '鍑嗗鎵归噺澶勭悊...'`、`message: '澶勭悊澶辫触'` | 处理流程确认/进度/错误提示乱码 | 间接是 | 高 | 否 | 是 | 中 |

说明：

- M1-M12 都是用户实际可见的页面或组件文案。
- M13-M15 虽然位于 composable，但会进入 `alert`、`confirm`、进度弹窗或错误展示，仍会影响用户理解。
- 这些项很多能“猜测”大意，但为了避免把业务语义修错，建议先做一次人工确认。

## 四、当前不建议处理的项

这些项不是“不能修”，而是不建议在下一轮把它们混进同一批文案编码修复里。

| 编号 | 文件路径 | 位置 | 原始异常文本 | 问题类型 | 是否用户可见 | 是否影响用户理解 | 是否可直接安全修复 | 是否需人工确认 | 风险 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| H1 | [PendingReview.vue](D:/workspace/123/ccc/astrobiology/astro_frontend/src/views/PendingReview.vue) | script | `reviewer_notes: '閫氳繃瀹℃牳'`、`reviewer_notes: '鎷掔粷瀹℃牳'`、`rejection_reason: '鏁版嵁涓嶇鍚堣姹?'`、`approveAllMeteorite('涓€閿€氳繃鍏ㄩ儴瀹℃牳')`、`rejectAllMeteorite(..., '涓€閿嫆缁濆叏閮ㄥ鏍?')` | 传入后端的审核备注/拒绝原因 | 可能间接可见 | 高 | 否 | 是 | 高 |
| H2 | [RecycleBinManagement.vue](D:/workspace/123/ccc/astrobiology/astro_frontend/src/views/RecycleBinManagement.vue) | script | `notes: '浠庡洖鏀剁珯鎭㈠'`、`notes: '姘镐箙鍒犻櫎'`、`notes: '鎵归噺鎭㈠'`、`notes: '鎵归噺姘镐箙鍒犻櫎'` | 传入后端的操作备注 | 可能间接可见 | 高 | 否 | 是 | 高 |
| H3 | [useProcessingStatus.js](D:/workspace/123/ccc/astrobiology/astro_frontend/src/composables/useProcessingStatus.js) | composable | `current_file`、`message` 载荷中的乱码文案 | 进度/错误载荷文本 | 间接是 | 中 | 否 | 是 | 高 |
| H4 | [useDocumentUpload.js](D:/workspace/123/ccc/astrobiology/astro_frontend/src/composables/useDocumentUpload.js) | composable | `progressModalRef.value.handleProcessingError({ message: ... })` 中的乱码消息 | 组件间传递的错误文案 | 间接是 | 中 | 否 | 是 | 高 |
| H5 | [UnifiedReview.vue](D:/workspace/123/ccc/astrobiology/astro_frontend/src/views/UnifiedReview.vue)、[ReviewDetailDialog.vue](D:/workspace/123/ccc/astrobiology/astro_frontend/src/components/review/ReviewDetailDialog.vue)、[ReviewRejectDialog.vue](D:/workspace/123/ccc/astrobiology/astro_frontend/src/components/review/ReviewRejectDialog.vue) | template/script | 英文界面文案、本地 `x` 关闭字符 | 非编码问题，不是本轮乱码候选 | 是 | 低 | 不适用 | 否 | 低 |

判断依据：

- H1-H2 虽然从上下文看很像“审核备注/拒绝原因/删除备注”，但这类字符串会进入后端或持久化记录，不能按普通 UI 文案批量替换。
- H3-H4 目前看像纯展示文本，但它们通过 payload 在组件间传递，下一轮若修复，建议和进度弹窗一起做最小验证。
- H5 不是乱码问题，继续处理反而会扩大范围。

## 五、建议的修复顺序

1. 先修低风险装饰项与调试串。
   - 关闭按钮字符
   - 空状态 emoji/伪元素图标
   - 纯 `console.*` 调试字符串
   - 可中性替换的分隔符

2. 再修页面级用户可见文案，但只限经过人工确认的一批。
   - `PendingReview.vue` 与 review 子组件
   - `RecycleBinManagement.vue` 与 review 子组件
   - `DocumentManagementTab.vue`

3. 最后单独处理 composable 里的运行期提示文本。
   - `alert/confirm`
   - 进度弹窗 `current_file`
   - `handleProcessingError` / `message` 载荷

4. 不要把后端备注类 payload 文案和普通 UI 文案混在一轮里改。
   - `reviewer_notes`
   - `rejection_reason`
   - `notes`

## 六、如果进入下一轮修复，建议采用的最小修改策略

- 先建立“已人工确认文案对照表”。
  - 每条乱码文案只修一次。
  - 不在代码里边看边猜。

- 第一批只动低风险项。
  - 关闭符号、空状态图标、伪元素图标、纯调试字符串、纯分隔符。
  - 这一批不需要改接口、不需要改状态流。

- 第二批按页面逐个修用户可见文案。
  - 先 `PendingReview.vue` + review 子组件。
  - 再 `RecycleBinManagement.vue` + review 子组件。
  - 最后再处理 `DocumentManagementTab.vue`，因为它文案密度最高、覆盖面最广。

- 第三批单独修 composable 的运行期提示。
  - 每修一个 composable，就做一次页面 smoke check。
  - 重点看确认框、错误提示、进度弹窗是否仍按原流程出现。

- 后端备注类文本单独审查。
  - `reviewer_notes`、`rejection_reason`、`notes` 不要在“前端文案清理”中顺手改。
  - 需要确认这些字段是否会被后端记录、回显、导出或参与审计。

## 结论

**结论 B：应先人工确认一批关键业务文案，再修复**

原因：

- 当前确实存在一批可直接修复的低风险编码问题，但占比更大的问题落在审核、删除、恢复、上传、处理等业务文案上。
- 这些字符串不少都处在用户确认、操作结果提示、进度反馈或后端备注载荷中；如果不先确认语义，直接批量修会有误修风险。
- 最合适的下一步是先整理一个“确认版文案映射表”，再按低风险项 -> 页面文案 -> composable 运行期提示 -> 后端备注载荷的顺序收口。
