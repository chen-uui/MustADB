# runtime_artifacts_audit_report

## 一、核验范围

本轮仅做只读核验，未执行任何删除、移动、重命名、覆盖、代码修改或 `.gitignore` 修改。

核验对象仅限以下 10 个路径：

- `D:\workspace\123\.serena\cache\`
- `D:\workspace\123\ccc\astrobiology\.serena\cache\`
- `D:\workspace\123\.trae\documents\`
- `D:\workspace\123\ccc\astrobiology\astro_frontend\dist\`
- `D:\workspace\123\logs\astrobiology.log`
- `D:\workspace\123\ccc\astrobiology\logs\astrobiology.log`
- `D:\workspace\123\ccc\astrobiology\backend\logs\astrobiology.log`
- `D:\workspace\123\ccc\astrobiology\backend\logs\bench_log.jsonl`
- `D:\workspace\123\ccc\astrobiology\backend\uploads\`
- `D:\workspace\123\ccc\astrobiology\backend\staticfiles\`

本轮明确未处理：

- `D:\workspace\123\ccc\astrobiology\backend\media\uploads\`
- `D:\workspace\123\ccc\astrobiology\backend\models\cache\`
- 所有 `management/commands/`
- `D:\workspace\123\ccc\astrobiology\data\`
- `D:\workspace\123\ccc\astrobiology\backend\runs\`
- `D:\workspace\123\ccc\astrobiology\backend\evaluation\`
- `D:\workspace\123\checkpoints\`
- `D:\workspace\123\.venv\`
- `D:\workspace\123\ccc\astrobiology\astro_frontend\node_modules\`

核验方法：

- 读取目录结构、文件大小、修改时间
- 反查代码、配置、启动脚本、日志配置、前端构建配置中的直接引用
- 对 `dist` 判断是否为 Vite 构建输出、是否存在当前部署依赖
- 对日志路径区分当前活跃写入位点与历史残留位点
- 对空目录判断是否为自动创建的兼容目录

---

## 二、工具缓存与工具目录分析

### 1. `D:\workspace\123\.serena\cache\`

- 分类：工具残留
- 当前内容：`python\document_symbols_cache_v23-06-25.pkl`，约 8.49 MB
- 是否被代码直接引用：否
- 是否被配置文件直接引用：否
- 是否被启动脚本/批处理文件引用：否
- 是否被日志配置写入：否
- 是否被前端构建流程依赖：否
- 是否只是“存在但未被主动使用”：对业务系统而言是
- 是否可自动重建：是，典型外部工具缓存
- 判断依据：目录名和文件名都指向 Serena 的文档符号缓存，不属于 Django、Vue、Vite 或业务运行产物
- 风险等级：中
- 结论：不影响业务系统运行，可进入后续人工确认删除清单

### 2. `D:\workspace\123\ccc\astrobiology\.serena\cache\`

- 分类：工具残留
- 当前内容：`python\document_symbols_cache_v23-06-25.pkl`，约 2.91 MB
- 是否被代码直接引用：否
- 是否被配置文件直接引用：否
- 是否被启动脚本/批处理文件引用：否
- 是否被日志配置写入：否
- 是否被前端构建流程依赖：否
- 是否只是“存在但未被主动使用”：对业务系统而言是
- 是否可自动重建：是
- 判断依据：同样属于 Serena 工具缓存，未发现业务代码或运行配置引用
- 风险等级：中
- 结论：不影响业务系统运行，可进入后续人工确认删除清单

### 3. `D:\workspace\123\.trae\documents\`

- 分类：工具残留
- 当前状态：空目录
- 是否被代码直接引用：否
- 是否被配置文件直接引用：否
- 是否被启动脚本/批处理文件引用：否
- 是否被日志配置写入：否
- 是否被前端构建流程依赖：否
- 是否只是“存在但未被主动使用”：是
- 是否可自动重建：大概率是
- 判断依据：未发现任何业务引用，目录名更像 IDE/工具工作目录；当前为空，说明至少当前项目运行不依赖其中内容
- 风险等级：中
- 结论：可进入后续人工确认删除清单，但不建议在未确认对应工具使用情况前直接处理

---

## 三、前端 dist 目录分析

### `D:\workspace\123\ccc\astrobiology\astro_frontend\dist\`

- 分类：手工部署快照候选
- 当前体积：约 4.76 MB
- 当前内容特征：
  - 存在 `index.html`
  - 存在 `assets\index-e5c6f86a.js`、`assets\index-7821bc7b.css`
  - 存在按哈希命名的分包 JS/CSS 与静态资源
  - 文件修改时间集中在 2025-11-23，符合一次完整构建输出的特征
- 是否被代码直接引用：否
- 是否被配置文件直接引用：是，`vite.config.js` 明确 `outDir: 'dist'`
- 是否被启动脚本/批处理文件引用：否，`start_frontend.bat` 与 `start_astrobiology_system.py` 都是 `npm run dev`
- 是否被日志配置写入：否
- 是否被前端构建流程依赖：是，`package.json` 的 `build` 为 `vite build`，`preview` 为 `vite preview`
- 是否只是“存在但未被主动使用”：从当前开发启动链路看，是
- 是否只是 Vite build 输出：是
- 是否可在需要时重建：是
- 是否存在当前项目的手工部署/静态发布依赖：未发现代码、后端配置或启动脚本对 `dist` 的直接运行时依赖
- 是否适合后续进入“可删除候选”：是，但仅限人工确认没有人依赖这份现成构建快照时

补充判断：

- `astro_frontend\.gitignore` 明确忽略 `dist/`
- `astro_frontend\jsconfig.json` 在 `exclude` 中排除了 `dist`
- 当前项目标准启动方式使用 Vite 开发服务器，不读取 `dist`
- `dist\index.html` 为典型静态发布入口，因此它也具备“手工部署快照候选”的属性

风险等级：中

结论：

- 本质上它是可自动重建的 Vite 构建产物
- 但如果有人在本地或外部服务器上直接复制这份目录做静态发布，它又可能承担“手工部署快照”角色
- 因此更稳妥的归类是“手工部署快照候选”，建议进入下一轮人工确认，而不是直接判定可删

---

## 四、日志位点分析

本项目的日志路径具有明显的“相对路径 + 当前工作目录”特征，因此不同启动位置可能落到不同 `logs\` 目录。这也是日志位点分散的主要原因。

### 1. `D:\workspace\123\ccc\astrobiology\backend\logs\astrobiology.log`

- 分类：仅影响调试/排障
- 当前状态：活跃写入位点
- 体积：约 3.65 MB
- 最后修改时间：2026-03-13 13:58:03
- 末尾内容显示：Weaviate 连接与 RAG 服务初始化成功
- 是否被代码直接引用：是
- 是否被配置文件直接引用：是
- 是否被启动脚本/批处理文件引用：间接是
- 是否被日志配置写入：是
- 是否被前端构建流程依赖：否
- 是否只是“存在但未被主动使用”：否
- 判断依据：
  - `backend\config\settings.py` 明确写 `BASE_DIR / 'logs' / 'astrobiology.log'`
  - `backend\logging_config.py` 也写 `logs\astrobiology.log`
  - `start_backend.bat` 与 `start_astrobiology_system.py` 都会先切到 `backend\` 再启动，因此当前标准启动链路会把日志写到这里
- 是否适合未来做日志轮转/归档，而不是删除：是
- 风险等级：高
- 结论：当前不建议处理，应视为现行活跃日志位点

### 2. `D:\workspace\123\ccc\astrobiology\backend\logs\bench_log.jsonl`

- 分类：仅影响调试/排障
- 当前状态：近期活跃的 benchmark 输出位点
- 体积：约 244 KB
- 最后修改时间：2026-02-25 15:21:35
- 末尾内容显示：连续 `extract_task` 基准记录写入
- 是否被代码直接引用：是
- 是否被配置文件直接引用：部分是
- 是否被启动脚本/批处理文件引用：否
- 是否被日志配置写入：否，属于基准脚本自行写入
- 是否被前端构建流程依赖：否
- 是否只是“存在但未被主动使用”：否
- 判断依据：
  - `backend\pdf_processor\bench_logging.py` 默认写入 `base_dir / "logs" / "bench_log.jsonl"`
  - 基准工作流可通过 `BENCH_LOG_PATH` 覆盖，但默认位点就是当前文件
  - 当前内容是结构化 JSONL 基准记录，不像普通错误日志
- `bench_log.jsonl` 是否仍用于当前 benchmark 工作流：是
- 是否适合未来做日志轮转/归档，而不是删除：是
- 风险等级：高
- 结论：应视为当前 benchmark 工作流输出，不建议进入删除候选

### 3. `D:\workspace\123\ccc\astrobiology\logs\astrobiology.log`

- 分类：仅影响调试/排障
- 当前状态：更像历史残留或替代启动位点
- 体积：0 B
- 最后修改时间：2025-09-30 16:00:48
- 是否被代码直接引用：否
- 是否被配置文件直接引用：弱引用
- 是否被启动脚本/批处理文件引用：否
- 是否被日志配置写入：可能在特定启动目录下被写入
- 是否被前端构建流程依赖：否
- 是否只是“存在但未被主动使用”：大概率是
- 判断依据：
  - `.env` 中 `LOG_FILE=./logs/astrobiology.log` 使用了相对路径
  - 如果有人从 `ccc\astrobiology\` 根目录启动后端，日志可能落到该目录
  - 但当前标准启动脚本都先切到 `backend\`，因此该文件不是当前标准位点
- 哪些更像历史残留：本文件属于这一类
- 是否适合未来做日志轮转/归档，而不是删除：不适用，先确认是否还有替代启动方式
- 风险等级：中
- 结论：可进入后续人工确认清单，但不建议自动处理

### 4. `D:\workspace\123\logs\astrobiology.log`

- 分类：仅影响调试/排障
- 当前状态：更像历史残留或工作区级启动残留
- 体积：约 13.58 KB
- 最后修改时间：2025-11-02 23:25:45
- 末尾内容显示：Weaviate 连接成功
- 是否被代码直接引用：否
- 是否被配置文件直接引用：弱引用
- 是否被启动脚本/批处理文件引用：否
- 是否被日志配置写入：可能在更高层工作目录下被写入
- 是否被前端构建流程依赖：否
- 是否只是“存在但未被主动使用”：大概率是
- 判断依据：
  - 同样受 `.env` 中相对日志路径影响
  - 如果从 `D:\workspace\123` 作为当前工作目录启动相关 Python 进程，可能生成该文件
  - 当前标准项目启动脚本不指向该路径
- 哪些更像历史残留：本文件属于这一类
- 是否适合未来做日志轮转/归档，而不是删除：先做人工确认即可
- 风险等级：中
- 结论：可进入后续人工确认清单，但不建议自动处理

日志位点总判断：

- 当前活跃写入位点：`backend\logs\astrobiology.log`
- 当前 benchmark 工作流位点：`backend\logs\bench_log.jsonl`
- 更像历史残留或替代启动位点：`ccc\astrobiology\logs\astrobiology.log`、`D:\workspace\123\logs\astrobiology.log`
- 后续更适合做的动作：日志轮转、归档策略、统一日志落点，而不是直接删除

---

## 五、空目录与兼容目录分析

### 1. `D:\workspace\123\ccc\astrobiology\backend\uploads\`

- 分类：空目录兼容位点
- 当前状态：空目录
- 是否为空：是
- 是否被代码直接引用：仅在配置层被引用
- 是否被配置文件直接引用：是
- 是否被启动脚本/批处理文件引用：否
- 是否被日志配置写入：否
- 是否被前端构建流程依赖：否
- 是否只是“存在但未被主动使用”：当前业务上传链路下，大概率是
- 判断依据：
  - `backend\config\settings.py` 中 `STORAGE_CONFIG['UPLOAD_DIR']` 默认指向 `BASE_DIR / 'uploads'`
  - 同一文件的 `ensure_directories()` 会主动创建该目录
  - 但当前上传视图实际写入的是 `settings.MEDIA_ROOT / 'uploads'`，即 `backend\media\uploads\`
- 是否由 settings / django_settings / 启动逻辑自动创建：是
- 如果删除，是否会在下次启动自动重建：大概率会
- 是否更适合“保留为空目录”而不是处理：是
- 风险等级：中
- 结论：它更像历史兼容目录或保底目录，虽可重建，但本轮更适合保留为空目录；若未来要删，必须先确认没有环境变量覆盖 `UPLOAD_DIR`

### 2. `D:\workspace\123\ccc\astrobiology\backend\staticfiles\`

- 分类：空目录兼容位点
- 当前状态：空目录
- 是否为空：是
- 是否被代码直接引用：否
- 是否被配置文件直接引用：是
- 是否被启动脚本/批处理文件引用：未发现直接引用
- 是否被日志配置写入：否
- 是否被前端构建流程依赖：否
- 是否只是“存在但未被主动使用”：在当前开发启动链路下，基本是
- 判断依据：
  - `backend\config\django_settings.py` 明确配置 `STATIC_ROOT = BASE_DIR / 'staticfiles'`
  - 同文件 `ensure_directories()` 会主动创建 `STATIC_ROOT`
  - 该目录典型用于 Django `collectstatic` 输出
- 是否由 settings / django_settings / 启动逻辑自动创建：是
- 如果删除，是否会在下次启动自动重建：大概率会
- 是否更适合“保留为空目录”而不是处理：是
- 风险等级：高
- 结论：虽然可重建，但它是 Django 静态资源发布位点，当前不建议处理

---

## 六、明确可进入下一轮人工确认的对象

以下对象可进入“下一轮人工确认”，但本轮不建议自动处理：

- `D:\workspace\123\.serena\cache\`
  - 原因：外部工具缓存，不影响业务运行，可重建

- `D:\workspace\123\ccc\astrobiology\.serena\cache\`
  - 原因：外部工具缓存，不影响业务运行，可重建

- `D:\workspace\123\.trae\documents\`
  - 原因：空工具目录，未见业务引用

- `D:\workspace\123\ccc\astrobiology\astro_frontend\dist\`
  - 原因：当前看是可重建的 Vite 输出，但仍需确认是否有人把它当现成本地部署快照使用

- `D:\workspace\123\logs\astrobiology.log`
  - 原因：更像工作区级历史残留日志位点，需要先确认是否存在非标准启动习惯

- `D:\workspace\123\ccc\astrobiology\logs\astrobiology.log`
  - 原因：更像项目根级历史残留日志位点，需要先确认是否存在替代启动方式

- `D:\workspace\123\ccc\astrobiology\backend\uploads\`
  - 原因：当前业务上传链路未直接使用，但仍受 `UPLOAD_DIR` 配置和自动建目录逻辑影响

---

## 七、当前不建议处理的对象

- `D:\workspace\123\ccc\astrobiology\backend\logs\astrobiology.log`
  - 当前标准启动链路下的活跃日志写入位点

- `D:\workspace\123\ccc\astrobiology\backend\logs\bench_log.jsonl`
  - 当前 benchmark 工作流默认输出位点

- `D:\workspace\123\ccc\astrobiology\backend\staticfiles\`
  - Django `STATIC_ROOT` 位点，属于静态发布兼容目录

不建议处理的核心原因：

- 当前仍被标准启动链路、配置或 benchmark 输出流程直接使用
- 即使目录为空，也承担发布兼容位点作用
- 更适合未来通过归档、轮转、流程统一来处理，而不是按“残留物”直接清理

---

## 八、建议的后续操作顺序

1. 先确认日志启动路径习惯。
   - 核实团队是否有人从 `D:\workspace\123` 或 `D:\workspace\123\ccc\astrobiology` 直接启动后端。

2. 再确认 `dist` 是否承担手工部署快照角色。
   - 如果没有人直接复制 `dist\` 做静态发布，它可进入后续可删候选。

3. 单独确认工具目录使用情况。
   - 若 Serena / Trae 只是本地辅助工具，缓存和空目录可进入更低风险的人工清单。

4. 对 `backend\uploads\` 检查是否存在环境变量覆盖。
   - 重点看是否有人设置 `UPLOAD_DIR` 指向该目录。

5. 对日志处理优先做“归档与轮转策略”确认。
   - 不建议把活跃日志位点直接纳入删除流程。

6. 对 `staticfiles\` 保持保守。
   - 除非已明确没有 Django 静态发布需求，否则不建议碰。

---

## 总表

| 路径 | 分类 | 是否被直接引用 | 是否可重建 | 当前风险等级 | 后续建议 |
| --- | --- | --- | --- | --- | --- |
| `D:\workspace\123\.serena\cache\` | 工具残留 | 否 | 是 | 中 | 人工确认后可删 |
| `D:\workspace\123\ccc\astrobiology\.serena\cache\` | 工具残留 | 否 | 是 | 中 | 人工确认后可删 |
| `D:\workspace\123\.trae\documents\` | 工具残留 | 否 | 大概率是 | 中 | 人工确认后可删 |
| `D:\workspace\123\ccc\astrobiology\astro_frontend\dist\` | 手工部署快照候选 | 是（构建配置） | 是 | 中 | 人工确认后可删 |
| `D:\workspace\123\logs\astrobiology.log` | 仅影响调试/排障 | 弱引用 | 是 | 中 | 人工确认后可删 |
| `D:\workspace\123\ccc\astrobiology\logs\astrobiology.log` | 仅影响调试/排障 | 弱引用 | 是 | 中 | 人工确认后可删 |
| `D:\workspace\123\ccc\astrobiology\backend\logs\astrobiology.log` | 仅影响调试/排障 | 是 | 是 | 高 | 归档 |
| `D:\workspace\123\ccc\astrobiology\backend\logs\bench_log.jsonl` | 仅影响调试/排障 | 是 | 是 | 高 | 保留 |
| `D:\workspace\123\ccc\astrobiology\backend\uploads\` | 空目录兼容位点 | 是（配置） | 是 | 中 | 保留 |
| `D:\workspace\123\ccc\astrobiology\backend\staticfiles\` | 空目录兼容位点 | 是（配置） | 是 | 高 | 不建议处理 |

