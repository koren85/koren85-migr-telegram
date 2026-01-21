#!/usr/bin/env python3
"""
Database Monitoring Telegram Bot

Monitors database tables for value changes and sends notifications via Telegram.
Supports multiple databases with JDBC connections.
"""

import asyncio
import argparse
import signal
import sys
from pathlib import Path
from typing import Dict
from loguru import logger

from config import Settings
from database import DatabaseMonitor
from telegram_bot import TelegramBot
from notifications import NotificationRulesEngine
from web import create_app


class DatabaseMonitoringApp:
    """Main application for database monitoring"""
    
    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = config_path
        self.settings = None
        self.telegram_bot = None
        self.monitors: Dict[str, DatabaseMonitor] = {}
        self.notification_engine = None
        self.web_server_task = None
        self.running = False
    
    async def initialize(self):
        """Initialize the application"""
        try:
            # Load configuration
            self.settings = Settings.load_from_file(self.config_path)
            logger.info(f"Configuration loaded from {self.config_path}")
            
            # Setup logging
            self._setup_logging()
            
            # Initialize notification engine
            self.notification_engine = NotificationRulesEngine()
            
            # Initialize Telegram bot
            self.telegram_bot = TelegramBot(self.settings)
            
            # Set up notification callback for rules engine
            self.notification_engine.set_notification_callback(self._send_smart_notification)
            
            # Initialize database monitors
            await self._initialize_monitors()
            
            # Set monitors in telegram bot for manual queries
            self.telegram_bot.set_monitors(self.monitors)
            
            # Set app instance for access to notification engine
            self.telegram_bot._app_instance = self
            
            # Create default rules for new monitors
            await self._create_default_rules()
            
            # Initial state sync
            await self.sync_monitor_states()
            
            logger.info("Application initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize application: {e}")
            raise
    
    def _setup_logging(self):
        """Setup logging configuration"""
        # Create logs directory
        log_file = Path(self.settings.logging.file)
        log_file.parent.mkdir(exist_ok=True)
        
        # Configure loguru
        logger.remove()  # Remove default handler
        logger.add(
            sys.stdout,
            level=self.settings.logging.level,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
        )
        logger.add(
            self.settings.logging.file,
            level=self.settings.logging.level,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
            rotation="10 MB",
            retention="1 week"
        )
    
    async def _initialize_monitors(self):
        """Initialize database monitors"""
        successful_monitors = 0
        total_monitors = len(self.settings.databases)
        
        for db_config in self.settings.databases:
            try:
                monitor = DatabaseMonitor(
                    db_config=db_config,
                    change_callback=self._on_value_change
                )
                self.monitors[db_config.name] = monitor
                successful_monitors += 1
                logger.info(f"Monitor initialized for database: {db_config.name}")
                
            except Exception as e:
                logger.error(f"Failed to initialize monitor for {db_config.name}: {e}")
        
        logger.info(f"Successfully initialized {successful_monitors}/{total_monitors} database monitors")
    
    async def _create_default_rules(self):
        """Create default notification rules for monitors"""
        for db_config in self.settings.databases:
            for table_config in db_config.tables:
                # Get monitor name (either new format or legacy)
                if hasattr(table_config, 'name') and table_config.name:
                    monitor_name = table_config.name
                else:
                    monitor_name = f"{table_config.table}.{table_config.column}"
                
                # Check if rules already exist for this monitor
                existing_rules = self.notification_engine.database.get_rules(
                    monitor_name=monitor_name, 
                    db_name=db_config.name
                )
                
                # Check if monitor was explicitly disabled
                is_disabled = self.notification_engine.database.is_monitor_disabled(
                    monitor_name, db_config.name
                )
                
                # Only create default rules if no existing rules AND monitor is not explicitly disabled
                if not existing_rules and not is_disabled:
                    self.notification_engine.create_default_rules(monitor_name, db_config.name)
                elif is_disabled:
                    logger.debug(f"Skipping rule creation for disabled monitor: {monitor_name} ({db_config.name})")
    
    async def _send_smart_notification(self, message: str, target_chats: list = None, priority=None):
        """Smart notification callback for rules engine"""
        if not self.telegram_bot:
            return
        
        # If no specific chats provided, use all authorized chats
        if not target_chats:
            target_chats = list(self.telegram_bot.authorized_chat_ids)
        
        # Add priority emoji based on priority level
        priority_emojis = {
            'low': '🔵',
            'medium': '🟡', 
            'high': '🟠',
            'critical': '🔴'
        }
        
        if priority and hasattr(priority, 'value'):
            priority_emoji = priority_emojis.get(priority.value, '🔔')
            message = f"{priority_emoji} {message}"
        
        # Send to all target chats
        for chat_id in target_chats:
            try:
                await self.telegram_bot.bot.send_message(
                    chat_id=chat_id,
                    text=message
                )
            except Exception as e:
                logger.error(f"Failed to send smart notification to {chat_id}: {e}")
    
    async def _on_value_change(self, db_name: str, table_column: str, old_value, new_value):
        """Handle value change notifications"""
        logger.info(f"📊 Value changed in {db_name}.{table_column}: {old_value} -> {new_value}")

        # Process through notification rules engine
        if self.notification_engine:
            logger.debug(f"Sending change to notification engine: db_name='{db_name}', monitor_name='{table_column}'")
            await self.notification_engine.process_value_change(
                db_name, table_column, old_value, new_value
            )
        else:
            logger.warning("⚠️ Notification engine is not initialized!")
    
    async def sync_monitor_states(self):
        """Sync current states from database monitors to notification engine"""
        if not self.notification_engine:
            return
            
        for db_name, monitor in self.monitors.items():
            if hasattr(monitor, 'monitor_states'):
                for monitor_key, db_state in monitor.monitor_states.items():
                    # monitor_key is already in format: db_name.monitor_name
                    # No need to reconstruct it
                    if monitor_key not in self.notification_engine.monitor_states:
                        from notifications.models import MonitorState
                        self.notification_engine.monitor_states[monitor_key] = MonitorState(
                            monitor_name=db_state.monitor_name,
                            db_name=db_name,
                            current_value=getattr(db_state, 'last_value', None)
                        )
                    else:
                        # Update existing state
                        engine_state = self.notification_engine.monitor_states[monitor_key]
                        engine_state.current_value = getattr(db_state, 'last_value', None)
        
        logger.debug("Monitor states synchronized")
        
        # Legacy notification (keep for backwards compatibility)
        # if self.telegram_bot:
        #     await self.telegram_bot.send_change_notification(
        #         db_name, table_column, old_value, new_value
        #     )
    
    async def start(self):
        """Start the application"""
        try:
            self.running = True
            logger.info("Starting database monitoring application")
            
            # Start Telegram bot
            await self.telegram_bot.start_bot()
            
            # Start web server
            await self._start_web_server()
            
            # Wait for startup delay
            if self.settings.monitoring.startup_delay > 0:
                logger.info(f"Waiting {self.settings.monitoring.startup_delay} seconds before starting monitoring...")
                await asyncio.sleep(self.settings.monitoring.startup_delay)
            
            # Start all database monitors
            monitor_tasks = []
            for monitor in self.monitors.values():
                task = asyncio.create_task(monitor.start_monitoring())
                monitor_tasks.append(task)
            
            # Add periodic sync task
            sync_task = asyncio.create_task(self._periodic_sync())
            monitor_tasks.append(sync_task)
            
            logger.info("All monitors started")
            
            # Keep the application running
            try:
                await asyncio.gather(*monitor_tasks)
            except asyncio.CancelledError:
                logger.info("Monitoring tasks cancelled")
        
        except Exception as e:
            logger.error(f"Error starting application: {e}")
            raise
    
    async def _periodic_sync(self):
        """Periodically sync monitor states"""
        while self.running:
            try:
                await asyncio.sleep(30)  # Sync every 30 seconds
                await self.sync_monitor_states()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in periodic sync: {e}")
                await asyncio.sleep(5)
    
    async def _start_web_server(self):
        """Start the web management interface"""
        try:
            from web.server import start_web_server
            
            # Start web server in background
            self.web_server_task = asyncio.create_task(
                start_web_server(port=8090, rules_engine=self.notification_engine, app_instance=self)
            )
            
            logger.info("Web management interface started on http://localhost:8090")
            
        except Exception as e:
            logger.error(f"Failed to start web server: {e}")
            # Don't fail the entire application if web server fails
    
    async def stop(self):
        """Stop the application"""
        if not self.running:
            return
        
        logger.info("Stopping database monitoring application")
        self.running = False
        
        # Stop all monitors
        for monitor in self.monitors.values():
            monitor.stop_monitoring()
        
        # Stop Telegram bot
        if self.telegram_bot:
            await self.telegram_bot.stop_bot()
        
        # Stop web server
        if self.web_server_task:
            self.web_server_task.cancel()
            try:
                await self.web_server_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Application stopped")
    
    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, initiating shutdown...")
            asyncio.create_task(self.stop())
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)


async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Database Monitoring Telegram Bot")
    parser.add_argument(
        "--config",
        default="config.yaml",
        help="Path to configuration file (default: config.yaml)"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging"
    )
    
    args = parser.parse_args()
    
    # Initialize and start application
    app = DatabaseMonitoringApp(args.config)
    
    try:
        await app.initialize()
        
        # Override log level if debug is requested
        if args.debug:
            logger.remove()
            logger.add(sys.stdout, level="DEBUG")
            logger.debug("Debug logging enabled")
        
        # Setup signal handlers
        app._setup_signal_handlers()
        
        # Start the application
        await app.start()
        
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error(f"Application error: {e}")
        return 1
    finally:
        await app.stop()
    
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))