from fastapi import FastAPI, HTTPException, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
import uvicorn
import time
from loguru import logger

from notifications import NotificationRulesEngine, NotificationDatabase
from notifications.models import NotificationRule, NotificationHistory, ConditionType, NotificationPriority


class RuleCreate(BaseModel):
    name: str
    monitor_name: str
    db_name: str
    condition_type: ConditionType
    condition_value: Optional[str] = None
    condition_duration: Optional[int] = None
    cooldown_seconds: int = 300
    priority: NotificationPriority = NotificationPriority.MEDIUM
    message_template: str = "🔔 {monitor_name}: {old_value} → {new_value}"
    target_chats: str = "all"
    is_active: bool = True


class RuleUpdate(BaseModel):
    name: Optional[str] = None
    monitor_name: Optional[str] = None
    db_name: Optional[str] = None
    condition_type: Optional[ConditionType] = None
    condition_value: Optional[str] = None
    condition_duration: Optional[int] = None
    cooldown_seconds: Optional[int] = None
    priority: Optional[NotificationPriority] = None
    message_template: Optional[str] = None
    target_chats: Optional[str] = None
    is_active: Optional[bool] = None


class NotificationStats(BaseModel):
    total_rules: int
    active_rules: int
    recent_notifications_24h: int
    success_rate_7d: float


def create_app(rules_engine: NotificationRulesEngine = None, app_instance = None) -> FastAPI:
    """Create FastAPI application"""
    
    app = FastAPI(
        title="Database Monitor Notifications",
        description="Web interface for managing database monitoring notification rules",
        version="1.0.0"
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Mount static files
    app.mount("/static", StaticFiles(directory="static"), name="static")
    
    # Global rules engine instance
    if rules_engine is None:
        rules_engine = NotificationRulesEngine()
    
    def get_rules_engine() -> NotificationRulesEngine:
        return rules_engine
    
    def get_database() -> NotificationDatabase:
        return rules_engine.database
    
    @app.get("/", response_class=HTMLResponse)
    async def read_root():
        """Serve main page"""
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Database Monitor Notifications</title>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
            <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
            <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
            <script src="https://unpkg.com/vue@3/dist/vue.global.js"></script>
            <script src="https://unpkg.com/axios/dist/axios.min.js"></script>
        </head>
        <body>
            <div id="app"></div>
            <script src="/static/app.js?v=1.4"></script>
        </body>
        </html>
        """
    
    # API Routes
    
    @app.get("/api/stats", response_model=NotificationStats)
    async def get_stats(db: NotificationDatabase = Depends(get_database)):
        """Get notification statistics"""
        stats = db.get_stats()
        return NotificationStats(**stats)
    
    @app.get("/api/rules", response_model=List[NotificationRule])
    async def get_rules(
        monitor_name: Optional[str] = None,
        db_name: Optional[str] = None,
        active_only: bool = True,
        db: NotificationDatabase = Depends(get_database)
    ):
        """Get notification rules"""
        return db.get_rules(monitor_name=monitor_name, db_name=db_name, active_only=active_only)
    
    @app.post("/api/rules", response_model=dict)
    async def create_rule(
        rule_data: RuleCreate,
        db: NotificationDatabase = Depends(get_database)
    ):
        """Create new notification rule"""
        rule = NotificationRule(
            name=rule_data.name,
            monitor_name=rule_data.monitor_name,
            db_name=rule_data.db_name,
            condition_type=rule_data.condition_type,
            condition_value=rule_data.condition_value,
            condition_duration=rule_data.condition_duration,
            cooldown_seconds=rule_data.cooldown_seconds,
            priority=rule_data.priority,
            message_template=rule_data.message_template,
            target_chats=rule_data.target_chats,
            is_active=rule_data.is_active
        )
        
        rule_id = db.create_rule(rule)
        return {"id": rule_id, "message": "Rule created successfully"}
    
    @app.put("/api/rules/{rule_id}", response_model=dict)
    async def update_rule(
        rule_id: int,
        rule_data: RuleUpdate,
        db: NotificationDatabase = Depends(get_database)
    ):
        """Update notification rule"""
        # Get existing rule
        existing_rules = db.get_rules(active_only=False)
        existing_rule = next((r for r in existing_rules if r.id == rule_id), None)
        
        if not existing_rule:
            raise HTTPException(status_code=404, detail="Rule not found")
        
        # Update fields
        for field, value in rule_data.model_dump(exclude_unset=True).items():
            setattr(existing_rule, field, value)
        
        success = db.update_rule(existing_rule)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update rule")
        
        return {"message": "Rule updated successfully"}
    
    @app.delete("/api/rules/{rule_id}", response_model=dict)
    async def delete_rule(
        rule_id: int,
        db: NotificationDatabase = Depends(get_database)
    ):
        """Delete notification rule"""
        success = db.delete_rule(rule_id)
        if not success:
            raise HTTPException(status_code=404, detail="Rule not found")
        
        return {"message": "Rule deleted successfully"}
    
    @app.delete("/api/monitors/{monitor_name}/disable")
    async def disable_monitor(
        monitor_name: str,
        db_name: str,
        db: NotificationDatabase = Depends(get_database)
    ):
        """Disable all notifications for a monitor (delete all rules and mark as disabled)"""
        # Get all rules for this monitor
        rules = db.get_rules(monitor_name=monitor_name, db_name=db_name, active_only=False)
        
        # Delete all rules
        deleted_count = 0
        for rule in rules:
            if db.delete_rule(rule.id):
                deleted_count += 1
        
        # Mark monitor as explicitly disabled
        db.mark_monitor_disabled(monitor_name, db_name)
        
        return {
            "message": f"Monitor disabled successfully",
            "deleted_rules": deleted_count,
            "monitor_name": monitor_name,
            "db_name": db_name
        }
    
    @app.post("/api/monitors/{monitor_name}/enable")
    async def enable_monitor(
        monitor_name: str,
        db_name: str,
        db: NotificationDatabase = Depends(get_database),
        rules_engine: NotificationRulesEngine = Depends(get_rules_engine)
    ):
        """Re-enable a monitor (remove from disabled list and create default rules)"""
        # Remove from disabled list
        db.enable_monitor(monitor_name, db_name)
        
        # Create default rules
        rules_engine.create_default_rules(monitor_name, db_name)
        
        return {
            "message": f"Monitor enabled successfully", 
            "monitor_name": monitor_name,
            "db_name": db_name
        }
    
    @app.get("/api/history", response_model=List[NotificationHistory])
    async def get_history(
        limit: int = 100,
        monitor_name: Optional[str] = None,
        db: NotificationDatabase = Depends(get_database)
    ):
        """Get notification history"""
        return db.get_notification_history(limit=limit, monitor_name=monitor_name)
    
    @app.get("/api/monitors", response_model=Dict[str, Any])
    async def get_monitors(
        engine: NotificationRulesEngine = Depends(get_rules_engine),
        db: NotificationDatabase = Depends(get_database)
    ):
        """Get current monitor states with disable status"""
        monitor_data = {}
        
        # Get data from notification engine states
        states = engine.get_monitor_states()
        for key, state in states.items():
            monitor_data[key] = {
                "monitor_name": state.monitor_name,
                "db_name": state.db_name,
                "current_value": state.current_value,
                "previous_value": state.previous_value,
                "last_change_time": state.last_change_time.isoformat() if state.last_change_time else None,
                "same_value_duration": state.same_value_duration,
                "active_cooldowns": len(state.notification_cooldowns),
                "is_disabled": db.is_monitor_disabled(state.monitor_name, state.db_name),
                "source": "rules_engine"
            }
        
        # If app_instance is available, also get data from database monitors
        if app_instance and hasattr(app_instance, 'monitors'):
            for db_name, monitor in app_instance.monitors.items():
                if hasattr(monitor, 'monitor_states'):
                    for monitor_key, db_state in monitor.monitor_states.items():
                        key = f"{db_name}.{db_state.monitor_name}"
                        
                        # Create combined view
                        current_value = getattr(db_state, 'last_value', 'Unknown')
                        monitor_data[key] = {
                            "monitor_name": db_state.monitor_name,
                            "db_name": db_name,
                            "current_value": current_value,
                            "previous_value": getattr(db_state, 'previous_value', None),
                            "last_change_time": getattr(db_state, 'last_check', None),
                            "same_value_duration": 0,
                            "active_cooldowns": 0,
                            "is_disabled": db.is_monitor_disabled(db_state.monitor_name, db_name),
                            "source": "database_monitor",
                            "check_interval": getattr(db_state, 'check_interval', 60)
                        }
        
        return monitor_data
    
    @app.get("/api/condition-types")
    async def get_condition_types():
        """Get available condition types"""
        return [
            {"value": ct.value, "label": ct.value.replace("_", " ").title()}
            for ct in ConditionType
        ]
    
    @app.get("/api/priorities")
    async def get_priorities():
        """Get available priority levels"""
        return [
            {"value": p.value, "label": p.value.title()}
            for p in NotificationPriority
        ]
    
    @app.post("/api/test-rule", response_model=dict)
    async def test_rule(
        rule_data: RuleCreate,
        test_old_value: str = "",
        test_new_value: str = "",
        engine: NotificationRulesEngine = Depends(get_rules_engine)
    ):
        """Test a notification rule with sample values"""
        # Create temporary rule (don't save to database)
        temp_rule = NotificationRule(
            name=rule_data.name,
            monitor_name=rule_data.monitor_name,
            db_name=rule_data.db_name,
            condition_type=rule_data.condition_type,
            condition_value=rule_data.condition_value,
            condition_duration=rule_data.condition_duration,
            priority=rule_data.priority,
            message_template=rule_data.message_template,
            target_chats=rule_data.target_chats
        )
        
        # Test condition evaluation
        from notifications.models import MonitorState
        test_state = MonitorState(
            monitor_name=rule_data.monitor_name,
            db_name=rule_data.db_name,
            current_value=test_new_value,
            same_value_duration=0 if test_old_value != test_new_value else 3600  # Simulate 1 hour
        )
        
        would_trigger = await engine._evaluate_condition(temp_rule, test_state, test_old_value, test_new_value)
        formatted_message = await engine._format_message(temp_rule.message_template, temp_rule, test_state, test_old_value, test_new_value)
        
        return {
            "would_trigger": would_trigger,
            "formatted_message": formatted_message,
            "test_values": {
                "old_value": test_old_value,
                "new_value": test_new_value
            }
        }
    
    @app.get("/api/debug")
    async def debug_info(engine: NotificationRulesEngine = Depends(get_rules_engine)):
        """Debug information"""
        debug_data = {
            "rules_engine_states": len(engine.get_monitor_states()),
            "app_instance_available": app_instance is not None,
            "database_monitors": {},
            "rules_engine_details": {}
        }
        
        # Get rules engine details
        for key, state in engine.get_monitor_states().items():
            debug_data["rules_engine_details"][key] = {
                "current_value": state.current_value,
                "monitor_name": state.monitor_name,
                "db_name": state.db_name
            }
        
        # Get database monitor details
        if app_instance and hasattr(app_instance, 'monitors'):
            for db_name, monitor in app_instance.monitors.items():
                debug_data["database_monitors"][db_name] = {
                    "has_monitor_states": hasattr(monitor, 'monitor_states'),
                    "monitor_states_count": len(getattr(monitor, 'monitor_states', {})),
                    "running": getattr(monitor, 'running', False)
                }
                
                if hasattr(monitor, 'monitor_states'):
                    for key, state in monitor.monitor_states.items():
                        debug_data["database_monitors"][db_name][f"state_{key}"] = {
                            "monitor_name": getattr(state, 'monitor_name', 'Unknown'),
                            "last_value": getattr(state, 'last_value', 'Unknown'),
                            "last_check": getattr(state, 'last_check', 'Unknown')
                        }
        
        return debug_data
    
    @app.post("/api/force-test", response_model=dict)
    async def force_test_notification(engine: NotificationRulesEngine = Depends(get_rules_engine)):
        """Force trigger a test notification"""
        try:
            # Simulate a value change for testing
            test_db_name = "voron_migr_db"
            test_monitor_name = "bdm_file_task_status"
            old_value = "test_old"
            new_value = "test_new_" + str(int(time.time()))
            
            # Process through notification rules engine
            await engine.process_value_change(test_db_name, test_monitor_name, old_value, new_value)
            
            return {"success": True, "message": f"Forced test notification sent: {old_value} → {new_value}"}
            
        except Exception as e:
            logger.error(f"Error in force test: {e}")
            return {"success": False, "error": str(e)}
    
    @app.post("/api/test-all-rules", response_model=dict)
    async def test_all_rules(engine: NotificationRulesEngine = Depends(get_rules_engine)):
        """Test all active notification rules"""
        try:
            # Get all active rules
            active_rules = engine.database.get_rules(active_only=True)
            if not active_rules:
                return {"success": False, "error": "Нет активных правил для тестирования"}
            
            tested_count = 0
            triggered_count = 0
            
            for rule in active_rules:
                monitor_key = f"{rule.db_name}.{rule.monitor_name}"
                
                # Get or create state for testing
                if monitor_key not in engine.monitor_states:
                    from notifications.models import MonitorState
                    engine.monitor_states[monitor_key] = MonitorState(
                        monitor_name=rule.monitor_name,
                        db_name=rule.db_name,
                        current_value="test_current_value",
                        previous_value="test_previous_value"
                    )
                
                state = engine.monitor_states[monitor_key]
                
                # Test with simulated values
                old_value = "test_old_" + str(int(time.time()))
                new_value = "test_new_" + str(int(time.time() + 1))
                
                try:
                    # Force evaluation by temporarily clearing cooldowns
                    original_cooldowns = state.notification_cooldowns.copy()
                    state.notification_cooldowns.clear()
                    
                    # Update state for testing
                    state.current_value = new_value
                    state.previous_value = old_value
                    
                    # Process the change
                    await engine.process_value_change(rule.db_name, rule.monitor_name, old_value, new_value)
                    tested_count += 1
                    triggered_count += 1  # Assume it triggered since we cleared cooldowns
                    
                    # Restore cooldowns
                    state.notification_cooldowns = original_cooldowns
                    
                except Exception as e:
                    logger.error(f"Error testing rule {rule.name}: {e}")
                    tested_count += 1
            
            return {
                "success": True, 
                "tested_count": tested_count,
                "triggered_count": triggered_count,
                "message": f"Протестировано {tested_count} правил, сработало {triggered_count}"
            }
            
        except Exception as e:
            logger.error(f"Error in test all rules: {e}")
            return {"success": False, "error": str(e)}
    
    return app


async def start_web_server(port: int = 8000, host: str = "0.0.0.0", 
                          rules_engine: NotificationRulesEngine = None,
                          app_instance = None):
    """Start the web server"""
    app = create_app(rules_engine, app_instance)
    
    config = uvicorn.Config(
        app=app,
        host=host,
        port=port,
        log_level="info"
    )
    
    server = uvicorn.Server(config)
    await server.serve()