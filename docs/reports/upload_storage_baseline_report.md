# upload/storage 基线验证报告

## 执行方式

- 验证脚本：`D:\workspace\123\ccc\astrobiology\backend\tests\upload_storage_smoke_check.py`
- 执行命令：`D:\workspace\123\.venv\Scripts\python.exe D:\workspace\123\ccc\astrobiology\backend\tests\upload_storage_smoke_check.py`

## 修改前基线结果

- 汇总：`pass=6`，`fail=1`，`error=0`

| 检查项 | 结果 | 说明 |
| --- | --- | --- |
| 用户上传一个新 PDF | 通过 | `views_user_upload.py` 会写入 `MEDIA_ROOT/uploads`，记录 `filename=原始文件名`、`review_status=pending`、`processed=False` |
| 跨入口重复上传同一份 PDF | 通过 | 已有同名 `PDFDocument` 时，Weaviate 上传入口会返回 `existing=true` 并跳过落盘 |
| direct processing 链路 | 通过 | 会写入 `MEDIA_ROOT/uploads` 并创建 `ProcessingTask`，对外返回 `task_id/status/message` |
| 旧路径兼容检查 | 通过 | 指向 `media/uploads` 与 `data/pdfs` 的历史 `file_path` 形式仍可被直接读取 |
| `reprocess_pdfs.py` 目录来源检查 | 失败 | 命令仍写死 `../data/pdfs`，未走统一配置或 helper |
| `PDFDocument` / `ProcessingTask` 关键字段检查 | 通过 | `filename/file_path/processed/sha1/review_status` 与 `document_path/options/status` 均仍存在 |
| Weaviate 链路最小 smoke | 通过 | 使用临时目录和 mock processor 验证上传、落盘、后台处理回调接线；未连接真实 Weaviate |

## 基线判断

- 当前上传/存储主链路没有明显断裂。
- 当前最明确、最值得在 Phase 1 收口的问题是：`reprocess_pdfs.py` 的目录来源仍然是相对路径字面量。
- 由于本轮禁止碰真实历史文件和真实数据库记录，基线验证采用了：
  - 临时目录隔离落盘
  - mock ORM / mock processor
  - 静态字段与源码检查

## 已知验证边界

- 未连接真实 PostgreSQL 测试库，避免影响现有 `PDFDocument` / `ProcessingTask` 数据。
- 未连接真实 Weaviate，只验证了上传入口与后台处理调用的接线。
- 未覆盖 `sync_pdfs.py`、`process_pending`、`process_stale` 的真实运行，只做了本轮主线必需的最小基线。
