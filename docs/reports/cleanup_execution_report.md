# 第一轮安全清理执行报告

## 执行概况

- 执行时间：2026-03-14
- 执行分支：`codex/chore-safe-cache-cleanup`
- 执行范围：仅处理 `cleanup_plan.md` 中“可立即删除”的低风险缓存类
- 未处理任何人工确认类对象
- 未触碰 `protected_paths.md` 中列出的高风险保护区

## 删除清单

### 1. `.venv` 下 Python 缓存目录

- 删除范围：`D:\workspace\123\.venv\Lib\site-packages\**\__pycache__\`
- 实际删除目录数：`2446`
- 删除前体量约：`197.19 MB`
- 删除后剩余：`0`

代表性已删除路径示例：

- `D:\workspace\123\.venv\Lib\site-packages\__pycache__`
- `D:\workspace\123\.venv\Lib\site-packages\aiohttp\__pycache__`
- `D:\workspace\123\.venv\Lib\site-packages\anyio\__pycache__`
- `D:\workspace\123\.venv\Lib\site-packages\asgiref\__pycache__`
- `D:\workspace\123\.venv\Lib\site-packages\django\__pycache__`

### 2. `backend` 下 Python 缓存目录

- 删除范围：`D:\workspace\123\ccc\astrobiology\backend\**\__pycache__\`
- 实际删除目录数：`16`
- 删除前体量约：`1.26 MB`
- 删除后剩余：`0`

实际删除路径：

- `D:\workspace\123\ccc\astrobiology\backend\__pycache__`
- `D:\workspace\123\ccc\astrobiology\backend\astro_data\__pycache__`
- `D:\workspace\123\ccc\astrobiology\backend\astro_data\migrations\__pycache__`
- `D:\workspace\123\ccc\astrobiology\backend\config\__pycache__`
- `D:\workspace\123\ccc\astrobiology\backend\meteorite_search\__pycache__`
- `D:\workspace\123\ccc\astrobiology\backend\meteorite_search\management\__pycache__`
- `D:\workspace\123\ccc\astrobiology\backend\meteorite_search\management\commands\__pycache__`
- `D:\workspace\123\ccc\astrobiology\backend\meteorite_search\migrations\__pycache__`
- `D:\workspace\123\ccc\astrobiology\backend\pdf_processor\__pycache__`
- `D:\workspace\123\ccc\astrobiology\backend\pdf_processor\direct_processing\__pycache__`
- `D:\workspace\123\ccc\astrobiology\backend\pdf_processor\management\__pycache__`
- `D:\workspace\123\ccc\astrobiology\backend\pdf_processor\management\commands\__pycache__`
- `D:\workspace\123\ccc\astrobiology\backend\pdf_processor\migrations\__pycache__`
- `D:\workspace\123\ccc\astrobiology\backend\pdf_processor\tests\__pycache__`
- `D:\workspace\123\ccc\astrobiology\backend\pdf_processor\urls\__pycache__`
- `D:\workspace\123\ccc\astrobiology\backend\pdf_processor\views\__pycache__`

### 3. `pdf_processor` 类型检查缓存

- 实际删除路径：`D:\workspace\123\ccc\astrobiology\backend\pdf_processor\.mypy_cache`
- 删除前体量约：`73.76 MB`
- 删除后状态：不存在

### 4. 前端 Vite 预构建缓存

- 实际删除路径：`D:\workspace\123\ccc\astrobiology\astro_frontend\node_modules\.vite`
- 删除前体量约：`8.85 MB`
- 删除后状态：不存在

## 空间释放估算

- 删除前目标缓存总量约：`281.06 MB`
  - `.venv` 下 `__pycache__`：`197.19 MB`
  - `backend` 下 `__pycache__`：`1.26 MB`
  - `.mypy_cache`：`73.76 MB`
  - `.vite`：`8.85 MB`
- 删除后目标缓存剩余：`0`
- 本轮大致释放空间：`约 281.06 MB`

说明：

- 这是按删除前文件大小汇总的近似值
- Windows 文件系统实际回收空间可能有少量偏差

## 跳过清单

本轮没有额外扩大处理范围；以下对象全部按规则跳过，未做任何处理：

- `.venv/` 根目录本体
- `D:\workspace\123\ccc\astrobiology\data\`
- `D:\workspace\123\ccc\astrobiology\data\pdfs\`
- `D:\workspace\123\ccc\astrobiology\data\weaviate_data\`
- `D:\workspace\123\ccc\astrobiology\backend\models\`
- `D:\workspace\123\ccc\astrobiology\backend\models\cache\`
- `D:\workspace\123\ccc\astrobiology\backend\media\uploads\`
- `D:\workspace\123\ccc\astrobiology\backend\runs\`
- `D:\workspace\123\ccc\astrobiology\backend\evaluation\`
- `D:\workspace\123\ccc\astrobiology\checkpoints\`
- `D:\workspace\123\ccc\astrobiology\backend\pdf_processor\management\commands\`
- `D:\workspace\123\ccc\astrobiology\backend\meteorite_search\management\commands\`
- 所有 `csv / json / xlsx / parquet / pkl / pt / bin / ckpt / faiss / db` 文件

不满足条件而被跳过的原计划对象：

- 无

## 轻量验证

### 目标缓存状态

- `.venv\Lib\site-packages\` 下 `__pycache__` 剩余数：`0`
- `backend\` 下 `__pycache__` 剩余数：`0`
- `backend\pdf_processor\.mypy_cache`：不存在
- `astro_frontend\node_modules\.vite`：不存在

### 关键目录仍存在

以下路径已核对存在：

- `D:\workspace\123\.venv`
- `D:\workspace\123\ccc\astrobiology\backend`
- `D:\workspace\123\ccc\astrobiology\data`
- `D:\workspace\123\ccc\astrobiology\data\pdfs`
- `D:\workspace\123\ccc\astrobiology\data\weaviate_data`
- `D:\workspace\123\ccc\astrobiology\backend\models`
- `D:\workspace\123\ccc\astrobiology\backend\models\cache`
- `D:\workspace\123\ccc\astrobiology\backend\media\uploads`
- `D:\workspace\123\ccc\astrobiology\backend\runs`
- `D:\workspace\123\ccc\astrobiology\backend\evaluation`
- `D:\workspace\123\ccc\astrobiology\checkpoints`
- `D:\workspace\123\ccc\astrobiology\backend\pdf_processor\management\commands`
- `D:\workspace\123\ccc\astrobiology\backend\meteorite_search\management\commands`

### 未删除源码、配置、模型和数据文件

以下关键文件已核对存在：

- `D:\workspace\123\manage.py`
- `D:\workspace\123\ccc\astrobiology\backend\manage.py`
- `D:\workspace\123\ccc\astrobiology\astro_frontend\src\main.js`
- `D:\workspace\123\ccc\astrobiology\astro_frontend\src\views\UnifiedReview.vue`
- `D:\workspace\123\ccc\astrobiology\backend\config\settings.py`
- `D:\workspace\123\ccc\astrobiology\backend\config\django_settings.py`
- `D:\workspace\123\ccc\astrobiology\backend\pdf_processor\embedding_service.py`
- `D:\workspace\123\ccc\astrobiology\backend\pdf_processor\reranker_service.py`
- `D:\workspace\123\ccc\astrobiology\backend\models\all-mpnet-base-v2\model.safetensors`
- `D:\workspace\123\ccc\astrobiology\data\weaviate_data\classifications.db`

## 风险说明

- 本轮删除对象全部为用户显式授权的低风险缓存
- 虽然 `backend\**\__pycache__` 中包含位于 `management\commands\` 下的字节码缓存，但本轮没有删除任何管理命令源码，仅删除了缓存目录
- 虽然处理了 `.venv` 的子目录缓存，但没有删除 `.venv` 根目录、解释器、包文件或任何模型/依赖二进制
- 没有触碰任何模型目录、向量库、实验结果、上传文件、评测文件、数据库文件或配置文件
