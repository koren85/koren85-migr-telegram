from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum


class NotificationPriority(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ConditionType(Enum):
    VALUE_EQUALS = "value_equals"
    VALUE_NOT_EQUALS = "value_not_equals"
    VALUE_CONTAINS = "value_contains"
    VALUE_CHANGED = "value_changed"
    VALUE_UNCHANGED = "value_unchanged"
    VALUE_GREATER = "value_greater"
    VALUE_LESS = "value_less"
    CUSTOM = "custom"


@dataclass
class DatabaseMonitorConfig:
    """Monitor configuration stored in database"""
    id: Optional[int] = None
    name: str = ""  # Display name (e.g., "Воронеж 1 задача")
    db_name: str = ""  # Database name (e.g., "voron_migr_db")
    sql_query: str = ""  # SQL query to execute
    check_interval: int = 60  # Check interval in seconds
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    # Database connection info (optional, can inherit from db_name config)
    driver: Optional[str] = None
    url: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    jar_path: Optional[str] = None


@dataclass
class NotificationRule:
    """Notification rule configuration"""
    id: Optional[int] = None
    name: str = ""
    monitor_name: str = ""
    db_name: str = ""
    condition_type: ConditionType = ConditionType.VALUE_CHANGED
    condition_value: Optional[str] = None
    condition_duration: Optional[int] = None  # seconds
    cooldown_seconds: int = 300  # 5 minutes default
    priority: NotificationPriority = NotificationPriority.MEDIUM
    message_template: str = "🔔 {monitor_name}: {old_value} → {new_value}"
    target_chats: str = "all"  # "all" or comma-separated chat IDs
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class NotificationHistory:
    """Notification history record"""
    id: Optional[int] = None
    rule_id: int = 0
    monitor_name: str = ""
    db_name: str = ""
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    message: str = ""
    target_chats: str = ""
    sent_at: Optional[datetime] = None
    success: bool = True
    error_message: Optional[str] = None


@dataclass
class MonitorState:
    """Extended monitor state with notification tracking"""
    monitor_name: str
    db_name: str
    current_value: Any = None
    previous_value: Any = None
    last_change_time: Optional[datetime] = None
    last_notification_time: Optional[datetime] = None
    same_value_duration: int = 0  # seconds
    notification_cooldowns: Dict[int, datetime] = None  # rule_id -> last_sent_time
    
    def __post_init__(self):
        if self.notification_cooldowns is None:
            self.notification_cooldowns = {}