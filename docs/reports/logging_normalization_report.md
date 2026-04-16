# logging_normalization_report

## 一、审计范围

本轮仅做日志配置与日志位点只读审计，未执行任何删除、移动、重命名、覆盖或代码修改。

审计对象：

- 日志文件位点
  - `D:\workspace\123\logs\astrobiology.log`
  - `D:\workspace\123\ccc\astrobiology\logs\astrobiology.log`
  - `D:\workspace\123\ccc\astrobiology\backend\logs\astrobiology.log`
  - `D:\workspace\123\ccc\astrobiology\backend\logs\bench_log.jsonl`
- 日志配置来源
  - `D:\workspace\123\ccc\astrobiology\backend\config\django_settings.py`
  - `D:\workspace\123\ccc\astrobiology\backend\config\settings.py`
  - `D:\workspace\123\ccc\astrobiology\backend\logging_config.py`
  - `D:\workspace\123\ccc\astrobiology\backend\pdf_processor\bench_logging.py`
  - `D:\workspace\123\ccc\astrobiology\backend\manage.py`
  - `D:\workspace\123\manage.py`
  - `D:\workspace\123\ccc\astrobiology\backend\start_backend.bat`
  - `D:\workspace\123\ccc\astrobiology\start_astrobiology_system.py`
  - `D:\workspace\123\ccc\astrobiology\.env`
  - `D:\workspace\123\ccc\astrobiology\backend\config\wsgi.py`
  - `D:\workspace\123\ccc\astrobiology\backend\config\asgi.py`

补充说明：

- `backend\config\` 下未发现独立的 `local settings` / `production settings` 文件
- 本轮未审计 `management/commands/` 具体实现，仅基于非命令文件中的 benchmark 日志写入逻辑判断其用途

---

## 二、日志配置来源分析

### 1. 当前主日志 `astrobiology.log` 的真实写入配置

当前标准 Django 启动入口是：

- `D:\workspace\123\ccc\astrobiology\backend\manage.py`
  - 默认 `DJANGO_SETTINGS_MODULE = config.django_settings`
- `D:\workspace\123\manage.py`
  - 会先 `os.chdir()` 到 `D:\workspace\123\ccc\astrobiology\backend\`
  - 再代理执行 `backend\manage.py`

因此，当前标准开发/命令行路径下，真正生效的主配置是：

- `D:\workspace\123\ccc\astrobiology\backend\config\django_settings.py`

该文件的主日志写入点定义为：

- `LOGGING['handlers']['file']['filename'] = get_env_var('LOG_FILE', str(BASE_DIR / 'logs' / 'django.log'))`

同时 `.env` 中存在：

- `LOG_FILE=./logs/astrobiology.log`

这意味着当前标准 Django 运行时，主日志实际写入的是：

- 相对路径 `./logs/astrobiology.log`

而不是硬编码绝对路径。

### 2. 为什么会出现多个不同目录下的 `astrobiology.log`

根因不是“有多个不同名字的日志配置”，而是“同一个相对日志路径在不同 `cwd` 下被解析到了不同目录”。

形成链条如下：

1. `.env` 把主日志文件名定义成相对路径 `./logs/astrobiology.log`
2. `config.django_settings` 直接读取该环境变量作为 `FileHandler` 的 `filename`
3. Python 的相对文件路径会相对于进程当前工作目录 `cwd` 解析
4. 当后端从不同目录启动时，同一个 `LOG_FILE` 会落到不同的 `logs\astrobiology.log`

所以会出现：

- `D:\workspace\123\logs\astrobiology.log`
- `D:\workspace\123\ccc\astrobiology\logs\astrobiology.log`
- `D:\workspace\123\ccc\astrobiology\backend\logs\astrobiology.log`

### 3. 这些路径分别由什么机制导致

#### `D:\workspace\123\ccc\astrobiology\backend\logs\astrobiology.log`

- 形成原因：相对路径 `./logs/astrobiology.log` 在 `cwd = backend\` 时解析
- 触发方式：
  - `backend\start_backend.bat` 先 `cd /d ...\backend`
  - 根级 `manage.py` 先 `os.chdir()` 到 `backend\`
  - `start_astrobiology_system.py` 的后端启动命令也先 `cd /d "{backend_dir}"`
- 结论：这是当前标准位点

#### `D:\workspace\123\ccc\astrobiology\logs\astrobiology.log`

- 形成原因：相对路径 `./logs/astrobiology.log` 在 `cwd = ccc\astrobiology\` 时解析
- 触发方式：更像从项目根目录直接启动 Python/Django 的历史用法或 IDE 启动残留
- 结论：替代启动残留 / 历史残留

#### `D:\workspace\123\logs\astrobiology.log`

- 形成原因：相对路径 `./logs/astrobiology.log` 在 `cwd = D:\workspace\123\` 时解析
- 触发方式：更像从工作区根目录启动某个 Python 入口时产生
- 结论：历史残留

### 4. 其他与日志相关的配置源

#### `backend\config\settings.py`

该文件也定义了日志：

- `file` handler：`get_env_var('LOG_FILE', str(BASE_DIR / 'logs' / 'app.log'))`
- `astro_file` handler：`str(BASE_DIR / 'logs' / 'astrobiology.log')`

风险点：

- 如果未来某个入口改用 `config.settings`，则会同时存在“相对路径 handler”和“固定 `BASE_DIR` handler”
- 当 `cwd != backend` 时，`file` handler 仍会分散写到其他目录

但当前标准 `manage.py runserver` 并不默认使用它。

#### `backend\logging_config.py`

该文件使用：

- `LOG_DIR = Path("logs")`
- `filename = str(LOG_DIR / 'astrobiology.log')`

这也是相对路径，仍受 `cwd` 影响。

它不是当前 Django 默认配置入口，但如果某个脚本显式调用 `setup_logging()`，同样会造成“按当前目录落日志”。

#### `backend\pdf_processor\pdf_utils.py`

存在：

- `logging.basicConfig(level=..., format=...)`

但这里只设置级别和格式，没有指定文件路径，不是 `astrobiology.log` 分散的主因。

### 5. benchmark 日志来源

`D:\workspace\123\ccc\astrobiology\backend\pdf_processor\bench_logging.py` 中：

- 优先使用 `BENCH_LOG_PATH`
- 否则使用 `Path(settings.BASE_DIR) / "logs" / "bench_log.jsonl"`
- 再不行才 fallback 到 `Path.cwd() / "logs" / "bench_log.jsonl"`

因此 benchmark 日志的默认策略比主日志更稳定：

- 在 Django 上下文里，默认会稳定落到 `backend\logs\bench_log.jsonl`

### 6. 哪个日志路径才是“当前标准位点”

当前标准位点是：

- `D:\workspace\123\ccc\astrobiology\backend\logs\astrobiology.log`

原因：

- 当前标准开发入口 `backend\manage.py` 使用 `config.django_settings`
- 根级 `manage.py` 会先切换到 `backend\`
- `start_backend.bat` 和 `start_astrobiology_system.py` 也都先切换到 `backend\`
- 该文件也是四个日志对象中最近一次活跃写入的主日志

---

## 三、4 个日志文件的状态判断

### 1. `D:\workspace\123\ccc\astrobiology\backend\logs\astrobiology.log`

- 当前是否仍在活跃写入：是
- 当前角色：标准位点
- 依据：
  - 最后修改时间为 `2026-03-13 13:58:03`
  - 末尾内容是 Weaviate 连接成功、RAG 服务初始化成功
  - 与当前标准启动链路一致
- 风险等级：高
- 后续建议：保留

### 2. `D:\workspace\123\ccc\astrobiology\backend\logs\bench_log.jsonl`

- 当前是否仍在活跃写入：是，至少近期仍用于 benchmark
- 当前角色：benchmark 专用输出
- 依据：
  - 最后修改时间为 `2026-02-25 15:21:35`
  - 内容是结构化 JSONL benchmark 记录
  - `bench_logging.py` 默认写入该文件
- 风险等级：高
- 后续建议：保留

### 3. `D:\workspace\123\logs\astrobiology.log`

- 当前是否仍在活跃写入：否，未见近期写入
- 当前角色：历史残留
- 依据：
  - 最后修改时间为 `2025-11-02 23:25:45`
  - 内容是旧的 Weaviate 连接日志
  - 当前标准启动路径不会把日志写到这里
- 风险等级：中
- 后续建议：人工确认后可删

### 4. `D:\workspace\123\ccc\astrobiology\logs\astrobiology.log`

- 当前是否仍在活跃写入：否
- 当前角色：替代启动残留
- 依据：
  - 当前是空文件
  - 最后修改时间为 `2025-09-30 16:00:48`
  - 更像曾经从 `ccc\astrobiology\` 目录启动时预创建或残留的位点
- 风险等级：中
- 后续建议：人工确认后可删

---

## 四、日志分散根因

日志分散的根因有四个，且其中前两个是主因。

### 根因 1：主日志路径使用了相对环境变量

- `.env` 中定义 `LOG_FILE=./logs/astrobiology.log`
- `config.django_settings.py` 直接使用这个值

这会把“主日志位点”绑定到运行时 `cwd`，而不是绑定到项目目录。

### 根因 2：项目存在多个会改变或依赖 `cwd` 的启动入口

已确认的 `cwd` 相关入口：

- `D:\workspace\123\manage.py`
  - 先 `os.chdir(backend_dir)`
- `D:\workspace\123\ccc\astrobiology\backend\start_backend.bat`
  - 先 `cd /d ...\backend`
- `D:\workspace\123\ccc\astrobiology\start_astrobiology_system.py`
  - 用 `cd /d "{backend_dir}" && python manage.py runserver`

这使得“标准入口”虽然比较稳定，但只要有人不走这些入口，仍可能把日志写到别的 `logs\` 目录。

### 根因 3：仓库里同时存在两套 Django settings

- `config.django_settings`
- `config.settings`

并且：

- `backend\manage.py` 默认用 `config.django_settings`
- `wsgi.py` / `asgi.py` 默认在 `USE_SETTINGS_UNIFIED != true` 时使用 `config.settings`

这会导致不同运行场景下使用不同日志 handler 组合，增加配置歧义。

### 根因 4：还有一套相对路径日志配置 `logging_config.py`

- `logging_config.py` 里的 `LOG_DIR = Path("logs")`

它不是当前标准 Django 入口的唯一来源，但如果某些脚本显式调用 `setup_logging()`，仍会继续制造“按当前目录落日志”的问题。

---

## 五、建议的标准日志位点

建议的标准主日志位点：

- `D:\workspace\123\ccc\astrobiology\backend\logs\astrobiology.log`

建议的 benchmark 日志位点：

- `D:\workspace\123\ccc\astrobiology\backend\logs\bench_log.jsonl`

理由：

- 两者都位于 `backend\logs\`
- 当前标准启动链路已经天然落到该目录
- benchmark 日志默认也使用 `settings.BASE_DIR / "logs"`
- 相比工作区根目录或项目根目录，`backend\logs\` 与后端运行边界更清晰

---

## 六、建议的日志收敛方案（只提方案，不修改）

### 方案 1：统一主日志目录到 `backend\logs\`

建议统一到：

- `D:\workspace\123\ccc\astrobiology\backend\logs\`

原因：

- 与当前标准运行链路一致
- 与 benchmark 日志现状一致
- 易于后续做轮转、归档和监控

### 方案 2：主日志路径改为稳定路径表达

建议不要再使用：

- `LOG_FILE=./logs/astrobiology.log`

建议未来统一为以下两种方式之一：

- 使用 `BASE_DIR / 'logs' / 'astrobiology.log'`
- 或使用明确的绝对路径环境变量

优先建议：

- 代码中统一以 `settings.BASE_DIR` 或等价绝对项目根路径拼接日志文件

原因：

- 避免 `cwd` 变化导致同名日志散落到不同目录
- 让 CLI、IDE、脚本、服务进程的行为一致

### 方案 3：统一 settings 入口

建议未来收敛到单一 Django settings 入口，至少统一日志配置来源。

当前问题：

- `manage.py` 走 `config.django_settings`
- `wsgi/asgi` 默认可能走 `config.settings`

建议：

- 保证开发、脚本、部署使用同一套日志配置

### 方案 4：保留并强化日志轮转

建议保留轮转能力，尤其是主日志。

原因：

- `backend\logs\astrobiology.log` 已持续积累到约 3.65 MB
- `config.settings` 和 `logging_config.py` 都已出现 `RotatingFileHandler`
- 收敛时应以可轮转方案为准，而不是退回普通 `FileHandler`

### 方案 5：benchmark 日志独立保留

建议 `bench_log.jsonl` 继续独立于普通运行日志。

原因：

- 内容是结构化实验/基准记录，不是常规运行故障日志
- 清理和归档策略应与主应用日志分开
- 不建议把它并入 `astrobiology.log`

---

## 七、未来可归档/可人工确认删除的对象

### 更适合未来归档的对象

- `D:\workspace\123\ccc\astrobiology\backend\logs\astrobiology.log`
  - 原因：当前活跃标准位点，不应直接删除，但未来可以按时间片归档

- `D:\workspace\123\ccc\astrobiology\backend\logs\bench_log.jsonl`
  - 原因：benchmark 专用输出，适合独立归档，不建议并入普通日志清理

### 更适合未来人工确认后删除的对象

- `D:\workspace\123\logs\astrobiology.log`
  - 原因：历史残留，当前标准启动路径不再写入

- `D:\workspace\123\ccc\astrobiology\logs\astrobiology.log`
  - 原因：替代启动残留或空文件残留

---

## 八、当前不建议处理的对象

- `D:\workspace\123\ccc\astrobiology\backend\logs\astrobiology.log`
  - 当前标准主日志位点，仍在活跃写入

- `D:\workspace\123\ccc\astrobiology\backend\logs\bench_log.jsonl`
  - 当前 benchmark 工作流专用输出，建议独立保留

对于以下对象，也不建议在未完成日志收敛前贸然处理：

- `D:\workspace\123\logs\astrobiology.log`
- `D:\workspace\123\ccc\astrobiology\logs\astrobiology.log`

原因：

- 这些文件本身风险不高，但它们反映出“相对路径 + 多启动入口”的根因仍未被修复
- 在收敛方案落地前，贸然删除可能掩盖真实启动路径问题

---

## 总表

| 路径 | 当前角色 | 是否活跃写入 | 形成原因 | 风险等级 | 后续建议 |
| --- | --- | --- | --- | --- | --- |
| `D:\workspace\123\logs\astrobiology.log` | 历史残留 | 否 | 相对 `LOG_FILE` 在工作区根目录 `cwd` 下解析 | 中 | 人工确认后可删 |
| `D:\workspace\123\ccc\astrobiology\logs\astrobiology.log` | 替代启动残留 | 否 | 相对 `LOG_FILE` 在项目根目录 `cwd` 下解析 | 中 | 人工确认后可删 |
| `D:\workspace\123\ccc\astrobiology\backend\logs\astrobiology.log` | 标准位点 | 是 | 当前标准入口先切到 `backend\`，相对 `LOG_FILE` 在此解析 | 高 | 保留 |
| `D:\workspace\123\ccc\astrobiology\backend\logs\bench_log.jsonl` | benchmark 专用输出 | 是 | `bench_logging.py` 默认使用 `settings.BASE_DIR / logs` | 高 | 保留 |

