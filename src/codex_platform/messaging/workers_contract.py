"""Stable worker task names and payload schema version for messaging."""

PAYLOAD_SCHEMA_VERSION = 1

TASK_SEND_NOTIFICATION = "send_universal_notification_task"
TASK_SEND_RENDERED = "send_rendered_notification_task"
TASK_SEND_CAMPAIGN = "send_campaign_batch_task"

__all__ = [
    "PAYLOAD_SCHEMA_VERSION",
    "TASK_SEND_NOTIFICATION",
    "TASK_SEND_RENDERED",
    "TASK_SEND_CAMPAIGN",
]
