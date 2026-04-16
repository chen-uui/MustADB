# 内容哈希去重最小策略设计

## 一、最小去重目标与边界

### 1. 最小去重目标

本轮内容哈希去重要解决的最小问题只有两个：

1. 新上传文件是否与现有文件内容完全相同。
2. 同一份 PDF 从不同入口进入时，是否会重复落盘、重复建记录、重复进入后续处理链路。

### 2. 当前应处理的范围

- 用户上传入口的新增文件
- direct processing 上传入口的新增文件
- Weaviate 上传入口的新增文件
- `sync_pdfs.py` / `reprocess_pdfs.py` 对“是否是同一内容文件”的识别能力

### 3. 当前明确不处理的范围

- 历史文件批量去重
- 历史数据迁移
- 自动合并已有 `PDFDocument`
- 自动合并已有 `ProcessingTask`
- 改变审核通过后的业务语义
- 清理 `backend/media/uploads/` 中既有重复 PDF
- 任何现有文件的删除、移动、重命名

### 4. 边界判断

本轮的“最小去重”本质上应理解为：

- 先识别新重复
- 再决定是否阻止新增重复落盘
- 不碰历史存量数据

## 二、各入口接入建议

### 1. 用户上传入口

- 文件：`D:\workspace\123\ccc\astrobiology\backend\pdf_processor\views_user_upload.py`
- 未来应接入内容哈希判断：`是`
- 接入时机建议：`落盘前判断为目标，最小实现可先“临时保存/计算哈希后判断、再决定是否保留文件”`
- 行为建议：
  - Phase 2B-1：只识别、记录日志，不改变当前行为
  - 后续更进一步时：可以考虑“识别到重复后不再保留重复落盘文件”，但不要顺手改审核语义

理由：

- 这是最容易累积重复文件的入口之一。
- 它当前只按 `filename` 查重，挡不住“同内容不同名”。
- 但它还带有待审核语义，不能把“去重”直接做成“跳过审核”。

### 2. direct processing 上传入口

- 文件：`D:\workspace\123\ccc\astrobiology\backend\pdf_processor\views\direct_processing_views.py`
- 未来应接入内容哈希判断：`是，但应更保守`
- 接入时机建议：`在创建 ProcessingTask 前识别`
- 行为建议：
  - Phase 2B-1：只识别、记录日志
  - 不建议作为首个“阻止重复落盘”的入口

理由：

- 这条链路当前没有 `PDFDocument` 主记录，只有 `ProcessingTask`
- 如果直接复用已有文件路径，很可能改变任务级别的可追踪语义
- 对这条链路，先做“识别但不阻断”最稳

### 3. Weaviate 上传入口

- 文件：`D:\workspace\123\ccc\astrobiology\backend\pdf_processor\weaviate_views.py`
- 未来应接入内容哈希判断：`是`
- 接入时机建议：`上传阶段判断`
- 行为建议：
  - 这是 Phase 2B-2 最适合先试点的入口
  - 因为它当前已经存在“同名文件已存在则跳过上传”的语义
  - 可以把“同内容不同名”纳入同类判断，而不需要一上来改变响应结构

理由：

- 这条链路当前本来就有 `existing=true` 的跳过上传语义
- 把判定条件从“同名”扩展到“同内容”对外语义变化最小
- 它也是最容易造成重复索引的入口之一

### 4. `reprocess_pdfs.py`

- 文件：`D:\workspace\123\ccc\astrobiology\backend\pdf_processor\management\commands\reprocess_pdfs.py`
- 当前不建议接入阻断式去重
- 建议只做：`识别重复并打日志`

理由：

- 它是重处理命令，不是上传入口
- 它的职责是重新读取目录并重建索引，不应该在这一步开始改变文件或记录关系
- 如果这里直接做阻断或复用，容易把“重处理逻辑”变成“数据修复逻辑”

### 5. `sync_pdfs.py`

- 文件：`D:\workspace\123\ccc\astrobiology\backend\pdf_processor\management\commands\sync_pdfs.py`
- 当前不建议接入阻断式去重
- 建议只做：`识别重复并在同步结果中标记/日志输出`

理由：

- 它的职责是“文件夹和数据库同步”
- 它当前按文件名同步，不应该在这轮去重里顺手升级成“自动合并记录器”
- 如果这里开始主动去重，很容易误删或误判历史目录中的合法并存文件

### 6. 哪些入口适合落盘前判断

- 用户上传入口：`适合`
- Weaviate 上传入口：`适合`
- direct processing：`理论上适合，但第一轮不建议阻断`

### 7. 哪些入口只需要识别重复但不阻断

- direct processing
- `reprocess_pdfs.py`
- `sync_pdfs.py`

### 8. 哪些入口当前不应接入

- 审核通过流程
- `process_pending`
- `process_stale`

这些入口当前应继续只围绕既有 `file_path` / `processed` 语义工作。

## 三、最小可执行策略设计

### 1. 哈希算法建议

#### 最小方案建议

- **短期最小可执行方案：继续使用 SHA-1**

原因：

- `UploadStorageService` 当前已经在计算 `sha1`
- `PDFDocument` 已经有 `sha1` 字段，且已建立索引
- `weaviate_views.sync_files()` 也已经围绕 `sha1` 在补写
- 采用 SHA-1 可以避免为了去重最小策略再引入数据库迁移

#### 长期更稳方案

- 如果以后要提升抗碰撞性，再单独评估迁移到 SHA-256
- 但这应作为后续单独演进，不应和本轮最小去重绑在一起

### 2. 何时计算哈希

#### 最小可执行建议

- 在上传流写入阶段同步计算
- 如果需要“落盘前判断”，可采用：
  - 先写入临时文件或 staging 文件
  - 计算哈希
  - 查已有记录
  - 再决定是否保留最终文件

#### 当前不建议的做法

- 先正式落盘，再把重复文件留在磁盘上不处理

因为这样虽然识别了重复，但没有真正阻止新增重复占用。

### 3. 哈希值存在哪里最稳妥

#### 最小方案

- 对新进入 `PDFDocument` 的文件：
  - 直接写入现有 `PDFDocument.sha1`
- 对不建 `PDFDocument` 的 direct processing：
  - 先只在 helper 内计算并输出日志
  - 暂不改 `ProcessingTask` 模型

#### 为什么不建议现在加新字段

- 模型里已有 `sha1`
- 本轮目标是最小策略，不是模型升级
- 新字段会引入迁移、历史数据为空值、索引策略等额外风险

### 4. 如果发现内容重复，系统的最小行为应该是什么

#### Phase 2B-1

- 只打日志/标记识别结果
- 不改变保存或建记录行为

#### Phase 2B-2 最稳策略

- 在 **Weaviate 上传入口** 先试点：
  - 如果哈希匹配到已有 `PDFDocument.sha1`
  - 则不再重复落盘
  - 直接复用已存在文档并返回当前已有的“existing”型语义

#### 不建议的首轮策略

- 在用户上传入口直接“内容重复则自动通过审核”
- 在 direct processing 中直接把新任务强行绑定到旧任务
- 在 `sync_pdfs.py` 中发现重复就跳过建库或删记录

### 5. 对现有语义影响最小的方案

最小影响方案是：

- 使用现有 `PDFDocument.sha1`
- 仅对新上传记录写入哈希
- 优先在已存在“跳过上传”语义的 Weaviate 上传入口试点
- 对用户上传和 direct processing 先只识别，不立即阻断

这样能尽量不碰：

- `file_path` 语义
- `filename` 唯一约束的现有含义
- `ProcessingTask.document_path` 的独立任务语义
- 审核与索引流程

## 四、验证与回归检查清单

### 1. 同一份 PDF 经用户上传两次

#### 修改前应观察到

- 如果文件名相同：当前会被 `filename` 查重挡住
- 如果文件名不同：会重复落盘、重复建待审核记录

#### 去重最小实现后应观察到

- Phase 2B-1：日志中能识别“同内容重复”
- 后续若启用阻断：同内容不同名也应能识别为重复

#### 是否属于行为变化

- `是`
- 特别是“同内容不同名”从原来可创建记录变成识别重复，必须单独告知用户

### 2. 同一份 PDF 分别经用户上传和 direct processing 上传

#### 修改前应观察到

- 会分别落盘到 `media/uploads`
- 用户上传建 `PDFDocument`
- direct processing 建 `ProcessingTask`

#### 去重最小实现后应观察到

- Phase 2B-1：能识别跨入口同内容，但不阻断
- 后续也不应贸然把 direct processing 自动复用成旧任务

#### 是否属于行为变化

- Phase 2B-1：`否`
- 若后续阻断 direct processing 落盘：`是`

### 3. 同一份 PDF 分别经用户上传和 Weaviate 上传

#### 修改前应观察到

- 很可能一份落到 `media/uploads`，一份落到 `data/pdfs`
- 可能造成重复建记录、重复处理、重复索引

#### 去重最小实现后应观察到

- Phase 2B-1：识别出跨入口同内容
- Phase 2B-2 若在 Weaviate 试点：Weaviate 入口可直接复用已有文档或至少不再重复落盘

#### 是否属于行为变化

- `是`
- 但这是最有价值、也最值得明确告知的行为变化

### 4. 同名不同内容 PDF

#### 修改前应观察到

- 可能被当前 filename 查重误挡

#### 去重最小实现后应观察到

- Phase 2B-1：日志能识别“文件名冲突但哈希不同”
- 不应直接当成同内容重复处理

#### 是否属于行为变化

- 如果未来放开这类文件的处理路径，属于显著行为变化，必须单独告知用户

### 5. 不同名相同内容 PDF

#### 修改前应观察到

- 会被当成新文件

#### 去重最小实现后应观察到

- 应识别为内容重复
- 若试点入口已启用阻断，则不再新增重复落盘

#### 是否属于行为变化

- `是`

### 6. reprocess / sync 是否会被错误当成新文件

#### 修改前应观察到

- `reprocess_pdfs.py` 只扫目录重处理
- `sync_pdfs.py` 只按文件名建/删记录

#### 去重最小实现后应观察到

- Phase 2B-1：最多只输出重复识别日志
- 不应让这两个命令改变其主要职责

#### 是否属于行为变化

- 不应有显著行为变化

### 7. 旧路径兼容是否受影响

#### 修改前应观察到

- 旧 `media/uploads` 与 `data/pdfs` 的 `file_path` 仍可被读取

#### 去重最小实现后应观察到

- 仍必须保持可读取
- 去重不能要求历史记录立刻补齐哈希才能运行

#### 是否属于行为变化

- 不应有

## 五、主要风险与不该一起做的事

### 1. 如果没有新字段，去重状态如何判断

- 可以依赖现有 `PDFDocument.sha1`
- 问题是历史记录里该字段可能大量为空
- 所以最小方案只能保证：
  - 对新进入的 `PDFDocument` 可逐步变得可靠
  - 对历史记录只能“有哈希就用，没有就回退”

### 2. 如果增加新字段，数据库迁移风险是什么

- 会引入迁移和回填问题
- 需要决定历史空值如何处理
- 需要重新设计索引和约束
- 这已经超出“最小去重策略”的范围

### 3. 如果直接复用旧文件路径，会不会影响当前 `ProcessingTask` / `PDFDocument` 语义

- 会

尤其在 direct processing 中：

- `ProcessingTask.document_path` 当前代表一次任务对应的实际输入文件
- 如果直接让不同任务复用旧路径，虽然技术上可行，但会改变任务与物理文件的一对一直觉语义

### 4. 为什么当前不应该把“内容哈希去重”和“历史文件清理”绑在一起做

- 去重解决的是“新重复不要继续产生”
- 历史清理解决的是“旧重复怎么处理”
- 两者验证口径、回滚方式、风险面完全不同
- 绑在一起会把一个可控的小改造，变成高风险数据治理项目

### 5. 为什么当前不应该把“内容哈希去重”和“审核通过自动索引”绑在一起做

- 去重是底层文件与记录判定问题
- 审核通过自动索引是业务流程语义问题
- 如果两者一起改，一旦行为变化，很难判断是去重出错还是流程语义改了

## 六、分阶段实施方案

### Phase 2B-1：只做哈希计算与日志/识别，不改变行为

#### 改哪些文件

- `D:\workspace\123\ccc\astrobiology\backend\pdf_processor\services\upload_storage_service.py`
- `D:\workspace\123\ccc\astrobiology\backend\pdf_processor\views_user_upload.py`
- `D:\workspace\123\ccc\astrobiology\backend\pdf_processor\views\direct_processing_views.py`
- `D:\workspace\123\ccc\astrobiology\backend\pdf_processor\weaviate_views.py`
- 视需要补充最小 smoke / 静态检查脚本

#### 不改哪些文件

- 模型结构
- `sync_pdfs.py` 的同步策略
- `reprocess_pdfs.py` 的重处理职责
- 审核流程
- 前端

#### 验证方式

- 新增 smoke：
  - 同名不同内容
  - 不同名相同内容
  - 跨入口相同内容
- 只验证是否能识别并输出一致日志/标记

#### 回滚方式

- 直接回退日志识别接线
- 因为 Phase 2B-1 不改变行为，所以回滚成本最低

### Phase 2B-2：对一个最安全入口启用“重复识别但不落盘重复文件”

#### 最建议试点入口

- `weaviate_views.py` 的 `upload`

#### 改哪些文件

- `D:\workspace\123\ccc\astrobiology\backend\pdf_processor\weaviate_views.py`
- `D:\workspace\123\ccc\astrobiology\backend\pdf_processor\services\upload_storage_service.py`

#### 不改哪些文件

- 用户上传审核逻辑
- direct processing 任务语义
- `sync_pdfs.py`
- `reprocess_pdfs.py`

#### 验证方式

- 同内容不同名，从 Weaviate 入口上传
- 观察是否：
  - 不再重复落盘
  - 不再重复建记录
  - 仍保持“existing 型”返回语义

#### 回滚方式

- 只回退 Weaviate 上传入口的哈希阻断逻辑
- helper 保留哈希计算能力不动

### Phase 2B-3：再评估是否扩展到其他入口

#### 可评估扩展对象

- 用户上传入口
- direct processing 上传入口

#### 改哪些文件

- `views_user_upload.py`
- `views/direct_processing_views.py`
- 相关 smoke/check 脚本

#### 不改哪些文件

- 历史文件
- 历史数据库记录
- 审核语义
- 索引语义

#### 验证方式

- 先对用户上传做最小试点，再看是否需要扩到 direct processing
- 尤其要验证：
  - 待审核文档是否仍保持待审核
  - 任务日志是否仍可追踪

#### 回滚方式

- 分入口回滚
- 不做多入口同时切换

## 七、建议的下一步

1. 先进入 Phase 2B-1，只做识别与日志，不改行为。
2. 补一组围绕“同内容不同名 / 同名不同内容 / 跨入口同内容”的 smoke 基线。
3. 如果识别结果稳定，再在 Weaviate 上传入口做 Phase 2B-2 试点。
4. 在 Weaviate 入口试点稳定前，不要把阻断式去重扩展到用户上传或 direct processing。

## 结论

**结论 A：现在适合进入 Phase 2B-1 实施**

原因：

- 当前路径来源已经基本收口。
- `UploadStorageService` 已经在计算 `sha1`。
- `PDFDocument` 已有 `sha1` 字段，无需为了最小去重先做数据库迁移。
- 因此现在最稳妥的下一步，就是先做“哈希识别 + 日志/标记”，而不是直接做阻断、迁移或业务语义改造。
