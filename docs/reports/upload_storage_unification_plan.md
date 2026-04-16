# 上传 / 存储链路统一实施方案

## 一、当前链路全景图

### 1. 主要入口与真实落盘路径

| 入口 | 主要文件 | 入口类型 | 当前落盘位置 | 当前命名规则 | 元数据记录 | 后续处理 |
| --- | --- | --- | --- | --- | --- | --- |
| 用户上传 PDF | `D:\workspace\123\ccc\astrobiology\backend\pdf_processor\views_user_upload.py` | API：`/api/pdf/documents/user-upload/` | `backend/media/uploads/` | 磁盘文件名为 UUID，数据库 `filename` 保留原始文件名 | 创建 `PDFDocument`，`review_status='pending'`，`processed=False` | 仅提取基础元数据，不触发 Weaviate 索引 |
| 直接处理 | `D:\workspace\123\ccc\astrobiology\backend\pdf_processor\views\direct_processing_views.py` | API：单文件 / 批量处理 | `backend/media/uploads/` | 磁盘文件名为 UUID | 不创建 `PDFDocument`，只创建 `ProcessingTask` | 立即进入直接处理链路，生成 `DirectProcessingResult` |
| Weaviate 文档上传 | `D:\workspace\123\ccc\astrobiology\backend\pdf_processor\weaviate_views.py` | API：文档上传 | `data/pdfs/` | 直接使用原始文件名 | 创建 `PDFDocument`，`processed=False` | 线程内异步触发单文档处理，成功后置 `processed=True` |
| 待处理文档补处理 | `D:\workspace\123\ccc\astrobiology\backend\pdf_processor\weaviate_views.py` | API：`process_pending` / `process_stale` | 不重新落盘，直接读 `PDFDocument.file_path` | 依赖既有路径 | 依赖 `PDFDocument` | 重新推送到 Weaviate |
| 文件夹同步 | `D:\workspace\123\ccc\astrobiology\backend\pdf_processor\weaviate_views.py` | API：`sync_files` | 扫描 `PDF_STORAGE_PATH` | 以文件夹中的文件名为准 | 补写/更新 `PDFDocument`，并尝试补写 `sha1` | 可修正数据库记录，不直接做全文处理 |
| 重处理命令 | `D:\workspace\123\ccc\astrobiology\backend\pdf_processor\management\commands\reprocess_pdfs.py` | 管理命令 | 直接读 `../data/pdfs` | 以文件系统文件名为准 | 基本绕过 `PDFDocument` | 直接分块并重建 Weaviate 数据 |
| 文件同步命令 | `D:\workspace\123\ccc\astrobiology\backend\pdf_processor\management\commands\sync_pdfs.py` | 管理命令 | 直接扫 `Path(settings.BASE_DIR).parent / 'pdfs'` | 以文件系统文件名为准 | 创建/删除 `PDFDocument` | 只做文件夹与数据库同步 |

### 2. 当前链路的关键事实

- 当前至少存在 3 套实际上传/落盘路径：`backend/media/uploads/`、`data/pdfs/`、`Path(settings.BASE_DIR).parent / 'pdfs'`。
- `backend/config/settings.py` 还定义了 `STORAGE_CONFIG['UPLOAD_DIR'] = BASE_DIR / 'uploads'`，但这条路径并不是当前主要上传入口的统一事实来源。
- 用户上传链路、直接处理链路、Weaviate 上传链路对“上传成功后要不要建库、要不要审核、要不要索引”的语义并不一致。
- `PDFDocument.filename` 是唯一字段，但部分链路用原始文件名建记录，部分链路用 UUID 落盘并把原始名仅放在 `filename` 字段，字段含义已经混合了“显示名”和“标识键”。

### 3. 谁会直接读写 PDF 文件

- `views_user_upload.py` 直接写磁盘文件，并创建 `PDFDocument`。
- `direct_processing_views.py` 直接写磁盘文件，并创建 `ProcessingTask`。
- `weaviate_views.py` 的 `upload` 直接写磁盘文件，并创建 `PDFDocument`。
- `weaviate_views.py` 的 `process_pending` / `process_stale` 直接读取 `PDFDocument.file_path` 指向的文件。
- `weaviate_views.py` 的 `sync_files` 直接扫描文件夹，并按现有文件修正数据库。
- `reprocess_pdfs.py` 直接扫描文件夹重建索引，基本不依赖数据库记录。
- `sync_pdfs.py` 直接扫描文件夹并增删 `PDFDocument`。

## 二、最核心的不一致点

### 1. 文件目录不一致

- 用户上传与直接处理落在 `backend/media/uploads/`。
- Weaviate 上传与 `reprocess_pdfs.py` 以 `data/pdfs/` 为事实目录。
- `sync_pdfs.py` 使用 `Path(settings.BASE_DIR).parent / 'pdfs'`，与上面两者都不一致。
- `settings.py` 里的 `STORAGE_CONFIG['UPLOAD_DIR']` 又指向 `backend/uploads/`。

### 2. 命名规则不一致

- 用户上传与直接处理使用 UUID 作为磁盘文件名，原始文件名保留在业务字段里。
- Weaviate 上传直接用原始文件名落盘。
- 重处理与同步命令都默认“文件系统中的文件名就是稳定主键”。

### 3. 重复校验不一致

- 用户上传、Weaviate 上传目前主要按原始文件名查重。
- 同内容不同文件名无法挡住重复落盘。
- 同文件名不同内容也可能被误判为冲突。
- `weaviate_views.sync_files()` 才补算 `sha1`，但它不是统一入口。
- `direct_processing/utils.py` 里已有 `generate_file_hash()`，但算法是 MD5，且当前入口并未真正统一使用。

### 4. 元数据记录不一致

- 用户上传与 Weaviate 上传创建 `PDFDocument`。
- 直接处理不创建 `PDFDocument`，只建 `ProcessingTask`。
- `PDFDocument.filename` 既承担展示名，又被当成唯一标识，难以同时满足用户展示和系统幂等。
- `file_path` 是自由字符串，没有统一“标准化路径来源”。
- `sha1` 字段存在，但不是所有入口都写。

### 5. 后续处理触发方式不一致

- 用户上传只进入“待审核”，批准时也只是改 `review_status`，不会自动进入索引。
- Weaviate 上传会立即异步处理并写入向量库。
- 直接处理进入另一条独立任务链，不进 `PDFDocument` 主表。
- `process_pending` / `process_stale` / `reprocess_pdfs.py` 又各自承担补处理能力。

### 6. 错误恢复与重试方式不一致

- 直接处理链路有 `ProcessingTask` 可跟踪。
- Weaviate 上传主要依赖线程内处理和 `processed` 标记。
- 用户上传的“审核通过后如何补索引”没有统一恢复链路。
- 管理命令级的重处理绕过入口服务，容易形成“线上逻辑一套，补数据逻辑另一套”。

### 7. 重复落盘、重复处理、重复索引风险

- 同一份 PDF 可能先在用户上传里写一份 UUID 文件，再在 Weaviate 上传里以原名再写一份。
- 相同内容跨入口上传时，由于查重依赖文件名，容易多次入库、多次建任务、多次索引。
- `reprocess_pdfs.py` 与 `process_pending/process_stale` 并存，存在重复索引或覆盖索引状态的风险。

## 三、这条优化主线的短期/中期收益

### 1. 短期收益

- 提高上传成功后的行为可预测性，减少“落盘成功但后续处理状态不一致”的问题。
- 降低路径漂移带来的找文件失败、命令扫描不到文件、数据库记录与磁盘不一致的故障。
- 为问题排查提供单一事实来源，排查时不必先判断文件是从哪条历史链路进入的。
- 先统一保存入口后，可以马上减少未来新增重复 PDF 的概率。

### 2. 中期收益

- 为内容哈希去重、统一命名、统一元数据规范打基础。
- 减少同一 PDF 多份落盘导致的存储浪费。
- 让重处理、同步、索引补偿都围绕同一套文件定位与元数据规范展开，便于实验复现和历史数据修复。
- 为后续收敛 `views_user_upload`、`direct_processing`、`weaviate_views` 的职责边界提供可落地支点。

### 3. 收益分级判断

- 对功能稳定性的提升是短期可见收益。
- 对重复 PDF 控制和存储占用的改善，是短期开始见效、中期更明显的收益。
- 对问题排查、实验复现、历史数据修补的改善更偏中长期收益。

## 四、最小可执行重构方案（分阶段）

### Phase 1：抽出统一 upload/storage service 雏形，不改变对外接口

#### 目标

- 先收敛“文件保存、路径解析、文件命名、内容哈希、元数据回填”的底座能力。
- 保持现有 API、视图返回值、处理语义不变。

#### 建议改动文件

- 新增一个后端内部服务模块，例如放在 `pdf_processor/services/` 或 `pdf_processor/storage/` 下。
- 读取并统一消费：
  - `D:\workspace\123\ccc\astrobiology\backend\config\django_settings.py`
  - `D:\workspace\123\ccc\astrobiology\backend\config\settings.py`
- 视情况只做最小接线准备的模块：
  - `D:\workspace\123\ccc\astrobiology\backend\pdf_processor\models.py`
  - `D:\workspace\123\ccc\astrobiology\backend\pdf_processor\direct_processing\utils.py`

#### Phase 1 不改的文件

- `views_user_upload.py`
- `views/direct_processing_views.py`
- `weaviate_views.py`
- `reprocess_pdfs.py`
- `sync_pdfs.py`
- 现有上传文件本体与数据库记录

#### 建议产出能力

- 统一的“标准上传根目录解析函数”。
- 统一的“稳定文件名/显示文件名分离策略”。
- 统一的内容哈希计算函数，明确只保留一种标准算法。
- 统一的存储返回对象，例如包含：
  - `stored_path`
  - `original_filename`
  - `stored_filename`
  - `file_size`
  - `content_hash`
- 兼容旧记录的路径标准化辅助函数，不主动迁移旧数据。

#### 风险点

- 一旦把“标准目录”定错，后续接线会放大问题。
- 如果提前修改模型语义，容易触发历史唯一约束冲突。
- 哈希算法从无到有引入后，需要确认不会把历史同名文件误当作同内容。

#### 最小验证方式

- 单元测试验证标准路径解析。
- 单元测试验证同一个文件在不同调用入口下得到一致的 `stored_path` / `content_hash`。
- 使用样例 PDF 做只读演练，确认不会改动现有记录。

#### 回滚方式

- Phase 1 只新增内部服务和测试，不接线上入口时，直接回退新增模块即可。

### Phase 2：逐步把三条上传入口接到统一 service

#### 目标

- 让 `views_user_upload`、`direct_processing`、`weaviate_views.upload` 共用同一套保存逻辑。
- 仍然不改变对外 API。

#### 建议改动文件

- `D:\workspace\123\ccc\astrobiology\backend\pdf_processor\views_user_upload.py`
- `D:\workspace\123\ccc\astrobiology\backend\pdf_processor\views\direct_processing_views.py`
- `D:\workspace\123\ccc\astrobiology\backend\pdf_processor\weaviate_views.py`
- Phase 1 新增的统一 service 模块

#### Phase 2 不改的文件

- 前端
- `reprocess_pdfs.py`
- `sync_pdfs.py`
- `pdf_utils.py`
- `backend/media/uploads/` 与 `data/pdfs/` 中的历史文件

#### 具体做法

- 仅把“接收上传文件并保存到磁盘”改为统一 service。
- 保留各入口原有业务语义：
  - 用户上传仍建 `PDFDocument`，仍是 `pending`
  - 直接处理仍建 `ProcessingTask`
  - Weaviate 上传仍触发索引线程
- 但三者都拿到同一种标准化的文件保存结果。

#### 风险点

- 入口虽然复用保存逻辑，但后续处理语义仍不同，容易让团队误以为“链路已经完全统一”。
- 如果标准化后改动了磁盘命名策略，需要确认旧的按原名扫描逻辑不会立刻失效。

#### 最小验证方式

- 手工 smoke test：
  - 用户上传 1 个新 PDF
  - 直接处理 1 个新 PDF
  - Weaviate 上传 1 个新 PDF
- 检查三个入口是否都能保存成功，且写出的标准元数据一致。
- 检查已有前端/调用方无需改动。

#### 回滚方式

- 若某入口接入后出问题，可单独把该入口切回旧的本地保存逻辑，不影响其他入口。

### Phase 3：去重策略、命名规则、元数据归一化、重处理命令收口

#### 目标

- 在入口统一后，再统一“什么算重复、数据库怎么记、命令如何补处理、旧路径怎么兼容”。

#### 建议改动文件

- `D:\workspace\123\ccc\astrobiology\backend\pdf_processor\models.py`
- `D:\workspace\123\ccc\astrobiology\backend\pdf_processor\weaviate_views.py`
- `D:\workspace\123\ccc\astrobiology\backend\pdf_processor\management\commands\reprocess_pdfs.py`
- `D:\workspace\123\ccc\astrobiology\backend\pdf_processor\management\commands\sync_pdfs.py`
- `D:\workspace\123\ccc\astrobiology\backend\pdf_processor\views_review.py`
- 统一 service 模块

#### Phase 3 不改的文件

- 历史上传文件本体
- `runs/`
- `evaluation/`
- `checkpoints/`
- 高风险大模块如 `pdf_utils.py`

#### 需要做的统一点

- 明确“系统唯一键”与“展示文件名”分离。
- 明确统一哈希字段与落库时机。
- 把重复判断从“按文件名”升级为“按内容哈希 + 文件大小 + 业务上下文”。
- 让 `reprocess_pdfs.py`、`sync_pdfs.py` 使用同一套目录和路径标准化函数。
- 决定审核通过后是否自动触发处理。这一项需要先补样例和业务确认，不能在 Phase 3 中默认拍板。

#### 风险点

- 会触碰历史数据兼容性。
- 会涉及 `PDFDocument.filename` 唯一约束的迁移策略。
- 容易影响 Weaviate 增量索引、历史重处理、审核流程语义。

#### 最小验证方式

- 针对旧记录做兼容性回归。
- 针对重复上传、重复索引、审核通过后的补处理分别做集成测试。
- 先在测试数据或样例目录上跑命令，不直接作用于现网历史目录。

#### 回滚方式

- 命令与入口切换保持开关化或分步上线。
- 数据库字段变更前先保留兼容读逻辑。
- 在旧路径兼容函数存在的前提下，可回退到旧扫描逻辑。

## 五、必须先补的验证与测试

### 1. 上传一个新 PDF 的 smoke test

- 用户上传后：
  - 文件是否写到预期标准目录
  - `PDFDocument` 是否记录完整
  - `review_status` / `processed` 是否符合当前语义

### 2. 上传相同 PDF 的重复处理测试

- 同文件同文件名重复上传
- 同文件不同文件名重复上传
- 相同内容分别从用户上传、Weaviate 上传、直接处理入口进入
- 目标是先验证“当前会如何重复”，再作为 Phase 3 的验收基线

### 3. direct processing 链路测试

- 单文件直接处理
- 批量直接处理
- 失败重试后是否仍能定位原文件

### 4. Weaviate 同步 / 查询不回归测试

- `upload`
- `process_pending`
- `process_stale`
- `sync_files`
- 上传后查询结果和向量存在性是否不回归

### 5. 旧文件路径兼容性测试

- 历史 `backend/media/uploads/` 文件是否仍能被 `PDFDocument.file_path` 正常读取
- 历史 `data/pdfs/` 文件是否仍能被重处理命令识别
- `Path(settings.BASE_DIR).parent / 'pdfs'` 这条命令路径要先确认是历史遗留还是仍有真实数据

### 6. 重处理命令是否仍能工作

- `reprocess_pdfs.py` 在标准目录切换后是否还能运行
- `sync_pdfs.py` 是否需要先修正目录来源再进入正式改造

### 7. 命名规则变化后的兼容性测试

- 如果引入稳定存储文件名，旧 `file_path` 记录不能失效
- 如果保留原始文件名用于展示，现有前端/API 展示行为不能回归

### 8. 建议先补的最小样例

- 3 份小 PDF：
  - 全新文件
  - 同内容不同文件名
  - 同文件名不同内容
- 1 组历史数据库记录样例：
  - `file_path` 指向 `media/uploads`
  - `file_path` 指向 `data/pdfs`

## 六、当前不建议触碰的对象

- `D:\workspace\123\ccc\astrobiology\backend\media\uploads\` 现有文件本体
- `D:\workspace\123\ccc\astrobiology\data\`
- `D:\workspace\123\ccc\astrobiology\backend\runs\`
- `D:\workspace\123\ccc\astrobiology\backend\evaluation\`
- `D:\workspace\123\checkpoints\`
- `D:\workspace\123\ccc\astrobiology\backend\pdf_processor\pdf_utils.py`
- 前端问题，包括第四批高风险文案问题
- 未经确认的历史 `PDFDocument` 记录清洗
- 现有 Weaviate 集合直接清空式重建操作

## 七、建议的实施顺序

1. 先补样例与验证基线，特别是跨入口重复上传和旧路径兼容测试。
2. 只做 Phase 1，先产出统一存储服务雏形与路径标准化能力，不接业务入口。
3. 选一条风险最低的入口先接入，优先建议从 `views_user_upload.py` 或 `direct_processing_views.py` 开始，不要三条入口同时改。
4. 分批接入剩余入口，完成 Phase 2。
5. 在入口统一稳定后，再单独立项做 Phase 3 的去重、命名、元数据和重处理命令收口。
6. 审核通过后是否自动触发索引，单独作为业务语义确认项，不要夹在底层存储重构里一起改。

## 结论

**结论 B：还需先补验证/样例，再实施**

原因：

- 当前不一致点已经足够明确，主线值得做。
- 但历史路径并存、命令目录来源不一致、审核通过是否触发索引语义未定，这三类问题如果不先补样例和验证，Phase 1 之后很容易把“底层统一”误做成“行为改变”。
- 因此最稳妥的推进方式是：先补验证基线，再进入 Phase 1。
