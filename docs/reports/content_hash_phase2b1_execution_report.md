# 内容哈希识别 Phase 2B-1 执行报告

## 1. 修改前基线结果

### 验证脚本

- `D:\workspace\123\ccc\astrobiology\backend\tests\upload_storage_smoke_check.py`

### 修改前结果

- 汇总：`pass=9`，`fail=4`，`error=0`

### 修改前失败的 4 项

| 检查项 | 修改前结果 | 原因 |
| --- | --- | --- |
| `same_name_different_content_identification` | 失败 | `UploadStorageService` 还没有同名不同内容识别方法 |
| `different_name_same_content_identification` | 失败 | `UploadStorageService` 还没有同内容重复识别方法 |
| `user_vs_direct_duplicate_logging` | 失败 | direct processing 入口还没有接入统一识别/日志 |
| `user_vs_weaviate_duplicate_logging` | 失败 | weaviate 上传入口还没有接入统一识别/日志 |

### 修改前已通过的 9 项

- 用户上传 smoke
- 跨入口重复上传（同名）smoke
- direct processing smoke
- 旧路径兼容
- `reprocess_pdfs.py` 目录来源检查
- `sync_pdfs.py` 目录来源检查
- `sync_pdfs.py` 最小 smoke
- 关键字段契约检查
- Weaviate 最小 smoke

## 2. 实际修改了哪些文件

- `D:\workspace\123\ccc\astrobiology\backend\pdf_processor\services\upload_storage_service.py`
- `D:\workspace\123\ccc\astrobiology\backend\pdf_processor\services\__init__.py`
- `D:\workspace\123\ccc\astrobiology\backend\pdf_processor\views_user_upload.py`
- `D:\workspace\123\ccc\astrobiology\backend\pdf_processor\views\direct_processing_views.py`
- `D:\workspace\123\ccc\astrobiology\backend\pdf_processor\weaviate_views.py`
- `D:\workspace\123\ccc\astrobiology\backend\tests\upload_storage_smoke_check.py`

## 3. 新增了哪些识别逻辑 / 内部标记

### helper 层新增

在 `upload_storage_service.py` 中新增了：

- `DuplicateInspection`
- `calculate_upload_sha1(uploaded_file)`
- `inspect_duplicate_markers(original_filename, sha1)`
- `inspect_uploaded_file(uploaded_file)`
- `log_duplicate_inspection(logger, source, inspection)`

### 新增的内部标记

本轮新增的内部识别字段包括：

- `duplicate_detected`
- `duplicate_sha1`
- `duplicate_document_id`
- `filename_conflict`
- `filename_conflict_document_id`
- `filename_conflict_same_content`

这些字段目前只用于：

- helper 返回对象
- 内部日志
- smoke 验证

没有改前端，也没有改外部 API 返回结构。

### 新增的最小内部数据补充

- `views_user_upload.py` 现在会把新上传文件的 `sha1` 写入 `PDFDocument.sha1`
- `weaviate_views.py` 现在也会把新上传文件的 `sha1` 写入 `PDFDocument.sha1`

这属于使用现有字段补充新记录元数据，不是数据库结构变更。

## 4. 三个入口分别如何接入哈希识别

### 用户上传入口

- 文件：`views_user_upload.py`
- 接入方式：
  - 在现有文件类型/大小校验后
  - 先调用 `UploadStorageService.inspect_uploaded_file(uploaded_file)`
  - 输出统一识别日志
  - 然后继续原来的同名检查、保存、建 `PDFDocument`
- 外部行为：
  - 不变
  - 仍然按原逻辑处理同名文件
  - 仍然创建待审核记录

### direct processing 上传入口

- 文件：`views/direct_processing_views.py`
- 接入方式：
  - 在保存前先做 `inspect_uploaded_file`
  - 输出统一识别日志
  - 仍然创建 `ProcessingTask`
  - 批量上传也接入了同样的日志识别
- 外部行为：
  - 不变
  - 不阻断任务创建
  - 不复用旧文件

### Weaviate 上传入口

- 文件：`weaviate_views.py`
- 接入方式：
  - 在现有同名检查前先做 `inspect_uploaded_file`
  - 输出统一识别日志
  - 继续原来的保存、建 `PDFDocument`、异步处理
- 外部行为：
  - 不变
  - 不阻断上传
  - 不跳过建记录

## 5. 修改后验证结果

### 静态导入检查

- 执行：`python -m py_compile`
- 结果：通过
- 覆盖文件：
  - `upload_storage_service.py`
  - `services/__init__.py`
  - `views_user_upload.py`
  - `views/direct_processing_views.py`
  - `weaviate_views.py`
  - `upload_storage_smoke_check.py`

### 修改后 smoke 复跑结果

- 汇总：`pass=13`，`fail=0`，`error=0`

### 新增识别基线结果

| 检查项 | 修改前 | 修改后 | 结论 |
| --- | --- | --- | --- |
| `same_name_different_content_identification` | 失败 | 通过 | helper 已能识别同名不同内容 |
| `different_name_same_content_identification` | 失败 | 通过 | helper 已能识别不同名同内容 |
| `user_vs_direct_duplicate_logging` | 失败 | 通过 | direct processing 已接入统一日志识别 |
| `user_vs_weaviate_duplicate_logging` | 失败 | 通过 | weaviate 上传已接入统一日志识别 |

### 既有 smoke 结果

- 原有 9 项继续全部通过。

## 6. 修改前后对比

### 新增了什么

- 新文件进入时，系统现在能统一识别：
  - 是否命中已有 `PDFDocument.sha1`
  - 是否与已有同名记录内容不同
- 三个入口现在都会输出一致风格的识别日志
- 新建 `PDFDocument` 记录时会携带 `sha1`

### 没有改变什么

- API 路由未变
- HTTP method 未变
- payload 结构未变
- 用户上传仍会保存新文件、仍会建待审核 `PDFDocument`
- direct processing 仍会保存新文件、仍会建 `ProcessingTask`
- Weaviate 上传仍会保存新文件、仍会建 `PDFDocument` 并异步处理
- 没有阻断上传
- 没有复用旧文件替代新文件
- 没有自动合并任何记录

## 7. 是否发现功能失效或行为变化

- 当前 smoke 范围内未发现功能失效。
- 未观察到对外语义变化。
- 本轮变化只体现在：
  - 新增内部识别
  - 新增日志/内部标记
  - 新建 `PDFDocument` 时补写 `sha1`

## 8. 当前仍未解决的点

- 识别到了重复，但还没有阻断式去重
- direct processing 仍无法基于持久化哈希识别“历史 ProcessingTask 级重复”
- 历史 `PDFDocument.sha1` 为空的记录仍然无法完整参与去重判断
- `sync_pdfs.py` / `reprocess_pdfs.py` 仍未接入“重复识别日志”，本轮按要求未扩范围
- 审核通过自动索引语义仍未触碰

## 9. 下一步是否适合进入 Phase 2B-2

- 适合，但应只在一个最安全入口试点。
- 当前最安全的试点入口仍然是：
  - `weaviate_views.py` 的 `upload`

原因：

- 它本来就有 `existing` 型跳过语义
- 把“同内容不同名”纳入这条入口的最小阻断策略，风险低于用户上传和 direct processing

## 结论

- Phase 2B-1 已完成。
- 本轮只增加了内容哈希识别和一致日志/标记，没有把“识别”升级成“阻断”。
- 修改后新增识别基线全部通过，原有 smoke 也全部保持通过。
- 现在适合进入 Phase 2B-2，但建议只在 Weaviate 上传入口做单入口试点。
