import sqlite3
import json
from datetime import datetime
from typing import List, Optional, Dict, Any
from pathlib import Path
from loguru import logger

from .models import NotificationRule, NotificationHistory, ConditionType, NotificationPriority


class NotificationDatabase:
    """SQLite database for notification rules and history"""
    
    def __init__(self, db_path: str = "data/notifications.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(exist_ok=True)
        self._init_database()
    
    def _init_database(self):
        """Initialize database tables"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS notification_rules (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    monitor_name TEXT NOT NULL,
                    db_name TEXT NOT NULL,
                    condition_type TEXT NOT NULL,
                    condition_value TEXT,
                    condition_duration INTEGER,
                    cooldown_seconds INTEGER NOT NULL DEFAULT 300,
                    priority TEXT NOT NULL DEFAULT 'medium',
                    message_template TEXT NOT NULL,
                    target_chats TEXT NOT NULL DEFAULT 'all',
                    is_active BOOLEAN NOT NULL DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS notification_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    rule_id INTEGER,
                    monitor_name TEXT NOT NULL,
                    db_name TEXT NOT NULL,
                    old_value TEXT,
                    new_value TEXT,
                    message TEXT NOT NULL,
                    target_chats TEXT NOT NULL,
                    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    success BOOLEAN NOT NULL DEFAULT 1,
                    error_message TEXT,
                    FOREIGN KEY (rule_id) REFERENCES notification_rules (id)
                )
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_rules_monitor 
                ON notification_rules (monitor_name, db_name, is_active)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_history_time 
                ON notification_history (sent_at)
            """)
            
            # Table to track monitors that had rules explicitly disabled
            conn.execute("""
                CREATE TABLE IF NOT EXISTS disabled_monitors (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    monitor_name TEXT NOT NULL,
                    db_name TEXT NOT NULL,
                    disabled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(monitor_name, db_name)
                )
            """)
            
            conn.commit()
    
    def create_rule(self, rule: NotificationRule) -> int:
        """Create a new notification rule"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT INTO notification_rules 
                (name, monitor_name, db_name, condition_type, condition_value, 
                 condition_duration, cooldown_seconds, priority, message_template, 
                 target_chats, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                rule.name, rule.monitor_name, rule.db_name, 
                rule.condition_type.value, rule.condition_value,
                rule.condition_duration, rule.cooldown_seconds,
                rule.priority.value, rule.message_template,
                rule.target_chats, rule.is_active
            ))
            
            rule_id = cursor.lastrowid
            conn.commit()
            logger.info(f"Created notification rule: {rule.name} (ID: {rule_id})")
            return rule_id
    
    def get_rules(self, monitor_name: str = None, db_name: str = None, 
                  active_only: bool = True) -> List[NotificationRule]:
        """Get notification rules"""
        query = "SELECT * FROM notification_rules WHERE 1=1"
        params = []
        
        if monitor_name:
            query += " AND monitor_name = ?"
            params.append(monitor_name)
        
        if db_name:
            query += " AND db_name = ?"
            params.append(db_name)
            
        if active_only:
            query += " AND is_active = 1"
        
        query += " ORDER BY priority DESC, created_at"
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(query, params)
            
            rules = []
            for row in cursor.fetchall():
                rule = NotificationRule(
                    id=row['id'],
                    name=row['name'],
                    monitor_name=row['monitor_name'],
                    db_name=row['db_name'],
                    condition_type=ConditionType(row['condition_type']),
                    condition_value=row['condition_value'],
                    condition_duration=row['condition_duration'],
                    cooldown_seconds=row['cooldown_seconds'],
                    priority=NotificationPriority(row['priority']),
                    message_template=row['message_template'],
                    target_chats=row['target_chats'],
                    is_active=bool(row['is_active']),
                    created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None,
                    updated_at=datetime.fromisoformat(row['updated_at']) if row['updated_at'] else None
                )
                rules.append(rule)
            
            return rules
    
    def update_rule(self, rule: NotificationRule) -> bool:
        """Update notification rule"""
        if not rule.id:
            return False
            
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                UPDATE notification_rules SET
                    name = ?, monitor_name = ?, db_name = ?,
                    condition_type = ?, condition_value = ?, condition_duration = ?,
                    cooldown_seconds = ?, priority = ?, message_template = ?,
                    target_chats = ?, is_active = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (
                rule.name, rule.monitor_name, rule.db_name,
                rule.condition_type.value, rule.condition_value, rule.condition_duration,
                rule.cooldown_seconds, rule.priority.value, rule.message_template,
                rule.target_chats, rule.is_active, rule.id
            ))
            
            success = cursor.rowcount > 0
            conn.commit()
            
            if success:
                logger.info(f"Updated notification rule: {rule.name} (ID: {rule.id})")
            return success
    
    def delete_rule(self, rule_id: int) -> bool:
        """Delete notification rule"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("DELETE FROM notification_rules WHERE id = ?", (rule_id,))
            success = cursor.rowcount > 0
            conn.commit()
            
            if success:
                logger.info(f"Deleted notification rule ID: {rule_id}")
            return success
    
    def mark_monitor_disabled(self, monitor_name: str, db_name: str):
        """Mark a monitor as explicitly disabled (rules deleted by user)"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO disabled_monitors (monitor_name, db_name, disabled_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
            """, (monitor_name, db_name))
            conn.commit()
    
    def is_monitor_disabled(self, monitor_name: str, db_name: str) -> bool:
        """Check if a monitor was explicitly disabled"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT 1 FROM disabled_monitors 
                WHERE monitor_name = ? AND db_name = ?
            """, (monitor_name, db_name))
            return cursor.fetchone() is not None
    
    def enable_monitor(self, monitor_name: str, db_name: str):
        """Re-enable a previously disabled monitor"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                DELETE FROM disabled_monitors 
                WHERE monitor_name = ? AND db_name = ?
            """, (monitor_name, db_name))
            conn.commit()
    
    def log_notification(self, notification: NotificationHistory) -> int:
        """Log notification to history"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT INTO notification_history 
                (rule_id, monitor_name, db_name, old_value, new_value, 
                 message, target_chats, success, error_message)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                notification.rule_id, notification.monitor_name, notification.db_name,
                notification.old_value, notification.new_value, notification.message,
                notification.target_chats, notification.success, notification.error_message
            ))
            
            history_id = cursor.lastrowid
            conn.commit()
            return history_id
    
    def get_notification_history(self, limit: int = 100, 
                               monitor_name: str = None) -> List[NotificationHistory]:
        """Get notification history"""
        query = "SELECT * FROM notification_history WHERE 1=1"
        params = []
        
        if monitor_name:
            query += " AND monitor_name = ?"
            params.append(monitor_name)
        
        query += " ORDER BY sent_at DESC LIMIT ?"
        params.append(limit)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(query, params)
            
            history = []
            for row in cursor.fetchall():
                notification = NotificationHistory(
                    id=row['id'],
                    rule_id=row['rule_id'],
                    monitor_name=row['monitor_name'],
                    db_name=row['db_name'],
                    old_value=row['old_value'],
                    new_value=row['new_value'],
                    message=row['message'],
                    target_chats=row['target_chats'],
                    sent_at=datetime.fromisoformat(row['sent_at']) if row['sent_at'] else None,
                    success=bool(row['success']),
                    error_message=row['error_message']
                )
                history.append(notification)
            
            return history
    
    def get_stats(self) -> Dict[str, Any]:
        """Get notification statistics"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            # Total rules
            total_rules = conn.execute("SELECT COUNT(*) as count FROM notification_rules").fetchone()['count']
            active_rules = conn.execute("SELECT COUNT(*) as count FROM notification_rules WHERE is_active = 1").fetchone()['count']
            
            # Recent notifications
            recent_notifications = conn.execute("""
                SELECT COUNT(*) as count FROM notification_history 
                WHERE sent_at > datetime('now', '-24 hours')
            """).fetchone()['count']
            
            # Success rate
            success_rate = conn.execute("""
                SELECT 
                    CAST(SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) AS FLOAT) * 100.0 / COUNT(*) as rate
                FROM notification_history 
                WHERE sent_at > datetime('now', '-7 days')
            """).fetchone()['rate'] or 0
            
            return {
                'total_rules': total_rules,
                'active_rules': active_rules,
                'recent_notifications_24h': recent_notifications,
                'success_rate_7d': round(success_rate, 2)
            }