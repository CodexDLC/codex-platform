"""
codex_platform.redis_service.mixins.stream
========================================
Redis Stream operations mixin.

Requires ``redis.asyncio.Redis`` client (provided by BaseRedisService).
All operations are async-only.
"""

import logging
from typing import Any

from redis.asyncio import Redis
from redis.exceptions import RedisError

log = logging.getLogger(__name__)


class StreamMixin:
    """
    Миксин для работы со стримами (Stream) в Redis.

    Доступные методы:
        stream_add(stream_name, data) → str | None (добавить событие)
        stream_create_group(stream_name, group_name) → None (создать группу)
        stream_read_group(stream_name, group_name, consumer_name, count) → list[tuple] (читать из группы)
        stream_ack(stream_name, group_name, event_id) → None (подтвердить обработку)

    Требует: BaseRedisService (предоставляет self.redis_client)
    """

    redis_client: Redis

    async def stream_add(self, stream_name: str, data: dict[str, Any]) -> str | None:
        """
        Добавляет событие в стрим Redis.

        Автоматически выполняет санитизацию данных:
        - Конвертирует boolean значения в строки ('True'/'False')
        - Фильтрует поля со значением None
        """
        try:
            sanitized_data = {k: (str(v) if isinstance(v, bool) else v) for k, v in data.items() if v is not None}
            result = await self.redis_client.xadd(stream_name, sanitized_data)
            log.debug("RedisStream | action=add status=success stream='%s' id='%s'", stream_name, result)
            return str(result) if result else None
        except RedisError:
            log.exception("RedisStream | action=add status=failed reason='Redis error' stream='%s'", stream_name)
            return None

    async def stream_create_group(self, stream_name: str, group_name: str) -> None:
        """Создает группу потребителей (если не существует)."""
        try:
            await self.redis_client.xgroup_create(stream_name, group_name, id="0", mkstream=True)
            log.debug(
                "RedisStream | action=create_group status=success stream='%s' group='%s'", stream_name, group_name
            )
        except RedisError as e:
            if "BUSYGROUP" in str(e):
                log.debug(
                    "RedisStream | action=create_group status=exists stream='%s' group='%s'", stream_name, group_name
                )
            else:
                log.exception(
                    "RedisStream | action=create_group status=failed reason='Redis error' stream='%s' group='%s'",
                    stream_name,
                    group_name,
                )

    async def stream_read_group(
        self, stream_name: str, group_name: str, consumer_name: str, count: int = 10
    ) -> list[tuple[Any, ...]]:
        """Читает новые события из стрима для группы."""
        try:
            streams = await self.redis_client.xreadgroup(
                groupname=group_name,
                consumername=consumer_name,
                streams={stream_name: ">"},
                count=count,
            )
            if streams:
                log.debug(
                    "RedisStream | action=read_group status=success stream='%s' count=%d",
                    stream_name,
                    len(streams[0][1]),
                )
                return streams[0][1]
            return []
        except RedisError:
            log.exception("RedisStream | action=read_group status=failed reason='Redis error' stream='%s'", stream_name)
            return []

    async def stream_ack(self, stream_name: str, group_name: str, event_id: str) -> None:
        """Подтверждает обработку события."""
        try:
            await self.redis_client.xack(stream_name, group_name, event_id)
            log.debug("RedisStream | action=ack status=success stream='%s' id='%s'", stream_name, event_id)
        except RedisError:
            log.exception(
                "RedisStream | action=ack status=failed reason='Redis error' stream='%s' id='%s'", stream_name, event_id
            )
