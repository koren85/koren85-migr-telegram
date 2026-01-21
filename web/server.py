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


class MonitorCreate(BaseModel):
    name: str
    db_name: str
    sql_query: str
    check_interval: int = 60
    is_active: bool = True
    driver: Optional[str] = None
    url: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    jar_path: Optional[str] = None


class MonitorUpdate(BaseModel):
    name: Optional[str] = None
    db_name: Optional[str] = None
    sql_query: Optional[str] = None
    check_interval: Optional[int] = None
    is_active: Optional[bool] = None
    driver: Optional[str] = None
    url: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    jar_path: Optional[str] = None


class RuleCopyRequest(BaseModel):
    target_monitor_name: Optional[str] = None  # If provided, copy rule to this monitor
    target_db_name: Optional[str] = None  # If provided, use this db_name


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
            <script src="/static/app.js?v=2.0"></script>
        </body>
        </html>
        """
    
    # API Routes
    
    @app.get("/api/stats", response_model=NotificationStats)
    async def get_stats(db: NotificationDatabase = Depends(get_database)):
        """Get notification statistics"""
        stats = db.get_stats()
        return NotificationStats(**stats)

    @app.get("/api/queue/stats", response_model=dict)
    async def get_queue_stats():
        """Get notification queue statistics (rate limiting, pending messages, etc.)"""
        if app_instance and hasattr(app_instance, 'notification_queue') and app_instance.notification_queue:
            return app_instance.notification_queue.get_stats()
        return {
            'running': False,
            'error': 'Notification queue not available'
        }

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
        logger.info(f"Creating rule: name={rule_data.name}, monitor_name={rule_data.monitor_name}, db_name={rule_data.db_name}")
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
        logger.info(f"Updating rule {rule_id}: received data = {rule_data.model_dump(exclude_unset=True)}")
        
        # Get existing rule
        existing_rules = db.get_rules(active_only=False)
        existing_rule = next((r for r in existing_rules if r.id == rule_id), None)
        
        if not existing_rule:
            raise HTTPException(status_code=404, detail="Rule not found")
        
        logger.info(f"Before update: monitor_name={existing_rule.monitor_name}, db_name={existing_rule.db_name}")
        
        # Update fields - preserve monitor_name and db_name if not provided
        update_data = rule_data.model_dump(exclude_unset=True)

        # Ensure critical fields are preserved if not explicitly updated
        if 'monitor_name' not in update_data and existing_rule.monitor_name:
            update_data['monitor_name'] = existing_rule.monitor_name
        if 'db_name' not in update_data and existing_rule.db_name:
            update_data['db_name'] = existing_rule.db_name

        for field, value in update_data.items():
            setattr(existing_rule, field, value)
        
        logger.info(f"After update: monitor_name={existing_rule.monitor_name}, db_name={existing_rule.db_name}")
        
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
    
    @app.post("/api/rules/{rule_id}/copy", response_model=dict)
    async def copy_rule(
        rule_id: int,
        copy_request: Optional[RuleCopyRequest] = None,
        db: NotificationDatabase = Depends(get_database)
    ):
        """Copy notification rule with new name and optionally to different monitor"""
        # Get existing rule
        existing_rules = db.get_rules(active_only=False)
        existing_rule = next((r for r in existing_rules if r.id == rule_id), None)

        if not existing_rule:
            raise HTTPException(status_code=404, detail="Rule not found")

        # Determine target monitor and db_name
        target_monitor_name = existing_rule.monitor_name
        target_db_name = existing_rule.db_name

        if copy_request:
            if copy_request.target_monitor_name:
                target_monitor_name = copy_request.target_monitor_name
            if copy_request.target_db_name:
                target_db_name = copy_request.target_db_name

        # Validate that target monitor exists
        monitors = db.get_monitors(db_name=target_db_name, active_only=False)
        monitor_exists = any(m.name == target_monitor_name for m in monitors)

        if not monitor_exists:
            logger.warning(f"Target monitor {target_monitor_name} in {target_db_name} does not exist")
            # Still allow creation for flexibility, but warn

        # Create a copy with modified name
        rule_suffix = " (копия)" if target_monitor_name == existing_rule.monitor_name else f" (для {target_monitor_name})"
        new_rule = NotificationRule(
            name=f"{existing_rule.name}{rule_suffix}",
            monitor_name=target_monitor_name,
            db_name=target_db_name,
            condition_type=existing_rule.condition_type,
            condition_value=existing_rule.condition_value,
            condition_duration=existing_rule.condition_duration,
            cooldown_seconds=existing_rule.cooldown_seconds,
            priority=existing_rule.priority,
            message_template=existing_rule.message_template,
            target_chats=existing_rule.target_chats,
            is_active=existing_rule.is_active
        )

        new_rule_id = db.create_rule(new_rule)
        logger.info(f"Copied rule {existing_rule.name} to {new_rule.name} for monitor {target_monitor_name}")
        return {"id": new_rule_id, "message": "Rule copied successfully", "monitor_name": target_monitor_name}
    
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
    
    @app.get("/api/monitor-states", response_model=Dict[str, Any])
    async def get_monitor_states(
        engine: NotificationRulesEngine = Depends(get_rules_engine),
        db: NotificationDatabase = Depends(get_database)
    ):
        """Get current monitor states with disable status (legacy endpoint for runtime states)"""
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

    @app.get("/api/monitors")
    async def get_monitors_list(db: NotificationDatabase = Depends(get_database)):
        """Get all monitors from database"""
        try:
            from notifications.models import DatabaseMonitorConfig
            monitors = db.get_monitors(active_only=False)
            return [{
                "id": m.id,
                "name": m.name,
                "db_name": m.db_name,
                "sql_query": m.sql_query,
                "check_interval": m.check_interval,
                "is_active": m.is_active,
                "driver": m.driver,
                "url": m.url,
                "username": m.username,
                "password": m.password,
                "jar_path": m.jar_path,
                "created_at": m.created_at.isoformat() if m.created_at else None,
                "updated_at": m.updated_at.isoformat() if m.updated_at else None
            } for m in monitors]
        except Exception as e:
            logger.error(f"Error getting monitors: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/api/monitors", response_model=dict)
    async def create_monitor(
        monitor_data: MonitorCreate,
        db: NotificationDatabase = Depends(get_database)
    ):
        """Create new monitor"""
        try:
            from notifications.models import DatabaseMonitorConfig

            # Check if monitor already exists
            if db.monitor_exists(monitor_data.name, monitor_data.db_name):
                raise HTTPException(status_code=400, detail="Monitor with this name already exists for this database")

            monitor = DatabaseMonitorConfig(
                name=monitor_data.name,
                db_name=monitor_data.db_name,
                sql_query=monitor_data.sql_query,
                check_interval=monitor_data.check_interval,
                is_active=monitor_data.is_active,
                driver=monitor_data.driver,
                url=monitor_data.url,
                username=monitor_data.username,
                password=monitor_data.password,
                jar_path=monitor_data.jar_path
            )

            monitor_id = db.create_monitor(monitor)

            # If app_instance has monitor_manager, reload monitors
            if app_instance and hasattr(app_instance, 'monitor_manager'):
                await app_instance.monitor_manager.reload_all_monitors()

            return {"id": monitor_id, "message": "Monitor created successfully"}

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error creating monitor: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.put("/api/monitors/{monitor_id}", response_model=dict)
    async def update_monitor(
        monitor_id: int,
        monitor_data: MonitorUpdate,
        db: NotificationDatabase = Depends(get_database)
    ):
        """Update monitor"""
        try:
            from notifications.models import DatabaseMonitorConfig

            # Get existing monitor
            existing_monitor = db.get_monitor_by_id(monitor_id)
            if not existing_monitor:
                raise HTTPException(status_code=404, detail="Monitor not found")

            # Update fields - preserve critical fields if not provided
            update_data = monitor_data.model_dump(exclude_unset=True)

            # Ensure critical fields are preserved if not explicitly updated
            if 'name' not in update_data and existing_monitor.name:
                update_data['name'] = existing_monitor.name
            if 'db_name' not in update_data and existing_monitor.db_name:
                update_data['db_name'] = existing_monitor.db_name
            if 'sql_query' not in update_data and existing_monitor.sql_query:
                update_data['sql_query'] = existing_monitor.sql_query

            for field, value in update_data.items():
                setattr(existing_monitor, field, value)

            success = db.update_monitor(existing_monitor)
            if not success:
                raise HTTPException(status_code=500, detail="Failed to update monitor")

            # If app_instance has monitor_manager, reload this monitor
            if app_instance and hasattr(app_instance, 'monitor_manager'):
                await app_instance.monitor_manager.reload_monitor(monitor_id)

            return {"message": "Monitor updated successfully"}

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error updating monitor: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.delete("/api/monitors/{monitor_id}", response_model=dict)
    async def delete_monitor(
        monitor_id: int,
        db: NotificationDatabase = Depends(get_database)
    ):
        """Delete monitor and all associated rules"""
        try:
            # Get monitor first to check if it exists
            monitor = db.get_monitor_by_id(monitor_id)
            if not monitor:
                raise HTTPException(status_code=404, detail="Monitor not found")

            # Delete all rules associated with this monitor
            rules = db.get_rules(monitor_name=monitor.name, db_name=monitor.db_name, active_only=False)
            deleted_rules = 0
            for rule in rules:
                if db.delete_rule(rule.id):
                    deleted_rules += 1

            # Stop monitor if running
            if app_instance and hasattr(app_instance, 'monitor_manager'):
                await app_instance.monitor_manager.stop_monitor(monitor_id)

            # Delete from database
            success = db.delete_monitor(monitor_id)
            if not success:
                raise HTTPException(status_code=500, detail="Failed to delete monitor")

            return {
                "message": "Monitor and associated rules deleted successfully",
                "deleted_rules": deleted_rules
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error deleting monitor: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/api/monitors/{monitor_id}/copy", response_model=dict)
    async def copy_monitor(
        monitor_id: int,
        db: NotificationDatabase = Depends(get_database)
    ):
        """Copy monitor with new name"""
        try:
            from notifications.models import DatabaseMonitorConfig
            
            # Get existing monitor
            existing_monitor = db.get_monitor_by_id(monitor_id)
            if not existing_monitor:
                raise HTTPException(status_code=404, detail="Monitor not found")
            
            # Generate unique name for copy
            base_name = f"{existing_monitor.name} (копия)"
            copy_name = base_name
            counter = 2
            while db.monitor_exists(copy_name, existing_monitor.db_name):
                copy_name = f"{base_name} {counter}"
                counter += 1
            
            # Create a copy
            new_monitor = DatabaseMonitorConfig(
                name=copy_name,
                db_name=existing_monitor.db_name,
                sql_query=existing_monitor.sql_query,
                check_interval=existing_monitor.check_interval,
                is_active=False,  # Disabled by default for safety
                driver=existing_monitor.driver,
                url=existing_monitor.url,
                username=existing_monitor.username,
                password=existing_monitor.password,
                jar_path=existing_monitor.jar_path
            )
            
            new_monitor_id = db.create_monitor(new_monitor)

            # Automatically copy rules from original monitor
            original_rules = db.get_rules(monitor_name=existing_monitor.name, db_name=existing_monitor.db_name, active_only=False)
            copied_rules = 0
            for rule in original_rules:
                # Create a copy of the rule for the new monitor
                from notifications.models import NotificationRule
                new_rule = NotificationRule(
                    name=f"{rule.name} (для {copy_name})",
                    monitor_name=copy_name,  # Point to the new monitor
                    db_name=rule.db_name,
                    condition_type=rule.condition_type,
                    condition_value=rule.condition_value,
                    condition_duration=rule.condition_duration,
                    cooldown_seconds=rule.cooldown_seconds,
                    priority=rule.priority,
                    message_template=rule.message_template,
                    target_chats=rule.target_chats,
                    is_active=False  # Disabled by default to match monitor state
                )
                try:
                    db.create_rule(new_rule)
                    copied_rules += 1
                except Exception as e:
                    logger.warning(f"Failed to copy rule {rule.name}: {e}")

            logger.info(f"Copied monitor {existing_monitor.name} to {copy_name} with {copied_rules} rules")
            return {"id": new_monitor_id, "message": f"Monitor copied successfully with {copied_rules} rules", "rules_copied": copied_rules}
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error copying monitor: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/api/monitors/{monitor_id}/test", response_model=dict)
    async def test_monitor(
        monitor_id: int,
        db: NotificationDatabase = Depends(get_database)
    ):
        """Test monitor by executing its SQL query"""
        try:
            from database.connection import DatabaseConnection
            from config.settings import DatabaseConfig

            # Get monitor
            monitor = db.get_monitor_by_id(monitor_id)
            if not monitor:
                raise HTTPException(status_code=404, detail="Monitor not found")

            # Create temporary database connection
            db_config = DatabaseConfig(
                name=monitor.db_name,
                driver=monitor.driver or "",
                url=monitor.url or "",
                username=monitor.username or "",
                password=monitor.password or "",
                jar_path=monitor.jar_path or "",
                tables=[]
            )

            connection = DatabaseConnection(db_config)

            try:
                # Try to connect
                if not connection.connect():
                    return {
                        "success": False,
                        "error": "Failed to connect to database",
                        "monitor_name": monitor.name
                    }

                # Execute query
                result = connection.execute_query(monitor.sql_query)

                if result is None:
                    return {
                        "success": False,
                        "error": "Query returned no result (connection or query error)",
                        "monitor_name": monitor.name
                    }

                return {
                    "success": True,
                    "result": str(result),
                    "monitor_name": monitor.name,
                    "message": "Monitor test successful"
                }

            finally:
                # Always disconnect
                connection.disconnect()

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error testing monitor: {e}")
            return {
                "success": False,
                "error": str(e),
                "monitor_name": monitor.name if 'monitor' in locals() else "unknown"
            }

    @app.post("/api/rules/bulk-delete", response_model=dict)
    async def bulk_delete_rules(
        rule_ids: List[int],
        db: NotificationDatabase = Depends(get_database)
    ):
        """Delete multiple rules at once"""
        try:
            deleted_count = 0
            failed_count = 0

            for rule_id in rule_ids:
                if db.delete_rule(rule_id):
                    deleted_count += 1
                else:
                    failed_count += 1

            return {
                "message": f"Deleted {deleted_count} rules successfully",
                "deleted_count": deleted_count,
                "failed_count": failed_count
            }

        except Exception as e:
            logger.error(f"Error in bulk delete rules: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/api/monitors/bulk-delete", response_model=dict)
    async def bulk_delete_monitors(
        monitor_ids: List[int],
        db: NotificationDatabase = Depends(get_database)
    ):
        """Delete multiple monitors and their associated rules at once"""
        try:
            deleted_monitors = 0
            deleted_rules = 0
            failed_count = 0

            for monitor_id in monitor_ids:
                try:
                    # Get monitor
                    monitor = db.get_monitor_by_id(monitor_id)
                    if not monitor:
                        failed_count += 1
                        continue

                    # Delete all rules associated with this monitor
                    rules = db.get_rules(monitor_name=monitor.name, db_name=monitor.db_name, active_only=False)
                    for rule in rules:
                        if db.delete_rule(rule.id):
                            deleted_rules += 1

                    # Stop monitor if running
                    if app_instance and hasattr(app_instance, 'monitor_manager'):
                        await app_instance.monitor_manager.stop_monitor(monitor_id)

                    # Delete monitor
                    if db.delete_monitor(monitor_id):
                        deleted_monitors += 1
                    else:
                        failed_count += 1

                except Exception as e:
                    logger.error(f"Error deleting monitor {monitor_id}: {e}")
                    failed_count += 1

            return {
                "message": f"Deleted {deleted_monitors} monitors and {deleted_rules} rules successfully",
                "deleted_monitors": deleted_monitors,
                "deleted_rules": deleted_rules,
                "failed_count": failed_count
            }

        except Exception as e:
            logger.error(f"Error in bulk delete monitors: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
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

    @app.post("/api/rules/{rule_id}/test")
    async def test_single_rule(rule_id: int, engine: NotificationRulesEngine = Depends(get_rules_engine)):
        """Send test notification for a specific rule"""
        try:
            # Get rule
            rule = None
            for r in engine.database.get_rules(active_only=False):
                if r.id == rule_id:
                    rule = r
                    break

            if not rule:
                raise HTTPException(status_code=404, detail="Rule not found")

            # Get monitor state
            monitor_key = f"{rule.db_name}.{rule.monitor_name}"
            state = engine.monitor_states.get(monitor_key)

            # Get real or test values
            test_old = state.previous_value if state else "old_value"
            test_new = state.current_value if state else "new_value"

            # Create a temporary state if needed for message formatting
            if not state:
                from notifications.models import MonitorState
                state = MonitorState(
                    monitor_name=rule.monitor_name,
                    db_name=rule.db_name,
                    current_value=test_new,
                    same_value_duration=0
                )

            # Format message using the rule's template
            formatted_message = await engine._format_message(
                rule.message_template, rule, state, test_old, test_new
            )

            # Add test prefix
            message = f"🧪 TEST: {formatted_message}"

            # Send test notification
            if engine.notification_callback:
                target_chats = None if rule.target_chats == "all" else [
                    int(cid.strip()) for cid in rule.target_chats.split(",") if cid.strip()
                ]

                await engine.notification_callback(message, target_chats, rule.priority)

                return {
                    "success": True,
                    "message": "Test notification sent",
                    "rule": rule.name,
                    "old_value": str(test_old),
                    "new_value": str(test_new)
                }
            else:
                raise HTTPException(status_code=500, detail="Notification callback not configured")

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error testing rule: {e}")
            raise HTTPException(status_code=500, detail=str(e))

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
