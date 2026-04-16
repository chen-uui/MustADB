# historical_log_archive_report

## 归档目录路径

- `D:\workspace\123\_archive\historical_logs\`

## 归档前检查结果

### 目标历史日志

- `D:\workspace\123\logs\astrobiology.log`
  - 归档前存在：是
  - 归档前大小：13,907 B
  - 归档前最后修改时间：2025-11-02 15:25:45 UTC
  - 活跃性复核：短间隔复核无写入变化，判定为非当前活跃写入

- `D:\workspace\123\ccc\astrobiology\logs\astrobiology.log`
  - 归档前存在：是
  - 归档前大小：0 B
  - 归档前最后修改时间：2025-09-30 08:00:48 UTC
  - 活跃性复核：短间隔复核无写入变化，判定为非当前活跃写入

### 标准主日志与 benchmark 日志复核

- 当前标准主日志仍为：
  - `D:\workspace\123\ccc\astrobiology\backend\logs\astrobiology.log`
  - 复核时存在，大小 `3,832,700 B`
  - 最后修改时间：2026-03-14 10:22:42 UTC

- benchmark 日志仍为：
  - `D:\workspace\123\ccc\astrobiology\backend\logs\bench_log.jsonl`
  - 复核时存在，大小 `249,913 B`
  - 最后修改时间：2026-02-25 07:21:35 UTC

## 实际归档了哪些文件

- 已归档：
  - 源文件 `D:\workspace\123\logs\astrobiology.log`
  - 归档为 `D:\workspace\123\_archive\historical_logs\root_logs_astrobiology.log`

- 已归档：
  - 源文件 `D:\workspace\123\ccc\astrobiology\logs\astrobiology.log`
  - 归档为 `D:\workspace\123\_archive\historical_logs\ccc_astrobiology_logs_astrobiology.log`

## 跳过了哪些文件及原因

- 无

## 归档后验证结果

### 源路径状态

- `D:\workspace\123\logs\astrobiology.log`
  - 归档后源路径是否存在：否

- `D:\workspace\123\ccc\astrobiology\logs\astrobiology.log`
  - 归档后源路径是否存在：否

### 归档文件状态

- `D:\workspace\123\_archive\historical_logs\root_logs_astrobiology.log`
  - 存在：是
  - 大小：13,907 B
  - 与归档前大小一致：是

- `D:\workspace\123\_archive\historical_logs\ccc_astrobiology_logs_astrobiology.log`
  - 存在：是
  - 大小：0 B
  - 与归档前大小一致：是

### 受保护日志复核

- `D:\workspace\123\ccc\astrobiology\backend\logs\astrobiology.log`
  - 归档后仍存在：是
  - 未触碰：是

- `D:\workspace\123\ccc\astrobiology\backend\logs\bench_log.jsonl`
  - 归档后仍存在：是
  - 未触碰：是

### 归档行为说明

- 本轮只做移动归档
- 未执行删除
- 未执行压缩
- 未修改日志内容

## 回滚方式说明

如需回滚，可将归档文件移回原位：

- `D:\workspace\123\_archive\historical_logs\root_logs_astrobiology.log`
  - 移回 `D:\workspace\123\logs\astrobiology.log`

- `D:\workspace\123\_archive\historical_logs\ccc_astrobiology_logs_astrobiology.log`
  - 移回 `D:\workspace\123\ccc\astrobiology\logs\astrobiology.log`

回滚时应先确认目标原路径不存在同名新文件，以免覆盖。

## 本轮明确未处理的对象

- `D:\workspace\123\ccc\astrobiology\backend\logs\astrobiology.log`
- `D:\workspace\123\ccc\astrobiology\backend\logs\bench_log.jsonl`
- `D:\workspace\123\ccc\astrobiology\astro_frontend\dist\`
- `D:\workspace\123\ccc\astrobiology\backend\uploads\`
- `D:\workspace\123\ccc\astrobiology\backend\staticfiles\`
- `D:\workspace\123\ccc\astrobiology\backend\media\uploads\`
- `D:\workspace\123\ccc\astrobiology\backend\models\cache\`
- 所有 `management/commands/`
- `D:\workspace\123\.venv\`
- `D:\workspace\123\ccc\astrobiology\data\`
- `D:\workspace\123\ccc\astrobiology\backend\runs\`
- `D:\workspace\123\ccc\astrobiology\backend\evaluation\`
- `D:\workspace\123\checkpoints\`

## 结论

本轮按“归档而非删除”的要求完成，仅处理了两份历史残留 `astrobiology.log`。两份日志均先通过非活跃写入复核，再移动到统一归档目录；当前标准主日志和 benchmark 日志均未被触碰。

