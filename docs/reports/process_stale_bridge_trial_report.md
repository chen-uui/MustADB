# process_stale Bridge-Semantics Trial Report

## 1. 实际检查和修改过的文件

检查过：

- `D:\workspace\123\ccc\astrobiology\backend\pdf_processor\weaviate_views.py`
- `D:\workspace\123\ccc\astrobiology\backend\pdf_processor\models.py`
- `D:\workspace\123\ccc\astrobiology\backend\pdf_processor\services\upload_storage_service.py`
- `D:\workspace\123\ccc\astrobiology\backend\tests\upload_storage_smoke_check.py`

实际修改：

- `D:\workspace\123\ccc\astrobiology\backend\pdf_processor\weaviate_views.py`
- `D:\workspace\123\ccc\astrobiology\backend\tests\upload_storage_smoke_check.py`

## 2. 具体改了什么

### `weaviate_views.py`

只对 `process_stale` 相关逻辑做了窄范围调整：

- 新增 `_collect_stale_candidates()`
- stale candidate 现在只把 `duplicate_of is null` 的 canonical record 作为独立内容候选
- `duplicate_of is not null` 的 duplicate child 不再独立进入 stale content repair
- 对 orphan / broken-link child 增加最小异常识别：
  - 记录 `process_stale_orphan_child ...` warning
  - 不把它当成正常 stale candidate 静默处理

### `upload_storage_smoke_check.py`

新增 4 个最小 stale 语义 smoke：

- `process_stale_canonical_gap_candidate`
- `process_stale_duplicate_child_skips_when_canonical_healthy`
- `process_stale_duplicate_child_delegates_to_canonical`
- `process_stale_orphan_child_flagged`

另外给 `FakeChainedQuerySet` 补了 `__iter__`，让新的候选集合测试可直接遍历。

## 3. 哪些规则已经落地

已落地：

- Rule 1：`duplicate_of is null` 的 canonical record 继续作为正常 stale candidate
- Rule 2：`duplicate_of is not null` 的 duplicate child 不再作为独立 stale content candidate
- Rule 3：child 的 stale / 内容失效解释优先看 canonical
- Rule 4：orphan / broken-link child 不再被当正常 stale candidate，改为显式异常识别
- Rule 5：本轮没有试图重写 child 的 `processed` 字段解释，只确保 `process_stale` 不再把 child 当独立内容修复对象

## 4. 哪些仍然故意没碰

本轮刻意不碰：

- `process_pending`
- 前端
- API 契约
- `processed` 字段体系重写
- review flow
- 审核通过后是否自动索引
- 历史数据迁移
- UploadEvent / ReviewAction 长期重构

## 5. 明确说明

- 是否改了前端：否
- 是否改了 API 契约：否
- 是否改了 `process_pending`：否
- 是否改了业务分支语义：只在 `process_stale` 的 stale candidate 选择语义上做了受控变化；未改 review flow、upload 语义、API 语义

## 6. 验证结果

### py_compile

执行：

- `py -m py_compile weaviate_views.py upload_storage_smoke_check.py`

结果：

- 通过

### smoke

执行：

- `D:\workspace\123\ccc\astrobiology\backend\tests\upload_storage_smoke_check.py`

结果：

- `28 pass / 0 fail / 0 error`

其中新增 stale 相关验证全部通过：

- canonical `processed=True` 但底层向量失效时，仍进入 stale candidate
- duplicate child 指向已处理 canonical 时，不进入独立 stale candidate
- duplicate child 指向未处理 canonical 时，不作为独立 stale candidate，由 canonical 承担 stale 责任
- orphan / broken-link child 会被识别为异常对象，而不是被当成正常 stale candidate
- 原有 upload/storage/duplicate 主线 smoke 未回归

## 7. 结论

结论：适合提交。

本轮已经把最小桥接式 stale 语义成功收进 `process_stale`，范围保持在单入口、低风险、可回滚。

下一轮建议：

- 可以单独评估 `process_pending`

但当前不建议马上继续改，除非先明确：

- duplicate child 是否永远不进入内容 pending
- 以及 child 的 `processed=False` 在 UI / API /运维解释上是否需要额外说明
