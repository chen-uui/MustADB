# upload/storage Phase 1 执行报告

## 1. 修改前基线验证结果

- 基线报告：`D:\workspace\123\docs\reports\upload_storage_baseline_report.md`
- 修改前汇总：`pass=6`，`fail=1`，`error=0`
- 唯一失败项：`reprocess_pdfs.py` 仍使用相对路径 `../data/pdfs`

## 2. 实际修改了哪些文件

- `D:\workspace\123\ccc\astrobiology\backend\pdf_processor\services\upload_storage_service.py`
- `D:\workspace\123\ccc\astrobiology\backend\pdf_processor\services\__init__.py`
- `D:\workspace\123\ccc\astrobiology\backend\pdf_processor\views_user_upload.py`
- `D:\workspace\123\ccc\astrobiology\backend\pdf_processor\views\direct_processing_views.py`
- `D:\workspace\123\ccc\astrobiology\backend\pdf_processor\weaviate_views.py`
- `D:\workspace\123\ccc\astrobiology\backend\pdf_processor\management\commands\reprocess_pdfs.py`
- `D:\workspace\123\ccc\astrobiology\backend\tests\upload_storage_smoke_check.py`

## 3. 新增了哪些 service / helper

### `UploadStorageService`

- 新增位置：`D:\workspace\123\ccc\astrobiology\backend\pdf_processor\services\upload_storage_service.py`
- 本轮只做了 4 件事：
  - 统一解析 `MEDIA_ROOT/uploads`
  - 统一解析 `PDF_STORAGE_PATH`
  - 统一决定文件命名策略：`uuid` / `original`
  - 统一保存上传文件并封装基础元数据：`file_path/file_size/sha1/original_filename/stored_filename`

### 本轮没有做的事

- 没有批量迁移历史文件
- 没有修改 `PDFDocument` 模型结构
- 没有统一去重策略
- 没有改审核通过后的业务语义

## 4. 哪些入口已经接入统一逻辑

### 已接入

- `views_user_upload.py`
  - 现在通过 `UploadStorageService.save_uploaded_file(..., storage_key=MEDIA_UPLOADS, naming_strategy='uuid')` 保存文件
- `views/direct_processing_views.py`
  - `_save_uploaded_file()` 现在复用同一 helper
- `weaviate_views.py`
  - `upload()` 现在通过 `UploadStorageService.save_uploaded_file(..., storage_key=PDF_LIBRARY, naming_strategy='original')` 保存文件
- `reprocess_pdfs.py`
  - 目录来源改为 `UploadStorageService.resolve_pdf_storage_dir()`

### 暂未完全接入

- `weaviate_views.py` 的 `sync_files`
  - 仍保留原有目录/同步逻辑，本轮只收口上传入口，不扩大到同步命令
- `weaviate_views.py` 的 `process_pending` / `process_stale`
  - 仍按既有 `PDFDocument.file_path` 工作，本轮保持兼容，不改处理语义
- `sync_pdfs.py`
  - 仍是独立历史命令，当前未接入统一 helper
- `views_review.py`
  - 审核通过后是否自动触发索引仍未改变，本轮明确不动业务语义

## 5. 修改后验证结果

### 静态导入检查

- 执行：`python -m py_compile`
- 结果：通过
- 覆盖文件：
  - `upload_storage_service.py`
  - `views_user_upload.py`
  - `direct_processing_views.py`
  - `weaviate_views.py`
  - `reprocess_pdfs.py`
  - `upload_storage_smoke_check.py`

### Phase 0 smoke 复跑

- 执行命令：`D:\workspace\123\.venv\Scripts\python.exe D:\workspace\123\ccc\astrobiology\backend\tests\upload_storage_smoke_check.py`
- 修改后汇总：`pass=7`，`fail=0`，`error=0`

| 检查项 | 修改前 | 修改后 | 结论 |
| --- | --- | --- | --- |
| 用户上传一个新 PDF | 通过 | 通过 | 外部行为一致 |
| 跨入口重复上传同一份 PDF | 通过 | 通过 | 外部行为一致 |
| direct processing 链路 | 通过 | 通过 | 外部行为一致 |
| 旧路径兼容检查 | 通过 | 通过 | 历史路径读取未破坏 |
| `reprocess_pdfs.py` 目录来源检查 | 失败 | 通过 | 已收口到统一 helper |
| 关键字段检查 | 通过 | 通过 | 字段契约未变 |
| Weaviate 最小 smoke | 通过 | 通过 | 上传与后台处理接线仍正常 |

## 6. 修改前后对比

### 发生了变化的地方

- 路径决定逻辑不再散落在 3 个入口和 1 个命令里，而是集中到 `UploadStorageService`
- `reprocess_pdfs.py` 不再依赖相对路径字面量
- 保存上传文件时会统一返回基础元数据对象，后续继续扩展去重或元数据归一化时有落点

### 没有变化的地方

- API 路由、HTTP method、payload 结构未变
- 用户上传仍写入 `MEDIA_ROOT/uploads`，仍是 UUID 磁盘名，仍建待审核 `PDFDocument`
- direct processing 仍写入 `MEDIA_ROOT/uploads`，仍建 `ProcessingTask`
- Weaviate 上传仍写入 PDF 库目录，仍保留原始文件名，仍触发异步处理
- 历史文件路径未迁移，旧记录读取兼容性未主动改变

## 7. 是否发现功能失效或行为变化

- 本轮验证中未发现明确功能失效。
- 基于当前 smoke 范围，未观察到对外行为语义变化。
- 本轮变化主要是内部实现收口，不是业务流程变更。

## 8. 当前仍存在的验证缺口

- 没有连接真实 PostgreSQL 测试库，因此未做真实数据库写入级的集成回归。
- 没有连接真实 Weaviate，只做了 mock processor 的非破坏 smoke。
- 未覆盖：
  - `sync_pdfs.py`
  - `process_pending`
  - `process_stale`
  - 审核通过后触发处理的业务语义决策

## 9. 下一步是否适合进入更深一步的上传/存储统一

- 适合继续，但应保持窄范围。
- 建议下一步优先级：
  1. 让 `sync_pdfs.py` 与统一 helper 对齐
  2. 设计内容哈希去重的最小策略
  3. 单独确认“审核通过后是否自动进入索引”这个业务语义

## 10. 结论

- Phase 0 基线已补齐，并已在修改前后各执行一遍。
- Phase 1 的最小统一实现已完成，且当前 smoke 未发现回归。
- 现在适合进入下一步更深一层的上传/存储统一，但仍应避免一次性触碰去重、审核语义和历史数据迁移。
