"""A small original teaching runtime: commit successful results, resume by cursor.

This is an in-memory deterministic example, not a production agent or sandbox.
"""
from dataclasses import asdict, dataclass, field
import json
from typing import Callable


@dataclass
class State:
    session_id: str
    cursor: int = 0
    status: str = 'ready'
    events: list[dict] = field(default_factory=list)


def run(state: State, plan: list[tuple[str, int]], tools: dict[str, Callable],
        budget: int | None = None) -> State:
    if not 0 <= state.cursor <= len(plan):
        raise ValueError('cursor outside plan')
    if budget is not None and budget < 0:
        raise ValueError('budget must be nonnegative')
    state.status = 'running'
    completed_this_call = 0
    while state.cursor < len(plan):
        if budget is not None and completed_this_call >= budget:
            state.status = 'paused'
            return state
        index = state.cursor
        name, value = plan[index]
        try:
            result = tools[name](value)
        except Exception:
            state.status = 'failed'
            raise
        state.events.append({'step': index, 'tool': name, 'result': result})
        state.cursor += 1
        completed_this_call += 1
    state.status = 'done'
    return state


def checkpoint(state: State) -> str:
    return json.dumps(asdict(state), sort_keys=True)


def restore(saved: str) -> State:
    payload = json.loads(saved)
    if payload['cursor'] < 0 or len(payload['events']) != payload['cursor']:
        raise ValueError('checkpoint cursor and committed events disagree')
    return State(**payload)
