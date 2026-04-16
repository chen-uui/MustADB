# logging_normalization_execution_report

## 执行范围

本轮只做“主日志路径标准化”相关的小范围修复，未删除、归档、移动、重命名任何现有日志文件，未改动 benchmark 日志语义，未触碰业务功能、数据库、上传、RAG、模型或评测逻辑。

## 实际修改的文件

- `D:\workspace\123\ccc\astrobiology\backend\config\django_settings.py`
- `D:\workspace\123\ccc\astrobiology\backend\config\settings.py`
- `D:\workspace\123\ccc\astrobiology\backend\logging_config.py`

本轮明确检查但未修改：

- `D:\workspace\123\ccc\astrobiology\.env`

## 每个修改的目的

### 1. `backend\config\django_settings.py`

- 目的：让当前标准 Django 入口在读取 `LOG_FILE` 时，不再受运行时 `cwd` 影响
- 做法：
  - 新增 `resolve_log_path(...)`
  - 新增 `MAIN_LOG_FILE`
  - 把主日志 handler 的 `filename` 改为 `str(MAIN_LOG_FILE)`
  - 把建目录逻辑改为使用 `MAIN_LOG_FILE.parent`

### 2. `backend\config\settings.py`

- 目的：让备用 settings 与 `django_settings.py` 在主日志位点上采用一致的稳定策略
- 做法：
  - 新增同样的 `resolve_log_path(...)`
  - 新增 `MAIN_LOG_FILE`
  - 把 `file` 和 `astro_file` 的主日志路径都收敛到 `MAIN_LOG_FILE`
  - 将 `root.handlers` 从 `['console', 'file', 'astro_file']` 收敛为 `['console', 'astro_file']`
  - 建目录逻辑改为使用 `MAIN_LOG_FILE.parent`

说明：

- 之所以同步调整 `root.handlers`，是为了避免在 `config.settings` 下出现两个 handler 同时写入同一个 `astrobiology.log` 的重复写入问题

### 3. `backend\logging_config.py`

- 目的：修复 `Path("logs")` 这类受 `cwd` 影响的相对路径写法
- 做法：
  - 新增基于 `__file__` 的 `BASE_DIR`
  - 把 `LOG_DIR` 改为稳定的 `BASE_DIR / "logs"`
  - 新增 `resolve_log_path(...)` 与 `MAIN_LOG_FILE`
  - 把主日志 handler 的 `filename` 改为 `str(MAIN_LOG_FILE)`

### 4. `.env`

- 本轮未修改
- 原因：
  - `.env` 当前仍是 `LOG_FILE=./logs/astrobiology.log`
  - 但代码层已把该相对值规范化为“相对于 backend BASE_DIR 的稳定路径”
  - 因此不需要把 `.env` 改成机器相关的绝对 Windows 路径，保留了可移植性

## 修改前后的关键差异摘要

### 修改前

- `config.django_settings.py`
  - 直接使用 `get_env_var('LOG_FILE', ...)`
  - `.env` 中的 `./logs/astrobiology.log` 会按当前 `cwd` 解析

- `config.settings.py`
  - `file` handler 使用相对 `LOG_FILE`
  - `astro_file` handler 使用 `BASE_DIR / logs / astrobiology.log`
  - 两套写法并存，未来容易再次分散

- `logging_config.py`
  - 使用 `Path("logs")`
  - 仍然受 `cwd` 影响

### 修改后

- 三处日志配置都统一引入了 `resolve_log_path(...)`
- 相对 `LOG_FILE` 会被规范化为：
  - `D:\workspace\123\ccc\astrobiology\backend\logs\astrobiology.log`
- 默认未设置 `LOG_FILE` 时，也统一回落到：
  - `backend\logs\astrobiology.log`
- `config.settings.py` 不再让两个 root file handler 同时写同一主日志

## 为什么这样可以避免不同 cwd 产生多个 astrobiology.log

修复前的核心问题是：

- `.env` 使用相对路径 `./logs/astrobiology.log`
- Python 在打开相对路径文件时，会相对于进程当前工作目录 `cwd`

修复后的核心变化是：

- 代码先把 `LOG_FILE` 转成 `Path`
- 如果是相对路径，就不再交给运行时 `cwd` 解析
- 而是显式按 `backend BASE_DIR` 做一次规范化

因此无论从哪个入口运行：

- `backend\manage.py`
- 根级 `manage.py`
- `start_backend.bat`
- `start_astrobiology_system.py`
- 甚至从其他 `cwd` 手工导入配置

最终主日志都会稳定指向：

- `D:\workspace\123\ccc\astrobiology\backend\logs\astrobiology.log`

## benchmark 日志为何未被并入主日志

- `bench_log.jsonl` 的职责是 benchmark / extraction 基准记录
- 它的格式是独立的 JSONL，不是普通运行日志
- 当前路径解析逻辑本身已经稳定：
  - 优先 `BENCH_LOG_PATH`
  - 否则 `settings.BASE_DIR / "logs" / "bench_log.jsonl"`
- 本轮目标是修复主日志 `astrobiology.log` 的分散写入，不是改变 benchmark 输出语义

因此本轮只做了验证，没有把 `bench_log.jsonl` 并入主日志，也没有改动其格式或写入语义。

## 轻量验证结果

### 1. 配置可正常导入

- 已通过 `py_compile` 校验：
  - `backend\config\django_settings.py`
  - `backend\config\settings.py`
  - `backend\logging_config.py`

### 2. 主日志路径在不同 cwd 下都稳定

已用 Python 直接导入 `config.django_settings` 验证两次：

- 在 `workdir = D:\workspace\123\ccc\astrobiology\backend`
- 在 `workdir = D:\workspace\123`

两次得到的主日志路径一致，都是：

- `D:\workspace\123\ccc\astrobiology\backend\logs\astrobiology.log`

### 3. 备用 settings 也已收敛

导入 `config.settings` 后确认：

- `file` handler 指向 `D:\workspace\123\ccc\astrobiology\backend\logs\astrobiology.log`
- `astro_file` handler 也指向同一稳定路径
- `root.handlers` 为 `console,astro_file`

### 4. `logging_config.py` 不再依赖 cwd

导入 `logging_config` 后确认：

- `MAIN_LOG_FILE` 为 `D:\workspace\123\ccc\astrobiology\backend\logs\astrobiology.log`
- 对应 handler 的 `filename` 也是同一路径

### 5. benchmark 日志仍保持独立逻辑

已做轻量导入验证，`bench_logging` 解析结果仍为：

- `D:\workspace\123\ccc\astrobiology\backend\logs\bench_log.jsonl`

未改 JSONL 语义，未并入主日志。

### 6. 本轮未改动业务代码和无关配置

本轮只修改了 3 个日志配置相关文件：

- `backend\config\django_settings.py`
- `backend\config\settings.py`
- `backend\logging_config.py`

`.env`、业务代码、RAG、上传、模型、评测、benchmark 格式均未改。

## 本轮明确未处理的对象

- 旧日志文件本身
  - `D:\workspace\123\logs\astrobiology.log`
  - `D:\workspace\123\ccc\astrobiology\logs\astrobiology.log`
  - `D:\workspace\123\ccc\astrobiology\backend\logs\astrobiology.log`
  - `D:\workspace\123\ccc\astrobiology\backend\logs\bench_log.jsonl`

- 任何日志归档、删除、移动、重命名
- `.env` 的绝对路径改写
- benchmark 日志格式和输出语义
- 任何业务功能和非日志配置

## 结论

本轮修复的效果是：

- 阻止未来继续因“相对 `LOG_FILE` + 多 `cwd`”把 `astrobiology.log` 写散到多个目录
- 保持 benchmark 日志独立且稳定
- 不清理历史日志文件，只修复未来的写入落点

