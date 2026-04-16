# process_pending / process_stale Alignment Audit

## 实际检查过的文件

- `D:\workspace\123\ccc\astrobiology\backend\pdf_processor\weaviate_views.py`
- `D:\workspace\123\ccc\astrobiology\backend\pdf_processor\services\upload_storage_service.py`
- `D:\workspace\123\ccc\astrobiology\backend\pdf_processor\models.py`
- `D:\workspace\123\ccc\astrobiology\backend\pdf_processor\management\commands\reprocess_pdfs.py`
- `D:\workspace\123\ccc\astrobiology\backend\pdf_processor\management\commands\sync_pdfs.py`
- `D:\workspace\123\ccc\astrobiology\backend\tests\upload_storage_smoke_check.py`

补充说明：

- 本轮名义上的 `process_pending` / `process_stale` 并不是独立管理命令文件，它们位于
  `weaviate_views.py` 的 API action 中。
- `reprocess_pdfs.py` / `sync_pdfs.py` 被一并复核，用来确认当前统一后的 storage helper
  没有被这条链路重新绕开。

## 已对齐项

### 1. 目录来源

`process_pending` / `process_stale` 本身没有再自行决定 PDF 根目录。

- 它们直接消费数据库里已有的 `doc.file_path`
- 没有重新拼接 `data/pdfs`
- 没有绕开当前统一后的 `UploadStorageService`

这意味着：

- 新文件从 upload/storage 主线落盘后的路径会被这两个入口直接复用
- 至少在“目录来源”这一层，没有再次分叉出新的路径规则

### 2. 统一底座关系

当前 upload/storage 主线里的 canonical duplicate 解析仍然集中在
`UploadStorageService`：

- `resolve_content_document(...)`
- `inspect_duplicate_markers(...)`

`reprocess_pdfs.py` 和 `sync_pdfs.py` 也已经继续沿用统一 helper：

- `reprocess_pdfs.py` 使用 `UploadStorageService.resolve_pdf_storage_dir()`
- `sync_pdfs.py` 使用 `resolve_pdf_dir()` 包装同一个 helper

所以从“目录 / storage helper 是否重新分叉”的角度看，主线是对齐的。

## 未对齐项

### 1. duplicate 语义未对齐

这是本轮最关键的问题。

`process_pending` 当前逻辑：

- 直接取 `processed=False` 的全部 `PDFDocument`
- 按 `upload_date` 顺序逐条 `process_single_document(doc.file_path, document_id=str(doc.id), ...)`

`process_stale` 当前逻辑：

- 先取 `processed=False`
- 再补充 `processed=True` 但 `has_document_vectors(str(doc.id))` 为假的记录
- 同样逐条按 `doc.file_path + doc.id` 重跑处理

这两个入口都没有显式识别：

- `duplicate_of is null` 的 canonical 内容记录
- `duplicate_of is not null` 的 duplicate-hit 桥接记录

因此它们当前会把 duplicate-hit 子记录当成普通内容记录处理。

### 2. 这会触碰的真实语义

对 duplicate-hit 用户上传记录来说：

- 物理文件是复用 canonical 父记录的
- 但 `document_id` 是新的

如果 `process_pending` / `process_stale` 继续对这类子记录跑向量化：

- 同一 physical file 可能被按多个 `document_id` 反复处理
- 这到底算“应有行为”还是“多余索引”并不是基础设施问题
- 一旦改成“跳过 duplicate_of 子记录”或“只处理 canonical 父记录”，就会改变当前 review/index 语义

这已经超出本轮允许的窄修边界。

### 3. 日志与可观测性仍未完全收口

当前 upload/duplicate 主线已经有稳定 token：

- `user_upload_duplicate_hit`
- `weaviate_existing_hit`
- `filename_conflict=True`

但 `process_pending` / `process_stale` 仍主要使用人类可读日志：

- 批量处理完成
- 增量修复完成
- 处理失败

缺口在于：

- 没有稳定 token 区分 “pending 普通记录” 与 “pending duplicate child”
- 没有稳定 token 标明 “stale candidate 来自 processed=False” 还是 “来自缺向量”
- 这会让后续 smoke/assert 很难在不引入语义判断的前提下写得足够可靠

不过这个缺口本身不能单独窄修，因为一旦定义 token，就隐含了对 duplicate child
是否应被处理的立场。

## 可直接窄修 vs 应停止的高风险点

### 可直接窄修

本轮结论：没有值得直接动手的窄修项。

原因：

- 目录来源已经对齐
- helper 接线没有明显漏接
- 剩余问题都落在 duplicate child 的处理语义，而不是单纯基础设施缺口

### 应停止的高风险点

以下都应停在报告层，不宜直接改：

- 在 `process_pending` 中跳过 `duplicate_of` 子记录
- 在 `process_stale` 中只处理 canonical 记录
- 把 duplicate child 自动重定向到 parent `document_id`
- 改变 stale 判定逻辑，让多个共享 `file_path` 的记录共用同一向量状态
- 给这两个入口补带语义判断的 smoke，并据此强制当前行为变更

这些动作都会触碰：

- review flow 与向量化之间的现有边界
- duplicate-hit 用户上传记录是否应拥有独立“已处理/已建索引”状态
- 审核通过后自动索引语义

根据本轮边界，这些都不应直接改。

## 实际改动文件

无。

本轮只做审计，没有修改任何代码、配置、脚本、模型或测试文件。

## 明确说明

- 是否改了前端：否
- 是否改了 API 契约：否
- 是否改了业务分支语义：否

## 验证结果

### py_compile

执行：

- `py -m py_compile weaviate_views.py`
- `py -m py_compile upload_storage_service.py`
- `py -m py_compile reprocess_pdfs.py`
- `py -m py_compile sync_pdfs.py`
- `py -m py_compile upload_storage_smoke_check.py`

结果：

- 通过

### smoke / 命令验证

执行现有：

- `D:\workspace\123\ccc\astrobiology\backend\tests\upload_storage_smoke_check.py`

结果：

- `24 pass / 0 fail / 0 error`

说明：

- 当前 upload/storage/duplicate 主线仍稳定
- 但该 smoke 目前没有直接覆盖 `process_pending` / `process_stale` 的 duplicate child 处理语义
- 这是覆盖缺口，但是否要补，取决于先决定业务语义

## 结论

结论：适合提交当前状态，不建议在本轮继续改。

原因：

- “目录来源”这一层已经对齐
- 剩余问题不是 helper 缺口，而是 duplicate_of 桥接记录在处理链路中的业务语义
- 按当前约束，不应在没有单独语义决策的情况下直接窄修

如果继续下一轮，建议只做一件事：

- 先单独设计并确认 `process_pending / process_stale` 对 duplicate_of 子记录的目标语义

在此之前，不建议继续补日志 token、断言或处理分支。
