# 内容哈希去重 Phase 2B-2 Weaviate 试点报告

## 1. 修改前基线结果

### 验证脚本

- `D:\workspace\123\ccc\astrobiology\backend\tests\upload_storage_smoke_check.py`

### 修改前汇总

- `pass=15`
- `fail=2`
- `error=0`

### 修改前新增 Weaviate 试点检查结果

| 检查项 | 修改前行为 | 结果 |
| --- | --- | --- |
| `weaviate_same_name_same_content_existing` | 同名同内容时直接返回现有记录 | 通过 |
| `weaviate_different_name_same_content_duplicate_hit` | 不同名但同内容时仍会落盘、建新记录、触发处理 | 失败 |
| `weaviate_same_name_different_content_keeps_filename_guard` | 同名不同内容时仍按原 filename guard 谨慎跳过 | 通过 |
| `user_then_weaviate_same_content_duplicate_hit` | 用户上传后，再从 Weaviate 上传同内容 PDF，仍会落盘、建新记录、触发处理 | 失败 |

### 修改前明确的行为事实

- `weaviate_views.py` 的 `upload` 原先只按 `filename` 检查“是否已存在”
- 即使 `duplicate_inspection` 已识别出 `duplicate_detected=True`
- 只要文件名不同，仍会：
  - 保存新文件
  - 创建新的 `PDFDocument`
  - 启动异步处理

这正是本轮试点要收口的最小分支。

## 2. 实际修改了哪些文件

- `D:\workspace\123\ccc\astrobiology\backend\pdf_processor\weaviate_views.py`
- `D:\workspace\123\ccc\astrobiology\backend\tests\upload_storage_smoke_check.py`

本轮没有修改：

- `views_user_upload.py`
- `views/direct_processing_views.py`
- `sync_pdfs.py`
- `reprocess_pdfs.py`
- 数据库结构
- 前端

## 3. Weaviate upload 原先的重复处理行为是什么

### 原先的行为

- 先计算/记录内容哈希识别结果
- 但真正阻断只依赖：
  - `existing_doc = self._filter_documents(filename=pdf_file.name).first()`

因此：

- 同名同内容：会跳过上传
- 同名不同内容：也会跳过上传
- 不同名同内容：**不会跳过**
- 跨入口同内容但文件名不同：**不会跳过**

### 原先的结果

- Weaviate 目录里会新增重复落盘
- 数据库里会新增重复 `PDFDocument`
- 后续会重复触发异步处理

## 4. 现在的阻断式去重行为是什么

### 本轮最小策略

只在 `weaviate_views.py` 的 `upload` 入口增加了这一分支：

- 如果：
  - `duplicate_inspection.duplicate_detected == True`
  - 且 `duplicate_document_id` 可解析到现有 `PDFDocument`
  - 且没有先被“同名 guard”分支处理
- 那么：
  - 不再调用 `save_uploaded_file`
  - 不再创建新的 `PDFDocument`
  - 不再触发新的异步处理
  - 直接返回现有记录语义

### 当前返回语义

本轮保持了与“文件已存在”分支相同的结构级兼容：

- `success`
- `message`
- `document_id`
- `filename`
- `existing`
- `title`
- `upload_date`

唯一受控变化是：

- 对“不同名但同内容”场景，`message` 现在是：
  - `文件内容已存在，跳过上传`

没有新增强制依赖的新字段，也没有修改路由、HTTP method 或 payload 结构。

## 5. 哪些情况会阻断，哪些情况不会阻断

### 会阻断

- Weaviate 上传时：
  - 文件名不同
  - 内容哈希与现有 `PDFDocument.sha1` 命中
  - 且能拿到对应现有 `PDFDocument`

示例：

- `existing.pdf` 已存在
- 现在上传 `new-name.pdf`
- 内容完全相同
- 结果：返回现有记录，不再重复落盘/建记录/触发处理

### 不会阻断

- 同名 guard 命中的场景
  - 仍走原先“文件已存在，跳过上传”
- 同名不同内容
  - 仍保持原来的谨慎 filename guard 行为
  - 不把它误判为内容重复
- 无法可靠定位 `duplicate_document_id` 对应现有文档
  - 保持原行为，不阻断
- 所有非 Weaviate 上传入口
  - 用户上传入口不变
  - direct processing 不变

## 6. 修改后验证结果

### 静态导入检查

- 执行：`python -m py_compile`
- 结果：通过
- 覆盖文件：
  - `weaviate_views.py`
  - `upload_storage_smoke_check.py`

### 修改后 smoke 复跑结果

- `pass=17`
- `fail=0`
- `error=0`

### Weaviate 试点行为对比

| 检查项 | 修改前 | 修改后 | 结论 |
| --- | --- | --- | --- |
| `weaviate_same_name_same_content_existing` | 200 existing | 200 existing | 行为保持一致 |
| `weaviate_different_name_same_content_duplicate_hit` | 201，新建记录并处理 | 200，返回 existing，不落盘不建记录 | 受控变化 |
| `weaviate_same_name_different_content_keeps_filename_guard` | 200 existing | 200 existing | 行为保持一致 |
| `user_then_weaviate_same_content_duplicate_hit` | 201，新建记录并处理 | 200，返回 existing，不落盘不建记录 | 受控变化 |

## 7. 原有 smoke 是否仍然通过

- 仍然全部通过。

包括：

- 用户上传 smoke
- 跨入口重复上传（同名）smoke
- direct processing smoke
- 旧路径兼容
- Phase 2B-1 的识别型 smoke
- `reprocess_pdfs.py` 目录来源检查
- `sync_pdfs.py` 目录来源检查与 smoke
- Weaviate 正常新上传 smoke

## 8. 是否发现功能失效或行为超出预期变化

- 当前 smoke 范围内未发现功能失效。
- 未发现变化超出 Weaviate upload 入口。

### 本轮明确发生的受控变化

只有一类：

- **Weaviate upload 对“不同名但同内容”的上传，改为返回 existing 语义，而不是继续新增记录**

这项变化符合本轮目标，且限定在单入口试点。

## 9. 当前仍未解决的点

- 用户上传入口仍不会阻断同内容重复
- direct processing 仍不会阻断同内容重复
- 历史 `sha1` 为空的 `PDFDocument` 仍不能稳定参与重复命中
- `sync_pdfs.py` / `reprocess_pdfs.py` 仍未纳入阻断式策略
- 同名不同内容仍只能依赖现有 filename guard，尚未设计更细的产品语义

## 10. 下一步是否适合把这套策略扩展到用户上传入口，还是应该先停在 Weaviate 试点

### 当前建议

- **先停在 Weaviate 试点，不建议立即扩到用户上传入口。**

### 原因

- 用户上传入口带有待审核语义
- 一旦把“同内容重复命中”扩展到用户上传：
  - 需要重新明确重复上传是否仍应保留一条新的待审核记录
  - 还要确认前端和审核人员如何感知“重复但未新建记录”
- 这些都已经超出本轮“单入口最小试点”的安全边界

### 更稳的下一步

1. 先观察/验证 Weaviate 试点是否满足预期
2. 再单独设计用户上传入口的重复命中语义
3. 在没有明确产品语义前，不要把相同策略直接复制到用户上传入口

## 结论

- 本轮已在 `weaviate_views.py` 的 upload 入口完成单入口、最小、可验证的阻断式去重试点。
- 受控变化仅限：
  - 不同名但同内容时，不再重复落盘、不再重复建记录、不再重复触发处理。
- 其他入口与主链路 smoke 均未回归。
- 当前建议先停在 Weaviate 试点，不要立刻扩到用户上传入口。
