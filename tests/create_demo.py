#!/usr/bin/env python3
"""Build a complete Chinese progressive kit from the original mini-runtime fixture."""
from __future__ import annotations
import argparse
import html
import json
import subprocess
import sys
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
SOURCE = SKILL / 'tests/fixtures/mini-runtime'
sys.path.insert(0, str(SKILL / 'scripts'))
from learning_kit import json_text, write_changed
from scaffold_learning import main as scaffold

DEFINITIONS = [
 ('state', '状态与责任', 'orient', 10, 15,
  '用 State 描述一个会话已经完成的工作。',
  'State 像一本进度账本：session_id 说明属于谁，cursor 说明下一步，events 保存已经提交的结果。这个例子没有模型调用；它帮助你先把执行状态和自然语言答案分开。',
  'status 为 done 是否代表结果有用？', '不能。这里只说明计划已耗尽，代码没有检查业务产物是否满足目标。',
  ['区分计划完成与业务成功', '指出需要独立产物验收'], '状态只是进度账本。'),
 ('commit', '工具结果的提交边界', 'trace', 30, 39,
  '定位工具调用、失败和进度提交的先后顺序。',
  '工具成功返回后才追加事件并移动 cursor；失败只改 status 并抛出异常。把每一行当作流水线上的一个交接点，就能看清“调用过”和“提交过”的差别。',
  '第二步工具抛错后，cursor 和 events 会是什么？', '若第一步成功，则 cursor=1、events 只有第一步结果、status=failed。失败步没有被提交。',
  ['成功事件数量等于 cursor', '失败不会推进 cursor', '异常向调用方传播'], '先看 try/except，再看提交顺序。'),
 ('snapshot', '检查点与恢复契约', 'reason', 44, 52,
  '解释恢复能保留什么，并指出不能恢复的外部效果。',
  'checkpoint 把状态转成 JSON，restore 检查事件数量与 cursor 对得上。它像一张账本照片，保存已提交的前缀；这张照片不包含原计划，也不会撤销已经发生的外部动作。',
  '恢复后换一份不同计划，现有校验会阻止吗？', '不会。检查点只验证 cursor 和事件数量，没有计划指纹；调用方必须保证计划一致，或扩展契约。',
  ['指出检查点缺少计划身份', '区分状态恢复与外部动作回滚', '提出需要验证的边界'], '找出 asdict(state) 包含和没有包含的字段。'),
 ('reconstruct', '重建提交不变量', 'rebuild', 18, 25,
  '独立实现成功提交、失败不前进和恢复后继续。',
  '先冻结输入、输出和状态变化，再写实现。像搭一段试验轨道：只保留能验证提交顺序的核心，把真实模型和文件操作排除。参考实现采用另一种循环写法，同一组行为测试判断两者。',
  '为什么用 reference 通过测试不能证明你掌握了恢复机制？', '它只证明教材有正对照。学习者必须自己完成 learner 版本，解释失败与恢复案例，并保留真实运行记录。',
  ['区分教材验证与学习者掌握', '说明不变量而非复制代码形状'], '看是谁编写并运行了被测试的代码。'),
 ('budget', '增加可暂停的执行预算', 'extend', 25, 29,
  '增加每次调用预算，同时保护已完成前缀。',
  '预算像一次通行的配额：本次成功完成多少步达到上限就暂停。cursor 是总进度，completed_this_call 是本次进度；混淆两者会让恢复后的预算失效。',
  '两步计划连续调用两次 budget=1，会提交几步？', '每次最多提交一步：第一次 paused 且 cursor=1，第二次 done 且 cursor=2，第一步不重复。',
  ['区分单次预算与全局 cursor', '指出暂停发生在下一步之前', '保护无重复提交'], '比较 completed_this_call 与 cursor 的生命周期。'),
 ('transfer', '从记忆复述并迁移', 'teach-back', 33, 41,
  '脱离源码说明整个模型，并设计一个反例。',
  '把读取、推演和实现压缩成一张心智地图：选择下一步 → 工具执行 → 事件提交 → cursor 前进 → 暂停或完成。把这张地图搬到有副作用的系统时，需要重新验证原子性与幂等，不能照搬恢复承诺。',
  '工具已经扣款但在追加事件前进程崩溃，恢复后安全吗？', '这个例子没有解决。检查点仍指向未提交步骤，重试可能重复扣款；需要幂等键或事务性外部协议，并做独立运行实验。',
  ['区分外部效果与本地事件提交', '识别重复执行风险', '给出可验证的改进方向'], '沿“工具返回”与“提交事件”之间的窗口推演。'),
]

TEST_CODE = '''import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))
from runtime import State, run, checkpoint, restore

class Cases(unittest.TestCase):
    def test_contract(self):
        state = State('s')
        self.assertEqual(restore(checkpoint(state)), state)

    def test_commit_and_resume(self):
        smoke = run(State('smoke'), [('add', 2)], {'add': lambda x: x + 1})
        self.assertEqual((smoke.cursor, smoke.status, smoke.events[0]['result']), (1, 'done', 3))
        calls = []
        def add(x):
            calls.append(x)
            return x + 1
        tools = {'add': add, 'fail': lambda x: (_ for _ in ()).throw(RuntimeError('tool failed'))}
        plan = [('add', 2), ('fail', 9)]
        state = State('s')
        with self.assertRaises(RuntimeError):
            run(state, plan, tools)
        self.assertEqual((state.cursor, len(state.events), state.status), (1, 1, 'failed'))
        resumed = restore(checkpoint(state))
        tools['fail'] = add
        run(resumed, plan, tools)
        self.assertEqual((resumed.cursor, resumed.status), (2, 'done'))
        self.assertEqual(calls, [2, 9])
        self.assertEqual([e['result'] for e in resumed.events], [3, 10])
        self.assertEqual(state.cursor, 1)  # restored state is independent

    def test_invalid_snapshot(self):
        with self.assertRaises(ValueError):
            restore('{"session_id":"s","cursor":1,"status":"ready","events":[]}')

    def test_budget(self):
        plan = [('add', 2), ('add', 9)]
        state = State('s')
        tools = {'add': lambda x: x + 1}
        run(state, plan, tools, budget=0)
        self.assertEqual((state.cursor, state.status), (0, 'paused'))
        run(state, plan, tools, budget=1)
        self.assertEqual((state.cursor, state.status), (1, 'paused'))
        run(state, plan, tools, budget=1)
        self.assertEqual((state.cursor, state.status), (2, 'done'))
        self.assertEqual([e['step'] for e in state.events], [0, 1])
        with self.assertRaises(ValueError):
            run(state, plan, tools, budget=-1)

if __name__ == '__main__':
    unittest.main()
'''

REFERENCE = '''from dataclasses import asdict, dataclass, field
import json

@dataclass
class State:
    session_id: str
    cursor: int = 0
    status: str = 'ready'
    events: list = field(default_factory=list)

def checkpoint(state):
    return json.dumps(asdict(state), sort_keys=True)

def restore(saved):
    data = json.loads(saved)
    if data['cursor'] < 0 or len(data['events']) != data['cursor']:
        raise ValueError('inconsistent checkpoint')
    return State(**data)

def run(state, plan, tools, budget=None):
    if state.cursor < 0 or state.cursor > len(plan) or (budget is not None and budget < 0):
        raise ValueError('invalid progress or budget')
    stop = len(plan) if budget is None else min(len(plan), state.cursor + budget)
    state.status = 'running'
    for index in range(state.cursor, stop):
        name, value = plan[index]
        try:
            output = tools[name](value)
        except Exception:
            state.status = 'failed'
            raise
        state.events.append(dict(step=index, tool=name, result=output))
        state.cursor = index + 1
    state.status = 'done' if state.cursor == len(plan) else 'paused'
    return state
'''


def build(root: Path, source: Path = SOURCE):
    scaffold([str(root), '--title', '从事件到恢复', '--subtitle', '用一个小型执行循环，走完源码阅读、推演、重建与迁移',
              '--source-root', str(source), '--mode', 'rebuild', '--profile', 'beginner', '--lang', 'zh-CN'])
    config = json.loads((root / 'course.json').read_text())
    kit = json.loads((root / 'learning-kit.json').read_text())
    lines = (source / 'runtime.py').read_text().splitlines()
    concepts = []
    for i, (cid, name, stage, start, end, outcome, explanation, question, answer, rubric, hint) in enumerate(DEFINITIONS):
        module = config['modules'][i]
        excerpt = '\n'.join(lines[start-1:end])
        concept = {'id': cid, 'name': name, 'stage': stage, 'module': module['id'], 'requires': [DEFINITIONS[i-1][0]] if i else [],
                   'outcome': outcome, 'explanation': explanation, 'dependsOn': [],
                   'anchors': [{'path': 'runtime.py', 'lines': f'{start}-{end}', 'text': excerpt,
                                'claim': outcome, 'kind': 'source-observation'}],
                   'checkpoints': [{'prompt': question, 'answer': answer, 'rubric': rubric, 'hints': [hint]}]}
        concepts.append(concept)
        kit['stages'][i].update(outcome=outcome, gate=question)
        extra = ''
        if i == 0:
            extra = '''<div class="component-chat" aria-label="执行方之间的交接"><div class="chat-message" data-speaker="Runner">我读取 cursor 指向的下一步。</div><div class="chat-message" data-speaker="Tool">我返回计算结果，也可能抛出异常。</div><div class="chat-message" data-speaker="State">成功结果提交后，我才记录下一步。</div><button class="replay-chat" type="button">重播交接</button></div>'''
        if i in (1, 2):
            details = [('选择步骤','cursor 指向未提交步骤。'),('工具调用','工具返回成功结果；失败则 status=failed 并传播异常。'),('提交事件','成功结果追加到 events。'),('推进进度','cursor 前进；预算用尽会在下轮前暂停。')]
            extra += '<div class="data-flow" aria-label="成功提交的数据流">' + ''.join(f'<button type="button" class="flow-step{" is-active" if n == 0 else ""}" data-detail="{html.escape(d,quote=True)}">{n+1}. {t}</button>' for n,(t,d) in enumerate(details)) + '<p class="flow-detail" aria-live="polite">cursor 指向未提交步骤。</p></div>'
        content = f'''<section class="course-module" id="{module['id']}" data-title="{name}">
 <div class="screen hero-screen"><p class="eyebrow">{stage} · {i+1}/6</p><h2>{name}</h2><p class="lede">{outcome}</p><p>{explanation}</p></div>
 <div class="screen"><h3>把源码翻译成责任</h3><p><dfn data-definition="下一项还没有被成功提交的步骤编号。">cursor</dfn> 把成功前缀和待执行后缀分开。下面是检查过的连续源码。</p>
 <figure class="code-translation" data-source="runtime.py" data-lines="{start}-{end}"><div class="code-pane"><p class="pane-label source-label"></p><pre><code>{html.escape(excerpt)}</code></pre></div><figcaption><p class="pane-label">白话解释</p><p>{explanation}</p><p>定位与调试：{outcome}</p></figcaption></figure>{extra}</div>
 <div class="screen"><div class="quiz" data-explanation="{html.escape(answer,quote=True)}"><p class="quiz-kicker">应用检查</p><h3>{question}</h3><div class="quiz-options"><button type="button" data-correct="true">{html.escape(answer)}</button><button type="button">只要 status 或测试显示成功，就能断言所有外部效果都安全。</button></div><p class="quiz-feedback" aria-live="polite"></p></div><p class="callout warning">本课程的运行证据限定为本地教学例子；真实模型、MCP、并发与外部副作用未实现。先在学习地图写下预测，再展开评价标准。</p></div>
</section>'''
        (root / 'modules' / module['file']).write_text(content)
    kit.update(scope='只研究固定计划下的本地工具提交、JSON 状态快照、恢复与单次预算；示例是原创测试输入，不代表生产 Agent 框架。',
               rebuildScope='重建 State/run/checkpoint/restore 的小型契约；排除模型、MCP、持久化、并发、权限、外部事务与计划版本管理。',
               unverified=['生产容器、模型与 MCP 集成未实现。','非事务性工具副作用的 exactly-once 不受此例保证。','真实学习者还未回答或实现；未写入用户掌握记录。'],
               runtimeEvidence=['当前脚本构建并校验教材；练习执行结果以 lab-runs 中的实际记录为准，未运行的 variant 没有运行证据。'],
               concepts=concepts)
    kit['notes'] = {
      'overview': '这是一个固定计划的执行器。先能说清 State 的字段和 done 的边界，再去追踪提交与恢复。\n\n事实：它不调用模型、不访问网络。研究推断：这种小模型适合练习状态不变量；生产等价性未验证。',
      'architecture': '静态调用关系：调用方 → run → tools[name] → State；调用方 → checkpoint/restore → JSON。\n\n`runtime.py` 是唯一实现文件。函数之间的边可直接在源码定位；工具的实际行为由调用方注入。\n\n```mermaid\nflowchart LR\n Caller --> Run\n Run --> Tool\n Tool --> Commit[成功事件提交]\n Commit --> State\n State --> JSON\n JSON --> Resume[恢复 State]\n```',
      'execution': '例子：plan=[("add",2),("fail",9)]。第一步结果为 3；第二步抛错时 cursor=1、events 只有第一个结果、status=failed。修复工具并从 checkpoint 恢复后，只执行未提交的第二步。\n\n反例：工具先产生外部效果再崩溃，cursor 未前进，重试会重复效果；本例未解决。',
      'abstractions': 'State 表示已提交前缀；plan 决定步骤；tools 把名称映射到调用；events 保存提交结果；cursor 指向下一未提交步骤；budget 限制本次调用。\n\n关键不变量：正常受控路径中 len(events)==cursor。调用方能直接修改 State，因此这是 API 契约，不是不可破坏的封装保证。',
      'reading': '阅读顺序按责任而非文件字母：\n\n1. State：先预测字段变化（source map: state）。\n2. run 成功/失败路径：逐行画提交边界（commit）。\n3. checkpoint/restore：列出保存和没保存的事实（snapshot）。\n4. run 的参数约束与 budget：完成 reconstruct/budget 练习。\n5. 从空白纸复述，再检查 transfer 反例。',
      'decisions': '源码观察：结果成功后才推进 cursor；恢复使用 JSON 和事件数量校验。独立参考采用 for 循环，源代码采用 while 循环，两者由行为测试比较。\n\n推断：这种顺序方便表达成功前缀。作者动机没有外部文档，不作历史断言。\n\n替代方案：为计划保存哈希、防篡改状态、为有副作用工具添加幂等键；这些均需要新的契约和实验，不能从当前通过结果推出。',
      'extension': '先实现每次调用 budget，再验证 budget=0、连续两次 budget=1、负预算拒绝，并重跑提交与恢复测试。\n\n下一课候选：在检查点存 plan 哈希，拒绝换计划恢复。先定义兼容旧快照的行为，再写反例；当前课程没有实现它。',
    }
    (root / 'playground/tests/test_runtime.py').write_text(TEST_CODE)
    (root / 'playground/reference/runtime.py').write_text(REFERENCE)
    starter = REFERENCE[:REFERENCE.index('def run(')] + "def run(state, plan, tools, budget=None):\n    raise NotImplementedError('Implement successful-prefix execution and per-call budget')\n"
    (root / 'playground/starter/runtime.py').write_text(starter)
    cases = [('contract','接口与快照基础',['state','snapshot'],[],['Cases.test_contract','Cases.test_invalid_snapshot'],'pass'),
             ('core','重建成功提交与失败恢复',['commit','reconstruct'],['contract'],['Cases.test_commit_and_resume'],'incomplete'),
             ('budget','增加单次预算且无重复提交',['budget','transfer'],['core'],['Cases.test_budget','Cases.test_commit_and_resume'],'incomplete')]
    milestones = []
    for mid,title,cids,requires,tests,expectation in cases:
        exercise = f'playground/exercises/{mid}.md'
        command = ['{python}','../tests/test_runtime.py',*tests]
        milestone = {'id':mid,'title':title,'concepts':cids,'requires':requires,'goal':title,
                     'invariant':'已提交事件数量等于 cursor；失败与暂停不会提交下一步。',
                     'exercise':exercise,'commands':[command],'timeoutSeconds':10,'starterExpectation':expectation}
        milestones.append(milestone)
        write_changed(root / exercise, f'# {title}\n\n目标：{title}。\n\n不变量：{milestone["invariant"]}\n\n源码锚点：{", ".join(cids)}，见 [source map](../../study/06-source-map.md)。\n\n运行：在 playground/<variant> 中用 Python 执行 `{ " ".join(command[1:]) }`。或用 Skill 的 check_milestone.py 指定 {mid} 与 variant。\n\nStarter 预期：{expectation}。Reference 必须 PASS。\n\n提示一：区分“已调用”与“已提交”；提示二：只在成功后改变进度。\n\n验收：正常路径、失败不前进、恢复不重复；budget 课还要覆盖零预算与两次单步预算。\n\n比较：先解释自己的不变量，再比较 while 与 for 的写法。模型、网络和外部事务不在练习范围。\n')
    kit['milestones'] = milestones
    (root / 'learning-kit.json').write_text(json_text(kit))
    (root / 'README.md').write_text('# 从事件到恢复 · v2 样例\n\n[学习路径](LEARNING_PATH.md) · [交互课](index.html) · [源码地图](study/06-source-map.md)\n\n完整的原创 mini-runtime 教学样例，用于验证 Skill 工具链。参考答案单独放在 playground/reference；学习者先从 starter 创建自己的 learner 目录。\n\n从 Skill 根目录运行 `python3 tests/create_demo.py <全新输出目录>` 可重建。用 Skill 的 `scripts/check_milestone.py` 对本目录运行练习控制，结果保存在 lab-runs。无真实学习者掌握记录。\n')
    for name in ('build_course.py','validate_course.py','update_course.py'):
        args = [sys.executable,str(SKILL/'scripts'/name),str(root)]
        if name != 'build_course.py': args += ['--source-root',str(source)]
        if name == 'update_course.py': args += ['--accept-baseline']
        completed = subprocess.run(args,check=True,capture_output=True,text=True)
        print(completed.stdout.strip())
    return root


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('output_dir',type=Path)
    args = p.parse_args()
    build(args.output_dir.expanduser().resolve())
