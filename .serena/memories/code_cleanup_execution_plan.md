# 代码清理执行计划

## 发现的主要重复代码问题

### 1. 重复的ViewSet类
- `PDFQAViewSet` 在以下文件中重复定义：
  - `views_qa.py` (第34行)
  - `views_qa_backup.py` (第34行) - 备份文件
  - `views_qa_extraction.py` (第38行)

### 2. 重复的服务函数
- `get_qa_service()` 函数在以下文件中重复：
  - `rag_service.py` (第47行)
  - `views_qa.py` (第22行)
  - `views_qa_backup.py` (第22行)
  - `views_qa_extraction.py` (第28行)

### 3. 重复的流式响应方法
- `_stream_response()` 方法在以下文件中重复：
  - `views_qa.py` (第38行)
  - `views_qa_backup.py` (第38行)
  - `views_qa_extraction.py` (第42行)

### 4. 其他重复函数（出现2次的函数）
- get_recovery_status, quick_health, metrics, change_password
- update_profile, logout, health_check, status
- ask_optimized, qa_demo, process_async, get_extraction_tasks
- preview_search, get_extraction_progress, clear_cache
- 等多个函数

## 清理策略

### 阶段1：移除明显的备份文件
1. **删除 `views_qa_backup.py`**
   - 这是一个备份文件，包含与 `views_qa.py` 完全相同的代码
   - 安全删除，不会影响系统功能

### 阶段2：合并重复的ViewSet
1. **保留 `views_qa_extraction.py` 中的 `PDFQAViewSet`**
   - 这个文件看起来是更完整的实现，包含了问答和数据提取功能
2. **重构 `views_qa.py`**
   - 移除重复的 `PDFQAViewSet` 类
   - 保留其他独特的功能（如果有）

### 阶段3：统一服务函数
1. **保留 `rag_service.py` 中的 `get_qa_service()`**
   - 这是服务层的正确位置
2. **从其他文件中移除重复的 `get_qa_service()` 函数**
   - 更新导入语句以使用统一的服务函数

### 阶段4：清理空文件和小文件
1. **删除空的 `__init__.py` 文件**（如果不需要）
2. **检查并清理其他小于100字节的文件**

## 执行顺序
1. 首先删除备份文件（最安全）
2. 然后合并重复的类和函数
3. 最后清理空文件和更新导入

## 风险评估
- **低风险**：删除备份文件
- **中风险**：合并ViewSet类（需要仔细检查功能差异）
- **高风险**：修改服务函数导入（需要更新所有引用）

## 测试计划
每个阶段完成后都需要：
1. 检查语法错误
2. 验证导入是否正确
3. 测试关键API端点
4. 确认系统启动正常