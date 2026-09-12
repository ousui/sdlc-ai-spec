# Implementation Plan: [FEATURE]（实施计划）

**Branch**: `[###-feature-name]` | **Date**: [DATE] | **Spec**: [link]

**Input**: 功能规格来源：`.sdlc/specs/[###-feature-name]/spec.md`

**Note**: 本模板由 `sdlc-200-plan` 填写；执行流程见该能力定义。

## Summary（概述）

[从功能规格提取主要需求，并概述研究得到的技术方案]

## Technical Context（技术上下文）

<!--
  必须处理：将本节内容替换为项目的具体技术细节。
  这里的结构仅作为建议，
  用于指导迭代过程。
-->

**Language/Version**: [例如 Python 3.11、Swift 5.9、Rust 1.75，或 NEEDS CLARIFICATION]

**Primary Dependencies**: [例如 FastAPI、UIKit、LLVM，或 NEEDS CLARIFICATION]

**Storage**: [适用时填写，例如 PostgreSQL、CoreData、文件，或 N/A]

**Testing**: [例如 pytest、XCTest、cargo test，或 NEEDS CLARIFICATION]

**Target Platform**: [例如 Linux 服务器、iOS 15+、WASM，或 NEEDS CLARIFICATION]

**Project Type**: [例如 library/cli/web-service/mobile-app/compiler/desktop-app，或 NEEDS CLARIFICATION]

**Performance Goals**: [领域相关，例如 1000 req/s、10k lines/sec、60 fps，或 NEEDS CLARIFICATION]

**Constraints**: [领域相关，例如 <200ms p95、<100MB 内存、支持离线，或 NEEDS CLARIFICATION]

**Scale/Scope**: [领域相关，例如 10k 用户、1M LOC、50 个界面，或 NEEDS CLARIFICATION]

## Constitution Check（宪法检查）

*门禁：必须在 Phase 0 研究之前通过；Phase 1 设计之后重新检查。*

[依据宪法文件确定检查门禁]

## Project Structure（项目结构）

### Documentation (this feature)（本功能文档）

```text
.sdlc/specs/[###-feature]/
├── plan.md              # 本文件（sdlc-200-plan 输出）
├── research.md          # Phase 0 输出（sdlc-200-plan）
├── data-model.md        # Phase 1 输出（sdlc-200-plan）
├── quickstart.md        # Phase 1 输出（sdlc-200-plan）
├── contracts/           # Phase 1 输出（sdlc-200-plan）
└── tasks.md             # Phase 2 输出（sdlc-300-task；不是由 sdlc-200-plan 创建）
```

### Source Code (repository root)（仓库根目录下的源码）
<!--
  必须处理：把下面的占位目录树替换为本功能的实际结构。
  删除未使用的选项，并将选中的结构展开为
  真实路径（例如 apps/admin、packages/something）。交付的计划
  不得保留 Option 标签。
-->

```text
# [REMOVE IF UNUSED] Option 1: 单项目（默认）
src/
├── models/
├── services/
├── cli/
└── lib/

tests/
├── contract/
├── integration/
└── unit/

# [REMOVE IF UNUSED] Option 2: Web 应用（识别到 "frontend" + "backend" 时）
backend/
├── src/
│   ├── models/
│   ├── services/
│   └── api/
└── tests/

frontend/
├── src/
│   ├── components/
│   ├── pages/
│   └── services/
└── tests/

# [REMOVE IF UNUSED] Option 3: Mobile + API（识别到 "iOS/Android" 时）
api/
└── [同上方 backend 结构]

ios/ or android/
└── [平台特定结构：功能模块、UI 流程、平台测试]
```

**Structure Decision**: [说明选中的结构，并引用上面列出的实际
目录]

## Complexity Tracking（复杂性记录）

> **仅在 Constitution Check 存在需要说明理由的违例时填写**

| Violation（违例） | Why Needed（必要性） | Simpler Alternative Rejected Because（未采用更简单方案的原因） |
|-----------|------------|-------------------------------------|
| [例如第 4 个项目] | [当前需求] | [为什么 3 个项目不足以满足要求] |
| [例如 Repository 模式] | [具体问题] | [为什么直接访问数据库不足以解决问题] |
