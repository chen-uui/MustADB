# frontend_build_baseline_report

## 缺失文件问题的根因判断

本轮构建阻塞的根因是：

- [MeteoriteSearch.vue](D:/workspace/123/ccc/astrobiology/astro_frontend/src/views/MeteoriteSearch.vue) 异步引用了不存在的 `@/components/workspace/tabs/MeteoriteSearchTabNew.vue`
- 实际存在的等价组件是 [MeteoriteSearchTab.vue](D:/workspace/123/ccc/astrobiology/astro_frontend/src/components/workspace/tabs/MeteoriteSearchTab.vue)
- 同时，前端其他入口已经在正常引用 `MeteoriteSearchTab.vue`
  - 例如 `FrontendWorkspaceMain.vue` 和 `WorkspaceMain.vue`

判断结果：

- 这不是“文件被误删”
- 这不是“需要补一个新的复杂组件”
- 这属于 `import 残留`

也就是说，`MeteoriteSearch.vue` 中还保留着历史上的 `MeteoriteSearchTabNew.vue` 引用，但项目实际组件已经是 `MeteoriteSearchTab.vue`

## 实际修改了哪些文件

本轮只做了一个源代码修复：

- 修改 [MeteoriteSearch.vue](D:/workspace/123/ccc/astrobiology/astro_frontend/src/views/MeteoriteSearch.vue)
  - 将异步 import 从 `MeteoriteSearchTabNew.vue` 改为现有的 `MeteoriteSearchTab.vue`

本轮未修改：

- 后端任何代码、配置、脚本、数据库、接口
- 其他页面
- `DocumentManagementTab.vue`
- `PendingReview.vue`
- `RecycleBinManagement.vue`
- `UnifiedReview.vue`

## 为什么选择这种最小修复方案

这是当前最小、最安全的恢复方案，原因有三点：

1. 项目中已经存在功能等价且正在被其他入口使用的现成组件 `MeteoriteSearchTab.vue`
2. 构建失败的直接原因只是错误的 import 指向，而不是缺少一整套业务实现
3. 直接修正 import 比新增一个兼容壳组件更小、更清晰，也不会制造新的中间层债务

## 是否新增了兼容壳组件

没有。

本轮不需要新增 `MeteoriteSearchTabNew.vue` 兼容壳，因为现有等价组件明确存在，直接修正 import 就能恢复构建。

## npm run build 的结果

执行结果：

- `npm run build` 成功
- Vite 完成 `1640 modules transformed`
- 已正常产出构建结果

说明：

- 上一轮的构建阻塞 `MeteoriteSearchTabNew.vue` 缺失问题已经修复
- 本轮没有再暴露新的构建级错误
- 仅有非阻塞 warning：
  - `apiClient.js` 同时被动态和静态导入
  - 部分 chunk 体积超过 500 kB

这些 warning 不影响当前“构建基线恢复”目标。

## 当前是否已经恢复到可继续前端重构的基线

是。

当前前端已经恢复到可继续做增量重构的基线，至少满足：

- `npm run build` 可通过
- `MeteoriteSearch.vue` 的缺失依赖问题已解除
- 本轮没有引入新的构建阻塞

## 下一步是否适合进入 DocumentManagementTab.vue 拆分

适合。

原因：

- 服务层拆分已经完成
- 构建基线已经恢复
- 现在可以在相对稳定的前提下进入 `DocumentManagementTab.vue` 的“只拆状态与子组件、不改接口契约”的下一轮工作

更稳妥的进入方式仍然是：

1. 先抽 composable，如上传、列表加载、处理状态轮询
2. 再拆 UI 子组件
3. 保持 `PDFService` 或新子 service 的调用契约不变
