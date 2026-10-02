# Codebase to Mastery · 源码掌握工坊

**从读懂真实源码，走向能够解释、重建、验证并迁移其中的机制。**

[English](README.md) · [最新 npm 包](https://raw.githubusercontent.com/StormTian/codebase-to-mastery/main/codebase-to-mastery.tgz) · [Skill 入口](SKILL.md) · [最新发布](https://github.com/StormTian/codebase-to-mastery/releases/latest) · [验证范围](docs/validation.md) · [MIT 许可证](LICENSE)

这是一个支持 **Codex、Claude Code 和通用 Agent Skills 客户端**的 Skill。输入本地代码库或 GitHub 项目，输出源码可追溯的学习包、离线交互课程和有边界的实践练习。

![六层学习路径](docs/mastery-path.jpg)

## 启发来源与原始项目的区别

最初的想法主要受到 **[Zara Zhang 的 codebase-to-course](https://github.com/zarazhangrui/codebase-to-course)** 启发：从产品出发，把真实源码变成易懂的 HTML 交互课程，用白话解释、可视化和测验帮助读者建立全貌。Codebase to Mastery 在这一体验上扩展了由浅入深的学习包和实践流程，并独立实现模板与工具。

| 设计维度 | codebase-to-course 的主要侧重 | Codebase to Mastery |
| --- | --- | --- |
| 面向读者 | 非技术背景的构建者、vibe coder | 从入门理解逐步走向工程层面的深学 |
| 学习目标 | 理解产品与代码如何工作 | 解释设计、追踪源码、局部重建、扩展验证、复述迁移 |
| 交付内容 | HTML 交互课程与可编辑模块 | HTML 加学习 manifest、阅读路径、source map、回忆题与实践包 |
| 源码依据 | 真实代码与通俗解释对照 | 对文件路径、行号、原文做精确校验，并覆盖最终 HTML |
| 实践与进度 | 可视化、Quiz 与课程进度 | starter/reference 共用行为测试；掌握状态需要真实回答、评价与 learner 运行 |
| 更新与界面 | 从产品组织课程及其视觉设计 | 源码变更影响报告、保留历史回答，以及独立的深色目录、青蓝配色和手机界面 |
| 分发与客户端 | Claude Code Skill 工作流 | 通用 Codex/Claude Code 资源、Skills CLI 安装及 GitHub 托管的 npm 安装入口 |

进阶设计还借鉴了以下项目的方法：

| 项目 | 借鉴思路 |
| --- | --- |
| [StrivingLee/repo-learning-kit](https://github.com/StrivingLee/repo-learning-kit) | 有目的的源码阅读、局部重建、里程碑测试和源码对照 |
| [Terryc21/tutorial-creator](https://github.com/Terryc21/tutorial-creator) | 从实际项目变更中学习、明确记录学习状态 |
| [shuolsure/code-learning-tutorial-skill](https://github.com/shuolsure/code-learning-tutorial-skill) | 概念前置依赖和渐进式执行可视化 |
| [ktaletsk/learn-codebase](https://github.com/ktaletsk/learn-codebase) | 预测、苏格拉底式引导、主动回忆和长期学习日志 |

以上属于设计思路借鉴；本仓库的模板、脚本和文字独立编写。比较针对 [实际审阅的冻结版本](references/provenance.md)，不概括上游未来所有版本，也不声称已经证明教学效果更好。[来源版本与哈希](docs/inspiration-sources.json)保留了可追溯记录。

## 设计差异

学习围绕六层能力推进：

| 层次 | 要形成的能力 | 材料与验证 |
| --- | --- | --- |
| 认识全貌 | 说明产品、组件和边界 | 架构概览、具体用户旅程 |
| 追踪源码 | 沿调用和状态变化阅读 | 阅读顺序、精确摘录、前置概念 |
| 解释设计 | 说明契约、不变量和失败路径 | 反例、替代方案、评价标准 |
| 局部重建 | 独立实现一段核心行为 | starter、独立 reference、共用测试 |
| 扩展验证 | 改一个行为并保护旧行为 | 扩展案例和回归检查 |
| 复述迁移 | 从记忆重建模型并处理新情境 | 主动回忆、迁移题、真实学习记录 |

大项目先读通，再选择一个子系统重建。源码变更会生成模块、概念、前置依赖和练习的复核清单；历史回答不会被覆盖。源码摘录同时检查编辑材料和最终 HTML。

交互课采用深色章节目录、冷色青蓝配色、六层路径卡片与源码/解释对照面板；手机端目录变为横向章节条。上方截图来自当前原创教学样例的实际页面。

**教材可用、参考实现通过、学习者掌握，是三个不同结果。** 掌握记录需要真实回答和评价；重建或扩展还需要当前有效的 learner 运行记录。

## 安装

### 直接安装最新 npm 包

最新的标准 npm 包放在仓库根目录，固定命名为 [`codebase-to-mastery.tgz`](https://raw.githubusercontent.com/StormTian/codebase-to-mastery/main/codebase-to-mastery.tgz)，内置零依赖安装入口。下面的命令始终安装当前最新版，无需选择版本：

```bash
npx --yes --allow-remote=all \
  --package=https://raw.githubusercontent.com/StormTian/codebase-to-mastery/main/codebase-to-mastery.tgz \
  codebase-to-mastery --agent codex claude-code
```

`--allow-remote=all` 只为这次命令允许从 URL 安装。[npm 12 默认拒绝远程 tarball](https://docs.npmjs.com/cli/v12/using-npm/config/#allow-remote)；这个参数不会修改全局 npm 配置。

需要 Node.js 18+。默认安装到当前项目的 `.agents/skills/codebase-to-mastery` 和 `.claude/skills/codebase-to-mastery`；加 `--global` 安装到个人目录，`--dry-run` 查看目标，其他客户端使用 `--directory /path/to/skills`。已有 Skill 文件夹不会被覆盖，重装前需先自行移走旧目录。安装入口负责放置 Skill，学习资料仍由 Agent 使用 Skill 生成。

这个 npm `.tgz` 托管在 **GitHub**，历史版本保留在 Releases；尚未发布到 npmjs.com 或 GitHub Packages registry，所以直接安装使用完整下载地址。也可先下载，再执行 `npx --yes --package=/absolute/path/codebase-to-mastery.tgz codebase-to-mastery --agent codex claude-code`。

### 使用通用 Skills CLI

在目标项目目录，一次安装到 Codex 和 Claude Code：

```bash
npx skills add StormTian/codebase-to-mastery \
  --skill codebase-to-mastery --agent codex claude-code
```

这是 [Skills CLI](https://github.com/vercel-labs/skills) 的安装方式。个人全局安装可加 `--global`，其他客户端使用对应 `--agent`。Node.js 用于两种 `npx` 安装方式；Skill 的学习脚本使用 Python 标准库。

[最新 Release](https://github.com/StormTian/codebase-to-mastery/releases/latest) 提供 ZIP、tar.gz、npm `.tgz`、源码/文件清单和 `SHA256SUMS`。ZIP/tar.gz 解压后可把完整的 `codebase-to-mastery/` 放到下方客户端目录。校验方法随发布说明提供，构建方式见 [打包与发布](docs/releasing.md)。历史版本保留在 [Releases](https://github.com/StormTian/codebase-to-mastery/releases)。

手工安装到 Codex 当前官方文档中的个人目录：

```bash
mkdir -p ~/.agents/skills
git clone https://github.com/StormTian/codebase-to-mastery.git \
  ~/.agents/skills/codebase-to-mastery
```

手工安装到 Claude Code：

```bash
mkdir -p ~/.claude/skills
git clone https://github.com/StormTian/codebase-to-mastery.git \
  ~/.claude/skills/codebase-to-mastery
```

项目级安装分别放在 `.agents/skills/codebase-to-mastery` 或 `.claude/skills/codebase-to-mastery`。部分 Codex 安装和 Skills CLI 的全局目标仍使用 `~/.codex/skills`，按实际客户端的发现目录选择，每个客户端保留一份入口。已有 clone 可先检查本地修改，再执行 `git pull --ff-only`。

其他通用客户端按其文档放入完整 Skill 文件夹，保留脚本、参考和资产的相对路径。`agents/openai.yaml` 只是 Codex 的可选界面信息，核心流程不依赖它。安装位置依据 [OpenAI 文档](https://learn.chatgpt.com/docs/build-skills)、[Claude Code 文档](https://code.claude.com/docs/en/skills) 和 [Agent Skills 规范](https://agentskills.io/specification)。

## 使用

Codex：

```text
用 $codebase-to-mastery 带我由浅入深学习这个项目。
先解释产品和架构，再沿一次请求读源码，
最后选择一个小型子系统做重建、扩展和迁移练习。
```

Claude Code：

```text
/codebase-to-mastery 带我由浅入深学习这个项目，包含源码追踪、
主动回忆、局部重建和有测试的扩展练习。
```

也可以只选一个模式：交互概览、子系统深学、逐题导师、代码变更课，或更新已有学习包。提供你的基础、语言、目标和想研究的子系统即可；产物请求默认直接制作完整材料。

## 环境和产物

需要能够读写文件、执行命令的 Agent，以及 **Python 3.10+**；Git 用于获取源码和记录版本。浏览器帮助验证交互课程。拉取远程源码需要网络，生成的 HTML 可离线阅读。辅助脚本无需模型 API Key、MCP 服务或付费接口。

学习包包含：可编辑 manifest 和 HTML 模块、学习路径、架构与执行说明、精确 source map、主动回忆题、starter/reference/tests、实际 lab-runs，以及按需产生的学习记录和增量更新报告。Markdown 是生成视图，修改正文应回到 manifest 或模块文件。

浏览器保存的是尚未评价的回忆笔记；它不会直接修改掌握状态。源码或评价标准变化后，历史状态保留，并提示重新复核。

## 运行教学样例

在本仓库根目录执行，输出目录必须全新：

```bash
python3 tests/create_demo.py /tmp/codebase-to-mastery-demo
python3 scripts/check_milestone.py /tmp/codebase-to-mastery-demo \
  --milestone core --variant starter
python3 scripts/check_milestone.py /tmp/codebase-to-mastery-demo \
  --milestone core --variant reference
python3 -m unittest discover -s tests -v
```

打开生成的 `index.html`。core 的 starter 应为 `EXPECTED_INCOMPLETE`，reference 应为 `PASS`。样例是原创小型执行器，不代表真实 Agent 框架或生产恢复行为。

详见 [验证范围](docs/validation.md)、[学习包编写](references/learning-kit.md)、[重建练习](references/rebuild-labs.md)、[导师和状态](references/tutoring.md)。跨客户端安装兼容，不等于已经验证所有客户端的端到端教学效果。

## 来源与边界

仓库采用单 Skill 根目录结构：`SKILL.md`、`scripts/`、`references/`、`assets/`、`tests/`。参考了 [anthropics/skills](https://github.com/anthropics/skills) 的独立 Skill 文件夹方式和 [vercel-labs/skills](https://github.com/vercel-labs/skills) 的安装体验，文档与工具独立实现。[来源说明](references/provenance.md) 保留冻结版本。

事实、文档观点、推断和实际运行证据分别标注。练习命令执行前需审阅；runner 不使用 shell 字符串，但不是操作系统沙箱。真实学习回答、凭据和本机运行材料不应进入共享仓库。

[MIT 许可证](LICENSE) 适用于本仓库的原创内容；被讲解项目的源码摘录仍遵循各自许可证。
