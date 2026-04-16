# dedup_audit_report

## 一、审计范围

本轮仅做只读去重审计，未执行任何删除、移动、重命名、覆盖或代码修改。

- 审计范围 A：`D:\workspace\123\ccc\astrobiology\backend\models\cache\`
- 审计范围 B：`D:\workspace\123\ccc\astrobiology\backend\media\uploads\`
- 审计范围 C：项目内所有 `.log` 文件，以及文件名包含 `log` / `logs` / `debug` / `error` / `runtime` 的文本输出文件

审计方法：

- 先按文件大小分组
- 再用 `SHA256` 确认是否为完全重复
- 对 PDF 额外尝试提取页数和标题元数据
- 对日志仅做盘点和风险判断，不做清理建议落地

明确未触碰范围：

- `D:\workspace\123\ccc\astrobiology\backend\models\`
- `D:\workspace\123\data\`
- `D:\workspace\123\ccc\astrobiology\backend\evaluation\`
- `D:\workspace\123\ccc\astrobiology\backend\runs\`
- `D:\workspace\123\checkpoints\`
- 所有 `management/commands/`

---

## 二、模型缓存重复审计

扫描结果：

- 文件总数：17
- 总体积：约 175.13 MB
- 发现完全重复组：2 组
- 未发现主模型权重文件的完全重复副本

### 分组 M-01

- 类型：模型缓存
- 路径列表：
  - `D:\workspace\123\ccc\astrobiology\backend\models\cache\all-MiniLM-L6-v2\special_tokens_map.json`
  - `D:\workspace\123\ccc\astrobiology\backend\models\cache\cross-encoder-ms-marco-MiniLM-L-6-v2\special_tokens_map.json`
- 文件大小：732 B / 文件
- 哈希值：`5AA43C2F985A25296D5A5CE621C2F77376CA8091A47993C492FD5460B895B140`
- 是否完全重复：是
- 为什么有重复嫌疑：两个不同模型缓存目录中存在内容完全一致的 tokenizer 辅助文件
- 是否文件名不同但内容完全相同：否，文件基名相同，完整路径不同
- 是否可能是同一模型的多份副本：更像是跨模型共享的 tokenizer 元数据副本，不足以认定为“同一模型多份副本”
- 风险等级：高
- 是否可能被代码、配置、Docker、脚本、文档、环境变量引用：是，模型加载逻辑通常按目录读取整套缓存文件
- 是否建议后续人工确认：是
- 是否建议保留一个主副本、其余作为候选清理对象：仅可作为后续人工确认候选，本轮不建议直接处理

### 分组 M-02

- 类型：模型缓存
- 路径列表：
  - `D:\workspace\123\ccc\astrobiology\backend\models\cache\all-MiniLM-L6-v2\vocab.txt`
  - `D:\workspace\123\ccc\astrobiology\backend\models\cache\cross-encoder-ms-marco-MiniLM-L-6-v2\vocab.txt`
- 文件大小：231,508 B / 文件
- 哈希值：`07ECED375CEC144D27C900241F3E339478DEC958F92FDDBC551F295C992038A3`
- 是否完全重复：是
- 为什么有重复嫌疑：两个不同模型缓存目录中包含完全相同的词表文件
- 是否文件名不同但内容完全相同：否，文件基名相同，完整路径不同
- 是否可能是同一模型的多份副本：更像同系列模型共享词表，不足以判定为冗余可删
- 风险等级：高
- 是否可能被代码、配置、Docker、脚本、文档、环境变量引用：是，模型运行时通常依赖目录内原位词表
- 是否建议后续人工确认：是
- 是否建议保留一个主副本、其余作为候选清理对象：仅可作为后续人工确认候选，本轮不建议直接处理

### 其他观察

- `all-MiniLM-L6-v2\model.safetensors` 与 `cross-encoder-ms-marco-MiniLM-L-6-v2\model.safetensors` 体积接近，但哈希不同，不属于完全重复文件
- 其余 `config.json`、`tokenizer.json`、`tokenizer_config.json`、`sentence_bert_config.json` 等文件均未发现完全重复
- 以“同目录名像 cache”为由直接判定可删，不成立

模型缓存区的理论重复体积上限：

- 若仅按“完全重复且保留 1 份”估算，理论可释放约 232,240 B，约 0.22 MB
- 但该空间涉及模型目录完整性，默认仍归类为“需要人工确认”

---

## 三、上传 PDF 重复审计

扫描结果：

- PDF 总数：30
- 总体积：约 145.08 MB
- 发现完全重复组：1 组
- 发现异常单文件：1 个

### 分组 P-01

- 类型：上传 PDF
- 路径列表：
  - `D:\workspace\123\ccc\astrobiology\backend\media\uploads\08c53e45-7a32-4f98-96d6-1bf28903fdc6.pdf`
  - `D:\workspace\123\ccc\astrobiology\backend\media\uploads\12730fe2-062a-410e-95f5-1f17bebdea48.pdf`
  - `D:\workspace\123\ccc\astrobiology\backend\media\uploads\12da6005-a674-4e5e-be50-0548ee2c5657.pdf`
  - `D:\workspace\123\ccc\astrobiology\backend\media\uploads\183deb9c-5d9b-4ee1-b612-81ed8541d53a.pdf`
  - `D:\workspace\123\ccc\astrobiology\backend\media\uploads\1bd097c6-4422-4af6-a1e4-9d2a430c24f1.pdf`
  - `D:\workspace\123\ccc\astrobiology\backend\media\uploads\1e1db684-a89a-4c31-9395-1e1da83a0223.pdf`
  - `D:\workspace\123\ccc\astrobiology\backend\media\uploads\3a8a492f-f73f-4ac0-a352-adcbc90b18ce.pdf`
  - `D:\workspace\123\ccc\astrobiology\backend\media\uploads\3de4ff01-c114-4c4a-9aaa-7f65d7f3c1e2.pdf`
  - `D:\workspace\123\ccc\astrobiology\backend\media\uploads\425081f9-f368-442f-bbaf-0f528b09ebd7.pdf`
  - `D:\workspace\123\ccc\astrobiology\backend\media\uploads\45d79fdb-8a79-44c9-9692-73a98855c11a.pdf`
  - `D:\workspace\123\ccc\astrobiology\backend\media\uploads\4930378d-32e1-4f65-bad7-178cdac3c187.pdf`
  - `D:\workspace\123\ccc\astrobiology\backend\media\uploads\4e00edf8-d00f-435d-9c54-d7572688e84e.pdf`
  - `D:\workspace\123\ccc\astrobiology\backend\media\uploads\5411b4f7-c5c3-4894-8a0c-87f2232288a5.pdf`
  - `D:\workspace\123\ccc\astrobiology\backend\media\uploads\61c29ca2-b069-4b95-a3ad-8e93316d8200.pdf`
  - `D:\workspace\123\ccc\astrobiology\backend\media\uploads\6da44894-e48b-4a15-9bdd-9dcb508413f7.pdf`
  - `D:\workspace\123\ccc\astrobiology\backend\media\uploads\81071930-de00-45d1-a102-574e3b22ad95.pdf`
  - `D:\workspace\123\ccc\astrobiology\backend\media\uploads\82c22657-368a-4893-b867-d6a41ae25e66.pdf`
  - `D:\workspace\123\ccc\astrobiology\backend\media\uploads\9924c054-aef6-487d-a0b9-55dc8ccb2324.pdf`
  - `D:\workspace\123\ccc\astrobiology\backend\media\uploads\a6e4c3bb-1b7b-40a4-b0c3-7333f2c1028b.pdf`
  - `D:\workspace\123\ccc\astrobiology\backend\media\uploads\b523328e-a3fc-4d34-a37d-ac8c1520a85a.pdf`
  - `D:\workspace\123\ccc\astrobiology\backend\media\uploads\b94dce80-c22b-4309-8c44-03475b1f905c.pdf`
  - `D:\workspace\123\ccc\astrobiology\backend\media\uploads\bad5e905-cdc8-47c8-bcee-29fca3502329.pdf`
  - `D:\workspace\123\ccc\astrobiology\backend\media\uploads\bb8bfac0-ca04-4274-a01a-781968b67540.pdf`
  - `D:\workspace\123\ccc\astrobiology\backend\media\uploads\c5e6111f-e6ac-45d3-8be1-683d0258990f.pdf`
  - `D:\workspace\123\ccc\astrobiology\backend\media\uploads\dbffd631-c709-4de1-b447-dd1e77525b01.pdf`
  - `D:\workspace\123\ccc\astrobiology\backend\media\uploads\f547567a-3893-4b5c-9055-dcb0154690da.pdf`
  - `D:\workspace\123\ccc\astrobiology\backend\media\uploads\f7c18a5e-e2c8-487a-948a-d8fe1baddd62.pdf`
- 文件大小：5,560,802 B / 文件
- 哈希值：`831E8ADC78DF74A6E06AC936EC28163FAF5C8DCC5CE78F8ECA39BB972B95B76C`
- 是否完全重复：是
- 为什么有重复嫌疑：27 个 UUID 风格文件名对应的 PDF 内容完全一致，明显存在重复上传或重复存储现象
- 是否文件名不同但内容完全相同：是
- 可能的文档元数据：
  - 页数：17
  - 标题：`Ceres: Organic‐Rich Sites of Exogenic Origin?`
- 组内数量：27
- 组内总占用空间：150,141,654 B，约 143.19 MB
- 最早修改时间：2025-10-23 19:51:44
- 最晚修改时间：2025-10-25 15:48:04
- 风险等级：高
- 是否可能被代码、配置、Docker、脚本、文档、环境变量引用：是，上传文件通常可能被数据库记录、业务表、向量索引、审计记录或页面链接引用
- 是否建议后续人工确认：是
- 是否建议保留一个主副本、其余作为候选清理对象：是，但仅限下一轮结合数据库/业务引用关系人工确认后执行

### 非重复但值得记录的单文件

- `D:\workspace\123\ccc\astrobiology\backend\media\uploads\555d59c0-187b-4b2c-91d4-b93b2cc9a160.pdf`
  - 哈希：`872101C20E0DD8B5492D8865651D7806FA76EAF910A61049146DE01DE9764715`
  - 大小：590,603 B
  - 页数：10
  - 标题：`Organic synthesis on Mars by electrochemical reduction of CO2`
  - 结论：非重复，不建议处理

- `D:\workspace\123\ccc\astrobiology\backend\media\uploads\62651ac5-44a6-421b-83eb-b879e17a3f74.pdf`
  - 哈希：`8C50F7DA1A817F9CCBA00CBC98D2DAAD909E0DD1ABBE0E1F9F62DC8C76E15A74`
  - 大小：1,399,544 B
  - 页数：8
  - 标题：`Evidence of martian perchlorate, chlorate, and nitrate in Mars meteorite EETA79001: Implications for oxidants and organics`
  - 结论：非重复，不建议处理

- `D:\workspace\123\ccc\astrobiology\backend\media\uploads\da492daa-9009-4da4-9181-902d679d5c22.pdf`
  - 哈希：`2C567635D348F074CE15683343052CB72879EB2F40AAAAEBE47B182C1917BB18`
  - 大小：385 B
  - 状态：无法正常打开，疑似异常占位文件或损坏 PDF
  - 结论：不是重复组，但涉及上传链路或异常处理逻辑，必须人工确认，不建议直接处理

上传 PDF 区的理论重复体积上限：

- 若仅按 P-01 保留 1 份、其余 26 份作为候选清理对象，理论可释放约 144,580,852 B，约 137.88 MB
- 但该区属于业务上传目录，默认归类为“高风险，必须人工确认”

---

## 四、日志文件盘点

扫描结果：

- 共识别日志/日志型文本输出文件：4 个
- 总体积：约 3.91 MB
- 未发现需要本轮按“重复组”处理的日志副本
- 发现 1 个体积明显偏大的运行日志

### 日志清单

| 路径 | 大小 | 类型判断 | 备注 | 风险 |
| --- | ---: | --- | --- | --- |
| `D:\workspace\123\ccc\astrobiology\backend\logs\astrobiology.log` | 3,831,681 B | 运行日志 | 体积最大，适合后续做归档/轮转策略审查，但本轮不建议删除 | 中 |
| `D:\workspace\123\ccc\astrobiology\backend\logs\bench_log.jsonl` | 249,913 B | 基准测试/输出日志 | 可能与性能对比或实验记录有关，只建议人工确认归档价值 | 高 |
| `D:\workspace\123\logs\astrobiology.log` | 13,907 B | 分散日志 | 路径分散，疑似历史运行产物，但仍可能用于排障或启动脚本 | 中 |
| `D:\workspace\123\ccc\astrobiology\logs\astrobiology.log` | 0 B | 空日志文件 | 可能是预创建日志或遗留产物，不建议仅凭空文件即删除 | 中 |

### 日志审计结论

- `backend\logs\astrobiology.log` 可标记为“明显可归档但暂不建议删除”
- `bench_log.jsonl` 虽然不大，但更接近实验/基准输出，默认提高保守级别
- 根目录与 `ccc\astrobiology\logs\` 下分散日志可能反映不同启动入口，不建议本轮做任何处理
- 未额外发现名称包含 `debug`、`error`、`runtime` 的独立文本输出文件

---

## 五、最可能可清理对象（仅候选，不执行）

以下对象仅代表“下一轮最值得人工核验”的候选，不构成自动清理建议。

### 候选 C-01

- 对象类型：上传 PDF 重复组
- 对应分组：P-01
- 候选原因：27 份 PDF 内容完全相同，且文件名均不同，重复特征最强
- 理论可释放空间：约 137.88 MB
- 风险等级：高
- 当前建议：保留 1 个主副本、其余 26 个仅作为人工确认候选

### 候选 C-02

- 对象类型：模型缓存重复辅助文件
- 对应分组：M-01、M-02
- 候选原因：跨模型缓存目录存在完全相同的小型 tokenizer 资源
- 理论可释放空间：约 0.22 MB
- 风险等级：高
- 当前建议：空间收益极低，不建议优先处理；若后续真要处理，必须先确认模型加载方式支持共享或重建

### 候选 C-03

- 对象类型：分散日志
- 对应对象：`D:\workspace\123\ccc\astrobiology\backend\logs\astrobiology.log`
- 候选原因：运行日志体积最大，较适合进入日志轮转或归档方案
- 理论可释放空间：约 3.65 MB
- 风险等级：中
- 当前建议：仅建议后续做归档策略确认，不建议直接删除

---

## 六、必须人工确认的对象

- 分组 P-01：业务上传目录中的 27 份完全重复 PDF
  - 原因：可能被数据库、页面链接、检索索引、任务记录引用

- `D:\workspace\123\ccc\astrobiology\backend\media\uploads\da492daa-9009-4da4-9181-902d679d5c22.pdf`
  - 原因：疑似损坏或异常占位文件，但仍可能对应失败上传、异常回放或审计场景

- 分组 M-01、M-02：模型缓存中的重复 tokenizer 资源
  - 原因：模型目录通常按整套文件原位加载，不能只凭哈希重复就判定为可删

- `D:\workspace\123\ccc\astrobiology\backend\logs\bench_log.jsonl`
  - 原因：可能属于实验、评测、性能对比输出，默认按高风险保守对待

- `D:\workspace\123\logs\astrobiology.log`
- `D:\workspace\123\ccc\astrobiology\logs\astrobiology.log`
  - 原因：分散在不同层级，可能与不同启动方式或历史运维脚本相关

---

## 七、明确不建议处理的对象

- `D:\workspace\123\ccc\astrobiology\backend\models\` 主模型目录
- `D:\workspace\123\data\`
- `D:\workspace\123\ccc\astrobiology\backend\evaluation\`
- `D:\workspace\123\ccc\astrobiology\backend\runs\`
- `D:\workspace\123\checkpoints\`
- 所有 `management/commands/`
- 所有与实验、评测、部署、论文复现、向量库、数据库引用关系可能相关的文件
- `backend\media\uploads\` 中所有未被证实可替换引用关系的单文件 PDF
- 模型权重文件 `*.safetensors`，即使体积接近，也不应按“看起来像副本”处理

---

## 八、建议的下一步操作

1. 先做业务引用核验，再决定是否处理 P-01。
   - 重点检查数据库上传记录、文档表、向量索引、任务结果表、前端下载链接是否直接引用 UUID 文件名。

2. 若确认 P-01 允许去重，先制定“保留主副本 + 引用映射修复 + 可回滚备份”的方案，再进入下一轮人工确认。

3. 对模型缓存不要以节省空间为主要目标。
   - M-01 与 M-02 的理论收益仅约 0.22 MB，远低于潜在加载风险。

4. 对日志优先考虑“轮转/归档策略审查”，不要直接删除。
   - 特别是 `backend\logs\astrobiology.log` 与 `bench_log.jsonl`。

5. 对异常小 PDF 先核查上传链路。
   - `da492daa-9009-4da4-9181-902d679d5c22.pdf` 更适合作为异常案例排查，而不是清理对象。

---

## 汇总表

| 对象类别 | 重复组数量 | 预计可释放空间 | 风险等级 | 是否建议进入下一轮人工确认 |
| --- | ---: | ---: | --- | --- |
| 模型缓存 | 2 | 约 0.22 MB | 高 | 是 |
| 上传 PDF | 1 | 约 137.88 MB | 高 | 是 |
| 日志文件 | 0 | 0 MB（本轮仅盘点） | 中 | 是 |

