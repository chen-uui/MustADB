# 用户上传重复命中 Phase 实施报告

## 1. 修改前基线结果

本轮先补充并执行了面向用户上传 duplicate-hit 过渡方案的基线 smoke。

修改前基线汇总：

- `pass=22`
- `fail=2`
- `error=0`

修改前明确失败的 2 项：

1. `user_different_name_same_content_pending_action`
   - 现状仍会重复落盘
   - 新建记录时没有 `duplicate_of`
2. `record_contract_fields`
   - `PDFDocument` 还没有 `duplicate_of` 字段

其余基线均通过，说明：

- 用户上传全新 PDF 正常
- 用户上传同名同内容 / 同名不同内容仍走当前 filename guard
- 待审核列表、审批隔离、共享 `file_path` 下载兼容、旧路径兼容
- Phase 1 / 2A / 2B-1 / 2B-2 既有 smoke 均保持正常

## 2. 实际修改了哪些文件

- [models.py](D:/workspace/123/ccc/astrobiology/backend/pdf_processor/models.py)
- [upload_storage_service.py](D:/workspace/123/ccc/astrobiology/backend/pdf_processor/services/upload_storage_service.py)
- [views_user_upload.py](D:/workspace/123/ccc/astrobiology/backend/pdf_processor/views_user_upload.py)
- [0010_pdfdocument_duplicate_of.py](D:/workspace/123/ccc/astrobiology/backend/pdf_processor/migrations/0010_pdfdocument_duplicate_of.py)
- [upload_storage_smoke_check.py](D:/workspace/123/ccc/astrobiology/backend/tests/upload_storage_smoke_check.py)

本轮未修改：

- [views_review.py](D:/workspace/123/ccc/astrobiology/backend/pdf_processor/views_review.py)
- `direct_processing`
- `sync_pdfs.py`
- `reprocess_pdfs.py`
- 前端代码

## 3. 新增的模型字段和 migration 内容

### 新增字段

在 `PDFDocument` 上新增了可空自关联字段：

- `duplicate_of`

语义：

- `duplicate_of is null`
  - 该记录自带物理文件，可视为内容主记录
- `duplicate_of is not null`
  - 该记录是新的审核动作
  - 复用 `duplicate_of` 指向的内容主记录的 `file_path` / `sha1`

### migration

新增 migration：

- [0010_pdfdocument_duplicate_of.py](D:/workspace/123/ccc/astrobiology/backend/pdf_processor/migrations/0010_pdfdocument_duplicate_of.py)

内容是一次最小 schema 变更：

- `AddField(PDFDocument.duplicate_of)`
- 可空外键
- `SET_NULL`
- 无历史回填

本轮还在本地执行了：

- `python manage.py migrate pdf_processor 0010`

目的仅是让本地验证路径与新模型保持一致，不涉及历史数据迁移或回填。

## 4. 用户上传入口原先的重复处理行为是什么

原先用户上传入口的行为是：

- 全新 PDF：落盘到 `MEDIA_ROOT/uploads`，创建新的 `pending PDFDocument`
- 同名同内容：被现有 filename guard 拦住
- 同名不同内容：同样被现有 filename guard 拦住
- 不同名同内容：
  - 仍会重复落盘
  - 仍会创建新的 `pending PDFDocument`
  - 新记录不指向已有内容主记录

也就是说，原先对“不同名同内容”没有真正的物理层去重。

## 5. 现在的最小重复命中行为是什么

本轮只在用户上传入口引入了过渡逻辑。

新行为：

- 用户上传全新 PDF：
  - 保持原样
  - 仍落盘
  - 仍创建新的 `pending PDFDocument`
- 用户上传同名同内容 PDF：
  - 保持当前已有行为
  - 仍由 filename guard 拦截
- 用户上传同名不同内容 PDF：
  - 保持当前已有行为
  - 仍由 filename guard 谨慎拦截
- 用户上传不同名同内容 PDF：
  - 不再重复落盘新文件
  - 新建一条新的 `pending PDFDocument`
  - 新记录的 `duplicate_of` 指向已有内容主记录
  - 新记录复用主记录的 `file_path` / `sha1`
  - 新记录仍保留本次 `filename`、`uploaded_by`、`upload_date` 语义
  - 返回仍是新的 `document_id`

## 6. 哪些情况会复用已有内容，哪些情况不会

会复用已有内容的情况：

- 仅限用户上传入口
- 且仅限“不同名同内容”
- 且必须能可靠定位到已有内容主记录
- 且已有主记录 `file_path` 存在

不会复用已有内容的情况：

- 用户上传全新内容
- 用户上传同名同内容
- 用户上传同名不同内容
- 无法可靠定位 `duplicate_document_id`
- 找到的既有记录没有可用 `file_path`
- Weaviate upload 入口
- direct processing 入口

## 7. 修改后验证结果

静态检查：

- `python -m py_compile` 通过
- `python manage.py makemigrations --check --dry-run pdf_processor` 通过
  - 输出：`No changes detected in app 'pdf_processor'`

修改后 smoke 复跑结果：

- `pass=24`
- `fail=0`
- `error=0`

本轮新增和重点关注的检查全部通过：

1. `user_different_name_same_content_pending_action`
2. `duplicate_hit_pending_reviews_visibility`
3. `duplicate_hit_approve_isolated`
4. `duplicate_hit_reject_isolated`
5. `shared_file_path_download_compatibility`

## 8. 原有 smoke 是否仍然通过

仍然全部通过。

包括：

- 用户上传全新 PDF
- 用户上传同名 guard 场景
- direct processing smoke
- Weaviate upload smoke
- Weaviate 试点 duplicate hit 语义
- 旧路径兼容
- `reprocess_pdfs.py` / `sync_pdfs.py` 目录来源检查
- 既有识别型 duplicate logging smoke

这说明本轮受控变化没有扩散到其他入口。

## 9. 是否发现功能失效或行为超出预期变化

未发现功能失效。

本轮明确发生的受控变化只有一类：

- 用户上传入口中的“不同名同内容”场景
  - 从“重复落盘 + 新建 pending 记录”
  - 变为“复用已有物理内容 + 新建 pending 记录”

未发生的变化：

- 前端接口结构未改
- `message` 语义未改
- 审核通过/拒绝逻辑未重写
- Weaviate 试点语义未改
- direct processing 未改
- `sync_pdfs.py` / `reprocess_pdfs.py` 未改职责
- 审核通过自动索引语义未改

## 10. 当前仍未解决的点

1. 这是短期过渡方案，`PDFDocument` 仍同时承载内容记录和审核动作记录
2. 历史 `sha1` 为空的记录仍不会稳定参与 duplicate hit
3. 本轮没有补任何历史 `duplicate_of` 回填
4. 本轮没有处理历史重复文件清理
5. 本轮没有把相同策略扩展到 Weaviate 之外的其他入口
6. 本轮没有设计前端如何显式展示“该 pending 项复用了已有内容”
7. 本轮默认 duplicate-hit 新动作仍统一进入 `pending`
   - 不继承历史 `approved/rejected` 结论

## 11. 下一步是否适合继续评估更长期的 UploadRequest / ReviewRequest 模型

适合。

当前状态已经把用户上传入口收口到了一个可回滚、可验证的过渡实现：

- 不需要前端配合
- 不重写审核流
- 不做历史清理

在这个前提下，下一步适合做的是“评估更长期的 `UploadRequest / ReviewRequest` 模型设计”，而不是立刻继续扩大行为改造。

更长期模型评估可以重点回答：

- 是否要把审核动作从 `PDFDocument` 中真正拆出
- 是否要让前端能区分“内容主记录”和“duplicate-hit 审核动作”
- 是否要在未来把用户上传入口也升级到更清晰的动作对象语义

## 修改前后对比摘要

修改前：

- `pass=22 / fail=2 / error=0`
- 缺口是 `duplicate_of` 不存在，以及用户上传“不同名同内容”仍重复落盘

修改后：

- `pass=24 / fail=0 / error=0`
- 用户上传入口已完成最小 duplicate-hit 过渡实现

## 结论

本轮目标已完成：

- 已为 `PDFDocument` 增加最小自关联字段 `duplicate_of`
- 已在用户上传入口实现“不同名同内容不重复落盘，但仍创建新的 pending 审核动作”
- 前端无感知
- 原有 smoke 未回归
- 当前可以先停在这个过渡方案，再单独评估长期的 `UploadRequest / ReviewRequest` 模型
