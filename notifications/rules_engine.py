import asyncio
import re
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from loguru import logger

from .models import NotificationRule, NotificationHistory, MonitorState, ConditionType, NotificationPriority
from .database import NotificationDatabase


class NotificationRulesEngine:
    """Engine for processing notification rules and conditions"""
    
    def __init__(self, db_path: str = "notifications.db"):
        self.database = NotificationDatabase(db_path)
        self.monitor_states: Dict[str, MonitorState] = {}
        self.notification_callback: Optional[Callable] = None
    
    def set_notification_callback(self, callback: Callable):
        """Set callback function for sending notifications"""
        self.notification_callback = callback
    
    def get_monitor_key(self, db_name: str, monitor_name: str) -> str:
        """Generate unique key for monitor"""
        return f"{db_name}.{monitor_name}"
    
    async def process_value_change(self, db_name: str, monitor_name: str, 
                                 old_value: Any, new_value: Any):
        """Process value change and check notification rules"""
        monitor_key = self.get_monitor_key(db_name, monitor_name)
        
        # Get or create monitor state
        if monitor_key not in self.monitor_states:
            self.monitor_states[monitor_key] = MonitorState(
                monitor_name=monitor_name,
                db_name=db_name
            )
        
        state = self.monitor_states[monitor_key]
        now = datetime.now()
        
        # Update monitor state
        state.previous_value = state.current_value
        state.current_value = new_value
        
        # Check if value actually changed
        value_changed = old_value != new_value
        if value_changed:
            state.last_change_time = now
            state.same_value_duration = 0
        else:
            # Calculate how long the value has been the same
            if state.last_change_time:
                state.same_value_duration = int((now - state.last_change_time).total_seconds())
        
        # Get rules for this monitor
        rules = self.database.get_rules(monitor_name=monitor_name, db_name=db_name)
        
        # Process each rule
        for rule in rules:
            if await self._should_trigger_notification(rule, state, old_value, new_value):
                await self._send_notification(rule, state, old_value, new_value)
    
    async def _should_trigger_notification(self, rule: NotificationRule, 
                                         state: MonitorState, old_value: Any, 
                                         new_value: Any) -> bool:
        """Check if notification should be triggered based on rule conditions"""
        
        # Check cooldown
        if await self._is_in_cooldown(rule, state):
            return False
        
        # Check condition
        return await self._evaluate_condition(rule, state, old_value, new_value)
    
    async def _is_in_cooldown(self, rule: NotificationRule, state: MonitorState) -> bool:
        """Check if rule is in cooldown period"""
        if not rule.id or rule.id not in state.notification_cooldowns:
            return False
        
        last_sent = state.notification_cooldowns[rule.id]
        cooldown_until = last_sent + timedelta(seconds=rule.cooldown_seconds)
        
        return datetime.now() < cooldown_until
    
    async def _evaluate_condition(self, rule: NotificationRule, state: MonitorState,
                                old_value: Any, new_value: Any) -> bool:
        """Evaluate rule condition"""
        condition_type = rule.condition_type
        condition_value = rule.condition_value
        
        try:
            if condition_type == ConditionType.VALUE_EQUALS:
                return str(new_value) == condition_value
            
            elif condition_type == ConditionType.VALUE_NOT_EQUALS:
                return str(new_value) != condition_value
            
            elif condition_type == ConditionType.VALUE_CONTAINS:
                return condition_value in str(new_value)
            
            elif condition_type == ConditionType.VALUE_CHANGED:
                return old_value != new_value
            
            elif condition_type == ConditionType.VALUE_UNCHANGED:
                # Check if value hasn't changed for specified duration
                if rule.condition_duration is None:
                    return False
                return state.same_value_duration >= rule.condition_duration
            
            elif condition_type == ConditionType.VALUE_GREATER:
                try:
                    return float(new_value) > float(condition_value)
                except (ValueError, TypeError):
                    return False
            
            elif condition_type == ConditionType.VALUE_LESS:
                try:
                    return float(new_value) < float(condition_value)
                except (ValueError, TypeError):
                    return False
            
            elif condition_type == ConditionType.CUSTOM:
                # Allow custom Python expressions (be careful with security!)
                return await self._evaluate_custom_condition(condition_value, state, old_value, new_value)
            
        except Exception as e:
            logger.error(f"Error evaluating condition for rule {rule.name}: {e}")
            return False
        
        return False
    
    async def _evaluate_custom_condition(self, condition: str, state: MonitorState,
                                       old_value: Any, new_value: Any) -> bool:
        """Safely evaluate custom condition (limited Python expressions)"""
        if not condition:
            return False
        
        # Create safe context for evaluation
        safe_context = {
            'old_value': old_value,
            'new_value': new_value,
            'current_value': state.current_value,
            'same_value_duration': state.same_value_duration,
            'str': str,
            'int': int,
            'float': float,
            'len': len,
            'abs': abs,
            'min': min,
            'max': max,
        }
        
        try:
            # Only allow simple expressions (no imports, exec, etc.)
            if any(keyword in condition for keyword in ['import', 'exec', 'eval', '__']):
                logger.warning(f"Unsafe custom condition rejected: {condition}")
                return False
            
            result = eval(condition, {"__builtins__": {}}, safe_context)
            return bool(result)
        
        except Exception as e:
            logger.error(f"Error in custom condition '{condition}': {e}")
            return False
    
    async def _send_notification(self, rule: NotificationRule, state: MonitorState,
                               old_value: Any, new_value: Any):
        """Send notification according to rule"""
        
        # Format message using template
        message = await self._format_message(rule.message_template, rule, state, old_value, new_value)
        
        # Determine target chats
        target_chats = await self._get_target_chats(rule.target_chats)
        
        # Update cooldown
        if rule.id:
            state.notification_cooldowns[rule.id] = datetime.now()
        
        # Create notification history record
        notification = NotificationHistory(
            rule_id=rule.id,
            monitor_name=state.monitor_name,
            db_name=state.db_name,
            old_value=str(old_value) if old_value is not None else None,
            new_value=str(new_value) if new_value is not None else None,
            message=message,
            target_chats=",".join(map(str, target_chats))
        )
        
        # Send notification
        success = True
        error_message = None
        
        try:
            if self.notification_callback:
                await self.notification_callback(message, target_chats, rule.priority)
            else:
                logger.warning("No notification callback set")
                success = False
                error_message = "No notification callback configured"
        
        except Exception as e:
            logger.error(f"Failed to send notification: {e}")
            success = False
            error_message = str(e)
        
        # Log to history
        notification.success = success
        notification.error_message = error_message
        self.database.log_notification(notification)
        
        logger.info(f"Notification sent for rule '{rule.name}': {message}")
    
    async def _format_message(self, template: str, rule: NotificationRule, 
                            state: MonitorState, old_value: Any, new_value: Any) -> str:
        """Format notification message using template"""
        
        # Available template variables
        variables = {
            'monitor_name': state.monitor_name,
            'db_name': state.db_name,
            'old_value': old_value,
            'new_value': new_value,
            'rule_name': rule.name,
            'priority': rule.priority.value,
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'same_value_duration': self._format_duration(state.same_value_duration)
        }
        
        # Replace variables in template
        try:
            return template.format(**variables)
        except Exception as e:
            logger.error(f"Error formatting message template: {e}")
            return f"🔔 {state.monitor_name}: {old_value} → {new_value}"
    
    async def _get_target_chats(self, target_chats_config: str) -> List[int]:
        """Parse target chats configuration"""
        if target_chats_config == "all":
            # Return all authorized chats (this should be injected from telegram bot)
            return []  # Will be handled by the notification callback
        
        # Parse comma-separated chat IDs
        try:
            chat_ids = []
            for chat_id_str in target_chats_config.split(","):
                chat_id_str = chat_id_str.strip()
                if chat_id_str:
                    chat_ids.append(int(chat_id_str))
            return chat_ids
        except ValueError:
            logger.error(f"Invalid target_chats format: {target_chats_config}")
            return []
    
    def _format_duration(self, seconds: int) -> str:
        """Format duration in human-readable format"""
        if seconds < 60:
            return f"{seconds}с"
        elif seconds < 3600:
            return f"{seconds // 60}м {seconds % 60}с"
        else:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            return f"{hours}ч {minutes}м"
    
    def create_default_rules(self, monitor_name: str, db_name: str):
        """Create default notification rules for a new monitor"""
        
        # Rule 1: Notify on any change
        change_rule = NotificationRule(
            name=f"{monitor_name} - Value Changed",
            monitor_name=monitor_name,
            db_name=db_name,
            condition_type=ConditionType.VALUE_CHANGED,
            cooldown_seconds=60,  # 1 minute
            priority=NotificationPriority.MEDIUM,
            message_template="🔄 {monitor_name}: {old_value} → {new_value}",
            target_chats="all"
        )
        
        # Rule 2: Alert if stuck for 1 hour
        stuck_rule = NotificationRule(
            name=f"{monitor_name} - Value Stuck",
            monitor_name=monitor_name,
            db_name=db_name,
            condition_type=ConditionType.VALUE_UNCHANGED,
            condition_duration=3600,  # 1 hour
            cooldown_seconds=1800,  # 30 minutes
            priority=NotificationPriority.HIGH,
            message_template="⚠️ {monitor_name} не изменяется уже {same_value_duration}",
            target_chats="all"
        )
        
        # Create rules in database
        self.database.create_rule(change_rule)
        self.database.create_rule(stuck_rule)
        
        logger.info(f"Created default notification rules for {db_name}.{monitor_name}")
    
    def get_monitor_states(self) -> Dict[str, MonitorState]:
        """Get all monitor states"""
        return self.monitor_states.copy()
    
    def get_rules_summary(self) -> Dict[str, Any]:
        """Get summary of all rules"""
        all_rules = self.database.get_rules(active_only=False)
        
        summary = {
            'total_rules': len(all_rules),
            'active_rules': len([r for r in all_rules if r.is_active]),
            'rules_by_priority': {},
            'rules_by_monitor': {}
        }
        
        # Count by priority
        for rule in all_rules:
            priority = rule.priority.value
            summary['rules_by_priority'][priority] = summary['rules_by_priority'].get(priority, 0) + 1
        
        # Count by monitor
        for rule in all_rules:
            monitor_key = f"{rule.db_name}.{rule.monitor_name}"
            summary['rules_by_monitor'][monitor_key] = summary['rules_by_monitor'].get(monitor_key, 0) + 1
        
        return summary