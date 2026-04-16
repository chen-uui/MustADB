# 清理计划（仅审计，不执行）

## 可立即删除

仅限低风险缓存类：

- `D:\workspace\123\.venv\Lib\site-packages\**\__pycache__\`
  - 原因：解释器派生缓存，可自动重建
- `D:\workspace\123\ccc\astrobiology\backend\**\__pycache__\`
  - 原因：解释器派生缓存，可自动重建
- `D:\workspace\123\ccc\astrobiology\backend\pdf_processor\.mypy_cache\`
  - 原因：类型检查缓存，非运行必需
- `D:\workspace\123\ccc\astrobiology\astro_frontend\node_modules\.vite\`
  - 原因：Vite 预构建缓存，开发时可重建

## 需要人工确认

- `D:\workspace\123\.serena\cache\`
  - 工具缓存，不属于业务资产，但可能影响 Serena 工具体验
- `D:\workspace\123\ccc\astrobiology\.serena\cache\`
  - 同上
- `D:\workspace\123\ccc\astrobiology\astro_frontend\dist\`
  - 构建产物，通常可重建，但可能被当作手工部署快照
- `D:\workspace\123\ccc\astrobiology\astro_frontend\node_modules\`
  - 可重装，但会影响当前前端运行环境
- `D:\workspace\123\logs\astrobiology.log`
  - 更像旧日志残留，但建议先确认是否还有人工排障价值
- `D:\workspace\123\ccc\astrobiology\logs\astrobiology.log`
  - 空日志文件，疑似遗留
- `D:\workspace\123\ccc\astrobiology\backend\logs\astrobiology.log`
  - 真实运行日志，可能仍需保留排障历史
- `D:\workspace\123\ccc\astrobiology\backend\logs\bench_log.jsonl`
  - benchmark 结果日志，可能用于性能对比
- `D:\workspace\123\ccc\astrobiology\backend\models\cache\`
  - 与正式模型目录存在精确重复，优先人工确认是否确属冗余缓存
- `D:\workspace\123\ccc\astrobiology\backend\media\uploads\`
  - 存在重复上传 PDF，但属于运行数据，不宜自动处理
- `D:\workspace\123\ccc\astrobiology\backend\uploads\`
  - 空目录，像旧版上传位点，但设置文件仍会创建它
- `D:\workspace\123\ccc\astrobiology\backend\staticfiles\`
  - 空目录，像生成目录，但 Django `STATIC_ROOT` 指向此处
- `D:\workspace\123\.trae\documents\`
  - 空工具目录，业务无直接引用
- `D:\workspace\123\ccc\astrobiology\backend\pdf_processor\management\commands\bench_*`
  - 名称像实验命令，但仍属管理命令保护区
- `D:\workspace\123\ccc\astrobiology\backend\pdf_processor\management\commands\test_*`
  - 名称像测试命令，但可能承担历史复现实验
- `D:\workspace\123\ccc\astrobiology\backend\pdf_processor\management\commands\debug_incremental_merge.py`
  - 名称像调试脚本，但仍可能被人工调用

## 建议保留

- `D:\workspace\123\.venv\`
  - 当前环境直接依赖，`.vscode/settings.json` 与 `backend/start_backend.bat` 都指向它
- `D:\workspace\123\ccc\astrobiology\data\pdfs\`
  - 文库数据目录，后端设置直接引用
- `D:\workspace\123\ccc\astrobiology\data\weaviate_data\`
  - Weaviate 持久化数据，Docker 直接挂载
- `D:\workspace\123\ccc\astrobiology\backend\models\all-mpnet-base-v2\`
  - 当前 embedding 模型资产
- `D:\workspace\123\ccc\astrobiology\backend\models\all-MiniLM-L6-v2\`
  - 当前运行日志显示实际加载过
- `D:\workspace\123\ccc\astrobiology\backend\models\cross-encoder\ms-marco-MiniLM-L-6-v2\`
  - 当前 reranker 实际加载路径
- `D:\workspace\123\ccc\astrobiology\backend\evaluation\`
  - gold set / qrels / scope probe，明确保护区
- `D:\workspace\123\ccc\astrobiology\backend\runs\`
  - 实验、评测、历史对比结果，明显属于复现资产
- `D:\workspace\123\ccc\astrobiology\checkpoints\extraction_tasks\`
  - 检查点与恢复链路目录，代码直接依赖
- `D:\workspace\123\scripts\`
  - 用户规则明确保护 `scripts/`
- `D:\workspace\123\ccc\astrobiology\backend\scripts\`
  - 用户规则明确保护 `scripts/`
- `D:\workspace\123\ccc\astrobiology\astro_frontend\scripts\`
  - 用户规则明确保护 `scripts/`

## 后续可优化的目录结构建议

- 统一运行期产物目录。
  - 当前日志、上传、静态产物分散在 `logs/`、`ccc/astrobiology/logs/`、`backend/logs/`、`backend/uploads/`、`backend/media/uploads/`、`backend/staticfiles/`
  - 建议未来通过配置统一到单一 `runtime/` 或 `var/` 根目录
- 明确区分“源数据 / 持久化库 / 实验输出 / 缓存”。
  - `data/pdfs/`、`data/weaviate_data/`、`backend/runs/`、`backend/models/cache/` 当前语义混杂
  - 建议后续补一份目录约定文档和保留策略
- 给实验输出设置命名规范和保留策略。
  - `backend/runs/` 中大量 `gold_* / smoke / eval / review` 目录可读性尚可，但缺少归档规则
  - 建议后续按批次、用途、是否已纳入论文/评测结论打标签
- 在 `.gitignore` / 文档中补充缓存说明。
  - 前端已忽略 `node_modules/`、`dist/`
  - 后端可在文档中明确 `__pycache__`、`.mypy_cache`、日志目录、benchmark 日志、模型缓存副本的处理边界
