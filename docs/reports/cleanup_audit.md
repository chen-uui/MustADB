# 安全清理审计报告

## 审计范围与约束

- 审计时间：2026-03-14
- 工作区：`D:\workspace\123`
- 本次仅执行只读扫描、引用分析和报告生成
- 未删除、移动、重命名或修改任何现有文件/目录

## 项目结构摘要

### 根目录概览

- 总文件数约 `79,042`
- 总体量约 `4.25 GB`
- 主要顶层结构：
  - `.venv/`：本地 Python 虚拟环境，约 `2.01 GB`
  - `ccc/`：主项目目录，约 `2.22 GB`
  - `.serena/`：工具元数据与缓存，约 `8.55 MB`
  - `docs/`：文档目录
  - `logs/`：根级日志目录
  - `manage.py`：仓库级 Django 代理入口

### 主项目 `ccc/astrobiology/`

- `backend/`：Django 后端、RAG/抽取/评测逻辑，约 `998.13 MB`
  - `models/`：本地模型资产，约 `768.83 MB`
  - `media/`：运行期上传文件，约 `145.08 MB`
  - `pdf_processor/`：抽取与评测逻辑，约 `76.51 MB`
  - `runs/`：实验/评测输出目录，约 `2.87 MB`
  - `evaluation/`：gold set / qrels /评测种子
  - `logs/`：后端日志目录，约 `3.89 MB`
- `astro_frontend/`：Vue + Vite 前端，约 `136.98 MB`
  - `node_modules/`：依赖目录，约 `127.38 MB`
  - `dist/`：构建产物，约 `4.76 MB`
  - `src/`：源码目录，约 `4.74 MB`
- `data/`：数据与向量库持久化，约 `1.09 GB`
  - `pdfs/`：PDF 文库，约 `832.27 MB`
  - `weaviate_data/`：Weaviate 持久化数据，约 `254.62 MB`
- `checkpoints/`：抽取任务检查点根目录
- `.env`、`docker-compose.yml`、`start_astrobiology_system.py`：运行关键入口

## 候选项清单

说明：

- “可能引用”列优先写明是否能从代码、配置、Docker、脚本、文档、环境变量中找到直接迹象
- 若涉及 `evaluation/`、`data/`、`migrations/`、`management/commands/`、`.env`、锁文件、实验结果、模型资产、上传文件、数据库/索引文件，一律保守处理

### 一、低风险缓存类

| 路径 | 类型 | 为什么怀疑可能无用 | 风险 | 是否可能被引用 | 建议 |
| --- | --- | --- | --- | --- | --- |
| `D:\workspace\123\.venv\Lib\site-packages\**\__pycache__\` | Python 字节码缓存目录 | 共约 `2,446` 个目录、`17,843` 个 `.pyc` 文件、约 `197.19 MB`；属于解释器派生缓存，可重建 | 低 | 间接依附于活跃 `.venv`，但并非业务必需数据 | 可立即删除 |
| `D:\workspace\123\ccc\astrobiology\backend\**\__pycache__\` | Python 字节码缓存目录 | 共 `16` 个目录、`178` 个文件、约 `1.26 MB`；均为运行后生成 | 低 | 仅被 Python 运行时再生成，不见业务直接引用 | 可立即删除 |
| `D:\workspace\123\ccc\astrobiology\backend\pdf_processor\.mypy_cache\` | 类型检查缓存目录 | 约 `1,853` 个缓存文件、`73.76 MB`；典型 `mypy` 缓存 | 低 | 未发现代码/配置直接依赖该目录 | 可立即删除 |
| `D:\workspace\123\ccc\astrobiology\astro_frontend\node_modules\.vite\` | 前端构建缓存目录 | 约 `8.85 MB`；Vite 预构建缓存 | 低 | 被 Vite 开发流程再生成，但非部署资产 | 可立即删除 |

### 二、需要人工确认

| 路径 | 类型 | 为什么怀疑可能无用 | 风险 | 是否可能被引用 | 建议 |
| --- | --- | --- | --- | --- | --- |
| `D:\workspace\123\.serena\cache\` | 工具缓存目录 | 仅 1 个符号缓存文件，约 `8.49 MB`；明显是外部工具缓存 | 中 | 可能被 Serena 工具重新使用，但不属于业务代码依赖 | 需要人工确认 |
| `D:\workspace\123\ccc\astrobiology\.serena\cache\` | 工具缓存目录 | 仅 1 个符号缓存文件，约 `2.91 MB`；同属工具缓存 | 中 | 可能被 Serena 工具重新使用，但不属于业务代码依赖 | 需要人工确认 |
| `D:\workspace\123\ccc\astrobiology\astro_frontend\dist\` | 前端构建产物目录 | 已在 `.gitignore` 忽略，且 `package.json` 使用 `vite build` 生成；`dist/assets/mars_image_1-d94f4c3f.png` 与源码图片重复 | 中 | `vite.config.js` 明确输出到 `dist`；可能被手工预览或静态发布流程使用 | 需要人工确认 |
| `D:\workspace\123\ccc\astrobiology\astro_frontend\node_modules\` | 前端依赖目录 | 约 `127.38 MB`；可由锁文件重装 | 中 | 被 `package.json` / `package-lock.json` / Vite 开发流程依赖 | 需要人工确认 |
| `D:\workspace\123\logs\astrobiology.log` | 根级日志文件 | 约 `13.58 KB`；未发现后端日志配置写入该路径，更像旧日志残留 | 中 | 未发现代码直接引用根级 `logs/astrobiology.log` | 需要人工确认 |
| `D:\workspace\123\ccc\astrobiology\logs\astrobiology.log` | 项目根级日志文件 | 空文件；与后端真实日志目录 `backend/logs/` 不一致 | 中 | 未发现代码直接引用该路径 | 需要人工确认 |
| `D:\workspace\123\ccc\astrobiology\backend\logs\astrobiology.log` | 后端运行日志 | 约 `3.66 MB`；内容是错误栈、运行轨迹和任务信息，具有明显日志特征 | 中 | `backend/logging_config.py` 与 `backend/config/settings.py` 直接写该目录 | 需要人工确认 |
| `D:\workspace\123\ccc\astrobiology\backend\logs\bench_log.jsonl` | 基准测试日志 | 约 `244 KB`；基准命令产生的 JSONL 运行记录 | 中 | `pdf_processor/bench_logging.py` 和 `bench_*` 管理命令直接写该文件 | 需要人工确认 |
| `D:\workspace\123\ccc\astrobiology\backend\models\cache\` | 模型缓存目录 | 约 `175.13 MB`；其中两组大文件与 `backend/models/` 下正式模型完全重复：`all-MiniLM-L6-v2/model.safetensors` 与 `cross-encoder-ms-marco-MiniLM-L-6-v2/model.safetensors` | 中 | 未发现代码直接引用 `models/cache/`；实际加载日志指向 `backend/models/all-MiniLM-L6-v2` 与 `backend/models/cross-encoder/ms-marco-MiniLM-L-6-v2` | 需要人工确认 |
| `D:\workspace\123\ccc\astrobiology\backend\uploads\` | 空目录 | 目录为空；看起来像旧版上传目录 | 中 | `backend/config/settings.py` 中 `STORAGE_CONFIG['UPLOAD_DIR']` 会确保该目录存在，属于历史兼容位点 | 需要人工确认 |
| `D:\workspace\123\ccc\astrobiology\backend\staticfiles\` | 空目录 | 目录为空；典型 `collectstatic` 输出目录 | 中 | `backend/config/django_settings.py` 配置了 `STATIC_ROOT = BASE_DIR / 'staticfiles'` | 需要人工确认 |
| `D:\workspace\123\ccc\astrobiology\backend\pdf_processor\management\commands\bench_*` | 疑似实验/基准脚本 | 命名明显偏 benchmark/smoke，用途偏一次性测试或基准 | 高 | 作为 Django `management/commands/`，可被 `manage.py` 直接调用 | 需要人工确认 |
| `D:\workspace\123\ccc\astrobiology\backend\pdf_processor\management\commands\test_*` | 疑似实验/测试脚本 | 命名明显偏测试/诊断；可能是历史实验命令 | 高 | 作为 Django `management/commands/`，可被 `manage.py` 直接调用 | 需要人工确认 |
| `D:\workspace\123\ccc\astrobiology\backend\pdf_processor\management\commands\debug_incremental_merge.py` | 疑似调试脚本 | 文件名带 `debug_`，疑似一次性调试入口 | 高 | 属于 `management/commands/` 保护区，仍可能被人工调用 | 需要人工确认 |
| `D:\workspace\123\scripts\` | 空脚本目录 | 目录为空，表面看像遗留结构 | 高 | `scripts/` 被用户规则明确列为保护区 | 建议保留 |
| `D:\workspace\123\ccc\astrobiology\backend\scripts\` | 空脚本目录 | 目录为空，表面看像遗留结构 | 高 | `scripts/` 被用户规则明确列为保护区 | 建议保留 |
| `D:\workspace\123\ccc\astrobiology\astro_frontend\scripts\` | 空脚本目录 | 目录为空，表面看像遗留结构 | 高 | `scripts/` 被用户规则明确列为保护区 | 建议保留 |
| `D:\workspace\123\.trae\documents\` | 空工具目录 | 目录为空，看起来是 IDE/工具残留 | 中 | 未发现业务代码引用；但可能被外部工具使用 | 需要人工确认 |

### 三、高风险对象，建议保留

| 路径 | 类型 | 为什么怀疑可能无用 | 风险 | 是否可能被引用 | 建议 |
| --- | --- | --- | --- | --- | --- |
| `D:\workspace\123\.venv\` | Python 虚拟环境目录 | 体量很大，约 `2.01 GB`，从“清理空间”角度像候选项 | 高 | `.vscode/settings.json` 与 `backend/start_backend.bat` 直接引用 `.venv`；当前工作区也依赖该环境 | 建议保留 |
| `D:\workspace\123\ccc\astrobiology\backend\media\uploads\` | 运行期上传 PDF 目录 | 约 `145.08 MB`；存在 `28` 个完全相同的 PDF 上传副本，且其中一组与 `data/pdfs/Ceres- OrganicRich Sites of Exogenic Origin-.pdf` 完全重复 | 高 | `views_user_upload.py` 和 `views/direct_processing_views.py` 直接写入 `MEDIA_ROOT/uploads` | 需要人工确认 |
| `D:\workspace\123\ccc\astrobiology\backend\runs\` | 实验/评测输出目录 | 命名包含 `gold_`、`eval`、`review`、`ablation`、`smoke`，显然属于实验复现和历史对比产物 | 高 | 运行结果之间互相引用；`summary.md/json` 中直接引用 `evaluation/` 与其他 `runs/` 文件 | 建议保留 |
| `D:\workspace\123\ccc\astrobiology\checkpoints\extraction_tasks\` | 检查点目录 | 目前为空，表面像可删空目录 | 高 | `task_checkpoint_manager.py`、恢复接口和多条管理命令直接依赖该路径 | 建议保留 |
| `D:\workspace\123\ccc\astrobiology\data\pdfs\` | PDF 数据文库 | 约 `832.27 MB`，是明显的大目录 | 高 | `backend/config/django_settings.py` 将其设为 `PDF_STORAGE_PATH`；日志也直接读取该路径 | 建议保留 |
| `D:\workspace\123\ccc\astrobiology\data\weaviate_data\` | 向量库持久化目录 | 约 `254.62 MB`，包含 `.db`、LSM 段文件、HNSW 索引等持久化内容 | 高 | `docker-compose.yml` 将其挂载到 Weaviate 的 `/var/lib/weaviate` | 建议保留 |
| `D:\workspace\123\ccc\astrobiology\backend\models\all-mpnet-base-v2\model.safetensors` | 大模型文件 | 单文件约 `417.68 MB`，看起来很大 | 高 | `settings.py` / `django_settings.py` 默认 embedding 模型即 `all-mpnet-base-v2` | 建议保留 |
| `D:\workspace\123\ccc\astrobiology\backend\models\all-MiniLM-L6-v2\` | 本地 embedding 模型目录 | 与 `all-mpnet-base-v2` 并存，容易被误判为旧模型 | 高 | `embedding_service.py` 会从 `backend/models/<model_name>` 加载本地模型；运行日志显示该目录正在使用 | 建议保留 |
| `D:\workspace\123\ccc\astrobiology\backend\models\cross-encoder\ms-marco-MiniLM-L-6-v2\` | 本地 reranker 模型目录 | 看起来像另一套模型副本 | 高 | `reranker_service.py` 会从 `backend/models/cross-encoder/ms-marco-MiniLM-L-6-v2` 加载；运行日志显示该目录正在使用 | 建议保留 |
| `D:\workspace\123\ccc\astrobiology\backend\evaluation\` | 评测/gold seed 目录 | 目录小，但全部是 gold set / qrels / scope probe / xlsx 等评测核心文件 | 高 | 明确属于用户定义保护区；`runs/` 中多份结果文件直接引用这里的数据 | 建议保留 |

## 审计结论

### 真正可“立即清理”的范围非常小

- 低风险且最像纯缓存的对象，主要只有：
  - Python `__pycache__`
  - `pdf_processor/.mypy_cache`
  - `astro_frontend/node_modules/.vite`

### 占空间大的对象大多不适合激进清理

- 大头空间主要来自：
  - `.venv/`
  - `data/pdfs/`
  - `data/weaviate_data/`
  - `backend/models/`
  - `backend/media/uploads/`
- 这些目录要么被代码/配置直接引用，要么属于实验、向量库、模型资产、上传文件、gold set 相关历史产物

### 当前最值得人工复核的点

- `backend/models/cache/` 是否可以去掉重复模型副本
- `backend/media/uploads/` 中 `28` 个完全相同的 PDF 上传副本是否只是重复导入
- `backend/logs/`、根级 `logs/`、项目根级 `logs/` 是否需要保留日志历史
- `astro_frontend/dist/` 是否仅为本地构建产物，而非手工部署快照
- `management/commands/` 下 `bench_* / test_* / debug_*` 是否仍承担实验复现职责
