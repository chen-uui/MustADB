# upload/storage Phase 2A sync 收口报告

## 1. sync_pdfs.py 修改前基线结果

### 验证方式

- 验证脚本：`D:\workspace\123\ccc\astrobiology\backend\tests\upload_storage_smoke_check.py`
- 执行命令：`D:\workspace\123\.venv\Scripts\python.exe D:\workspace\123\ccc\astrobiology\backend\tests\upload_storage_smoke_check.py`

### 修改前结果

- 汇总：`pass=8`，`fail=1`，`error=0`

| 检查项 | 修改前结果 | 说明 |
| --- | --- | --- |
| `sync_directory_source` | 失败 | `sync_pdfs.py` 仍在 `handle()` 中直接使用 `Path(settings.BASE_DIR).parent / 'pdfs'` |
| `sync_command_smoke` | 通过 | 在临时目录 + mock `PDFDocument.objects` 下，`sync_pdfs()` 仍能新增 1 条记录、删除 0 条记录 |
| Phase 1 既有 7 项 smoke | 全部通过 | 用户上传、跨入口重复、direct processing、旧路径兼容、reprocess 目录来源、字段契约、Weaviate 最小 smoke 均保持通过 |

### 修改前的真实目录来源

- `sync_pdfs.py` 原先在 `handle()` 中直接设置：
  - `Path(settings.BASE_DIR).parent / 'pdfs'`
- 这条路径与当前统一 helper 的目录来源不一致：
  - `UploadStorageService.resolve_pdf_storage_dir() -> D:\workspace\123\ccc\astrobiology\data\pdfs`

## 2. 实际修改了哪些文件

- `D:\workspace\123\ccc\astrobiology\backend\pdf_processor\management\commands\sync_pdfs.py`
- `D:\workspace\123\ccc\astrobiology\backend\tests\upload_storage_smoke_check.py`

## 3. sync_pdfs.py 原先的目录来源是什么

- 原先是命令内部自带的一条历史路径规则：
  - `Path(settings.BASE_DIR).parent / 'pdfs'`
- 问题不在同步流程本身，而在于：
  - 它没有复用 `UploadStorageService`
  - 它和 `reprocess_pdfs.py`、`weaviate upload` 的目录标准不一致
  - 后续如果统一存储根目录，`sync_pdfs.py` 会成为新的分叉点

## 4. 现在如何与 UploadStorageService 对齐

### 本轮最小实现

- 在 `sync_pdfs.py` 中新增：
  - `resolve_pdf_dir()`
- 该方法现在统一返回：
  - `UploadStorageService.resolve_pdf_storage_dir()`
- `handle()` 不再自己拼目录，而是调用：
  - `self.pdf_dir = self.resolve_pdf_dir()`

### 本轮没有改的内容

- 没有改 `sync_pdfs()` 的同步职责
- 没有改新增/删除数据库记录的行为
- 没有改 `PDFDocument` 模型
- 没有改去重策略
- 没有改 `process_pending` / `process_stale`
- 没有改审核通过后的索引语义

## 5. 修改后验证结果

### 静态导入检查

- 执行：`python -m py_compile`
- 结果：通过
- 覆盖文件：
  - `sync_pdfs.py`
  - `upload_storage_smoke_check.py`

### 修改后 smoke 复跑结果

- 汇总：`pass=9`，`fail=0`，`error=0`

| 检查项 | 修改前 | 修改后 | 结论 |
| --- | --- | --- | --- |
| `sync_directory_source` | 失败 | 通过 | 目录来源已收口到统一 helper |
| `sync_command_smoke` | 通过 | 通过 | 同步核心职责未回归 |
| Phase 1 既有 7 项 smoke | 全部通过 | 全部通过 | 现有上传/存储主链路未受影响 |

## 6. Phase 1 的 smoke 是否仍然通过

- 仍然全部通过。
- 具体仍通过的 7 项：
  - 用户上传一个新 PDF
  - 跨入口重复上传同一份 PDF
  - direct processing 链路
  - 旧路径兼容检查
  - `reprocess_pdfs.py` 目录来源检查
  - `PDFDocument` / `ProcessingTask` 关键字段检查
  - Weaviate 最小 smoke

## 7. 是否发现功能失效或行为变化

- 本轮未发现明确功能失效。
- 从当前 smoke 看，`sync_pdfs.py` 的对外职责没有变化：
  - 仍扫描一个 PDF 目录
  - 仍按文件夹内容补建/删除 `PDFDocument`
- 变化只发生在“目录从哪里来”这一层。

## 8. 当前仍未收口的点

- `weaviate_views.py` 的 `sync_files` 仍保留自己的同步逻辑
- `process_pending` / `process_stale` 仍按既有 `file_path` 工作
- 内容哈希去重策略尚未设计落地
- `sync_pdfs.py` 仍然用文件名作为同步键，本轮刻意没有碰这部分
- 审核通过后是否自动进入索引，仍是单独业务语义问题

## 9. 下一步是否适合进入“内容哈希去重最小策略设计”

- 适合。
- 原因：
  - 当前主要路径分叉点已经进一步收口
  - `reprocess_pdfs.py` 与 `sync_pdfs.py` 都已经能对齐到统一 helper
  - 现在进入“内容哈希去重最小策略设计”会比之前更稳，因为目录来源已经不再分裂

## 结论

- `sync_pdfs.py` 这个历史分叉点已经收口到 `UploadStorageService`
- 修改后未观察到 Phase 1 主链路回归
- 当前可以进入下一轮“内容哈希去重最小策略设计”，但仍应保持设计先行，不要直接扩成数据迁移或业务语义改造
