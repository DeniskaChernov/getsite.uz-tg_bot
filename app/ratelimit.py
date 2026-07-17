"""Анти-флуд: лимиты на пользователя и глобальный circuit breaker."""
from __future__ import annotations

import time
from collections import defaultdict, deque

PER_USER_LLM_INTERVAL = 3          # не чаще 1 LLM-запроса в 3 сек
PER_USER_WINDOW = 600              # 10 минут
PER_USER_WINDOW_LIMIT = 30         # 30 сообщений / 10 минут

GLOBAL_WINDOW = 60
GLOBAL_LIMIT = 300                 # аномальный всплеск: > 300 сообщений/мин на всех
BREAKER_COOLDOWN = 300             # 5 минут работы без LLM после всплеска


class RateLimiter:
    def __init__(self) -> None:
        self._last_llm: dict[int, float] = {}
        self._windows: defaultdict[int, deque[float]] = defaultdict(deque)
        self._global: deque[float] = deque()
        self._breaker_until: float = 0.0

    def check_user(self, user_id: int) -> bool:
        """True — можно обрабатывать; False — флуд, ответить шаблоном без LLM."""
        now = time.monotonic()

        window = self._windows[user_id]
        window.append(now)
        while window and now - window[0] > PER_USER_WINDOW:
            window.popleft()
        if len(window) > PER_USER_WINDOW_LIMIT:
            return False

        if now - self._last_llm.get(user_id, 0.0) < PER_USER_LLM_INTERVAL:
            return False
        self._last_llm[user_id] = now
        return True

    def check_global(self) -> bool:
        """True — LLM доступен; False — circuit breaker открыт, шаблоны без LLM."""
        now = time.monotonic()
        if now < self._breaker_until:
            return False
        self._global.append(now)
        while self._global and now - self._global[0] > GLOBAL_WINDOW:
            self._global.popleft()
        if len(self._global) > GLOBAL_LIMIT:
            self._breaker_until = now + BREAKER_COOLDOWN
            return False
        return True

    @property
    def breaker_open(self) -> bool:
        return time.monotonic() < self._breaker_until


limiter = RateLimiter()
