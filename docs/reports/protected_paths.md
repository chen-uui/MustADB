# 高风险保护区清单

以下路径在本次审计中视为高风险保护区，不建议自动删除。

## 运行关键入口与配置

- `D:\workspace\123\manage.py`
- `D:\workspace\123\ccc\astrobiology\backend\manage.py`
- `D:\workspace\123\ccc\astrobiology\.env`
- `D:\workspace\123\ccc\astrobiology\.env.template`
- `D:\workspace\123\ccc\astrobiology\docker-compose.yml`
- `D:\workspace\123\ccc\astrobiology\start_astrobiology_system.py`
- `D:\workspace\123\ccc\astrobiology\backend\requirements.txt`
- `D:\workspace\123\ccc\astrobiology\astro_frontend\package.json`
- `D:\workspace\123\ccc\astrobiology\astro_frontend\package-lock.json`

## 数据、文库、向量库、上传文件

- `D:\workspace\123\ccc\astrobiology\data\`
- `D:\workspace\123\ccc\astrobiology\data\pdfs\`
- `D:\workspace\123\ccc\astrobiology\data\weaviate_data\`
- `D:\workspace\123\ccc\astrobiology\backend\media\uploads\`
- `D:\workspace\123\ccc\astrobiology\backend\evaluation\`
- `D:\workspace\123\ccc\astrobiology\backend\runs\`

## 模型、检查点与持久化状态

- `D:\workspace\123\ccc\astrobiology\backend\models\`
- `D:\workspace\123\ccc\astrobiology\backend\models\all-mpnet-base-v2\`
- `D:\workspace\123\ccc\astrobiology\backend\models\all-MiniLM-L6-v2\`
- `D:\workspace\123\ccc\astrobiology\backend\models\cross-encoder\ms-marco-MiniLM-L-6-v2\`
- `D:\workspace\123\ccc\astrobiology\checkpoints\`
- `D:\workspace\123\ccc\astrobiology\checkpoints\extraction_tasks\`

## Django 迁移与管理命令

- `D:\workspace\123\ccc\astrobiology\backend\astro_data\migrations\`
- `D:\workspace\123\ccc\astrobiology\backend\meteorite_search\migrations\`
- `D:\workspace\123\ccc\astrobiology\backend\pdf_processor\migrations\`
- `D:\workspace\123\ccc\astrobiology\backend\meteorite_search\management\commands\`
- `D:\workspace\123\ccc\astrobiology\backend\pdf_processor\management\commands\`

## 脚本目录

- `D:\workspace\123\scripts\`
- `D:\workspace\123\ccc\astrobiology\backend\scripts\`
- `D:\workspace\123\ccc\astrobiology\astro_frontend\scripts\`

## 规则层面的文件类型保护

- 本工作区内所有 `csv / json / xlsx / parquet / pkl / pt / bin / ckpt / faiss / db` 文件
- 与实验、评测、gold set、seed set、论文图表、模型配置、抽取结果直接相关的文件
- `backend/runs/` 内的 `summary.md / summary.json / raw.jsonl / raw_extraction_*.jsonl / accuracy_*.csv / gold_seed_*.csv` 等结果文件

## 备注

- 即使某些对象看起来“旧”“重复”或“近期未被 import”，只要它们落在以上保护区，默认都不应自动判定为可删
- 特别是 Django、Vue、RAG、向量库、评测脚本、管理命令相关路径，本次统一按保守策略处理
