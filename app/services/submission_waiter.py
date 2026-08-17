from __future__ import annotations

import asyncio
import inspect
from dataclasses import dataclass
from time import monotonic
from typing import Awaitable, Callable, Iterable

from sqlalchemy.orm import Session

from app.models.orm_models import SubmissionModel

TERMINAL_STATUS_IDS = frozenset(range(3, 10))

class SubmissionWaitError(RuntimeError):
    pass

class SubmissionWaitTimeout(SubmissionWaitError):
    def __init__(self, pending_tokens: Iterable[str]):
        self.pending_tokens = tuple(pending_tokens)
        super().__init__("Timed out waiting for submission result")

class SubmissionWaitCancelled(SubmissionWaitError):
    pass

class SubmissionWaitNotFound(SubmissionWaitError):
    def __init__(self, missing_tokens: Iterable[str]):
        self.missing_tokens = tuple(missing_tokens)
        super().__init__("Submission disappeared while waiting for its result")

@dataclass(frozen=True)
class SubmissionState:
    token: str
    status_id: int

DisconnectCheck = Callable[[], bool | Awaitable[bool]]

class SubmissionWaiter:
    def __init__(
        self,
        *,
        timeout: float,
        poll_interval: float,
        session_factory: Callable[[], Session] | None = None,
    ):
        if timeout <= 0:
            raise ValueError("timeout must be positive")
        if poll_interval <= 0 or poll_interval > timeout:
            raise ValueError("poll_interval must be positive and not exceed timeout")
        if session_factory is None:
            from app.db.session import SessionLocal

            session_factory = SessionLocal
        self.timeout = timeout
        self.poll_interval = poll_interval
        self.session_factory = session_factory

    def _load_states(self, tokens: tuple[str, ...]):
        db = self.session_factory()
        try:
            rows = (
                db.query(SubmissionModel.token, SubmissionModel.status_id)
                .filter(SubmissionModel.token.in_(tokens))
                .all()
            )
            return {
                row.token: SubmissionState(token=row.token, status_id=row.status_id)
                for row in rows
            }
        finally:
            db.close()

    async def _disconnected(self, check: DisconnectCheck | None):
        if check is None:
            return False
        result = check()
        if inspect.isawaitable(result):
            result = await result
        return bool(result)

    async def wait_for_terminal(
        self,
        token: str,
        *,
        disconnected: DisconnectCheck | None = None,
    ):
        states = await self.wait_many((token,), disconnected=disconnected)
        return states[token]

    async def wait_many(
        self,
        tokens: Iterable[str],
        *,
        disconnected: DisconnectCheck | None = None,
    ):
        ordered_tokens = tuple(dict.fromkeys(tokens))
        if not ordered_tokens:
            return {}

        deadline = monotonic() + self.timeout
        while True:
            if await self._disconnected(disconnected):
                raise SubmissionWaitCancelled("Client disconnected while waiting")

            states = await asyncio.to_thread(self._load_states, ordered_tokens)
            missing = [token for token in ordered_tokens if token not in states]
            if missing:
                raise SubmissionWaitNotFound(missing)

            pending = [
                token
                for token in ordered_tokens
                if states[token].status_id not in TERMINAL_STATUS_IDS
            ]
            if not pending:
                return states

            remaining = deadline - monotonic()
            if remaining <= 0:
                raise SubmissionWaitTimeout(pending)
            await asyncio.sleep(min(self.poll_interval, remaining))
