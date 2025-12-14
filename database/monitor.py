import asyncio
import time
from typing import Dict, Any, Optional, Callable
from loguru import logger
from dataclasses import dataclass
from config.settings import DatabaseConfig, TableConfig
from .connection import DatabaseConnection


@dataclass
class MonitorState:
    """Stores monitoring state for a query"""
    database_name: str
    monitor_name: str
    sql_query: str
    last_value: Any = None
    last_check: float = 0
    check_interval: int = 60


class DatabaseMonitor:
    """Monitors database tables for value changes"""
    
    def __init__(self, db_config: DatabaseConfig, change_callback: Callable[[str, str, Any, Any], None]):
        self.db_config = db_config
        self.connection = DatabaseConnection(db_config)
        self.change_callback = change_callback
        self.monitor_states: Dict[str, MonitorState] = {}
        self.running = False
        # Database-level connection tracking
        self.db_consecutive_failures = 0
        self.db_last_failure_time = 0
        self.db_connection_disabled = False
        
        # Initialize monitor states
        for table_config in db_config.tables:
            # Support both new SQL query format and legacy table.column format
            if hasattr(table_config, 'sql_query') and table_config.sql_query:
                monitor_name = table_config.name
                sql_query = table_config.sql_query
            else:
                # Legacy format
                monitor_name = f"{table_config.table}.{table_config.column}"
                sql_query = f"SELECT {table_config.column} FROM {table_config.table} LIMIT 1"
            
            self.monitor_states[monitor_name] = MonitorState(
                database_name=db_config.name,
                monitor_name=monitor_name,
                sql_query=sql_query,
                check_interval=table_config.check_interval
            )
    
    async def start_monitoring(self):
        """Start monitoring all configured tables"""
        self.running = True
        logger.info(f"Starting monitoring for database: {self.db_config.name}")
        
        # Initialize current values
        await self._initialize_current_values()
        
        # Start monitoring loop
        while self.running:
            try:
                await self._check_all_tables()
                await asyncio.sleep(1)  # Check every second for due tables
            except Exception as e:
                logger.error(f"Error in monitoring loop for {self.db_config.name}: {e}")
                await asyncio.sleep(5)  # Wait before retrying
    
    def stop_monitoring(self):
        """Stop monitoring"""
        self.running = False
        self.connection.disconnect()
        logger.info(f"Stopped monitoring for database: {self.db_config.name}")
    
    async def _initialize_current_values(self):
        """Get initial values for all monitored tables"""
        successful_inits = 0
        total_monitors = len(self.monitor_states)
        
        for state in self.monitor_states.values():
            try:
                current_value = await self._get_table_value_async(state)
                if current_value is not None:
                    state.last_value = current_value
                    state.last_check = time.time()
                    successful_inits += 1
                    logger.info(f"Initialized {state.database_name}.{state.monitor_name} = {current_value}")
                else:
                    logger.warning(f"No data returned for {state.database_name}.{state.monitor_name}")
            except Exception as e:
                logger.error(f"Failed to initialize value for {state.monitor_name}: {e}")
        
        logger.info(f"Initialized {successful_inits}/{total_monitors} monitors for database {self.db_config.name}")
    
    async def _check_all_tables(self):
        """Check all tables that are due for checking"""
        current_time = time.time()
        
        for state in self.monitor_states.values():
            if current_time - state.last_check >= state.check_interval:
                await self._check_table(state)
    
    async def _check_table(self, state: MonitorState):
        """Check a specific table for changes"""
        try:
            current_value = await self._get_table_value_async(state)
            
            if current_value is not None:
                # Check if value has changed
                if state.last_value is not None and current_value != state.last_value:
                    logger.info(f"Value changed in {state.database_name}.{state.monitor_name}: {state.last_value} -> {current_value}")
                    
                    # Call change callback
                    await asyncio.create_task(
                        self._async_callback(state.database_name, state.monitor_name, state.last_value, current_value)
                    )
                
                state.last_value = current_value
            
            state.last_check = time.time()
            
        except Exception as e:
            logger.error(f"Error checking {state.monitor_name}: {e}")
    
    async def _get_table_value_async(self, state: MonitorState) -> Optional[Any]:
        """Get value using SQL query asynchronously with intelligent reconnection logic"""
        current_time = time.time()
        
        # Skip if database connection is temporarily disabled due to repeated failures
        if self.db_connection_disabled:
            # Re-enable after exponential backoff: 1min, 5min, 15min, 30min, 60min max
            backoff_delay = min(60 * (2 ** min(self.db_consecutive_failures - 5, 4)), 3600)
            if current_time - self.db_last_failure_time < backoff_delay:
                return None
            else:
                self.db_connection_disabled = False
                logger.info(f"Re-enabling connection attempts for {self.db_config.name} after {backoff_delay}s backoff")
        
        loop = asyncio.get_event_loop()
        
        # Try to execute query
        result = await loop.run_in_executor(
            None,
            self.connection.execute_query,
            state.sql_query
        )
        
        if result is not None:
            # Reset failure tracking on successful query
            if self.db_consecutive_failures > 0:
                logger.info(f"Connection restored for {self.db_config.name}")
                self.db_consecutive_failures = 0
                self.db_connection_disabled = False
            return result
        
        # Handle connection failure
        self.db_consecutive_failures += 1
        self.db_last_failure_time = current_time
        
        # Disable connection attempts after 5 consecutive failures
        if self.db_consecutive_failures >= 5:
            self.db_connection_disabled = True
            logger.warning(f"Disabling connection attempts for {self.db_config.name} after {self.db_consecutive_failures} failures (will retry with backoff)")
        
        # Try to reconnect only if not yet disabled
        if not self.db_connection_disabled and not self.connection.is_connected():
            logger.debug(f"Attempting reconnection to {self.db_config.name} (failure #{self.db_consecutive_failures})")
            try:
                if await loop.run_in_executor(None, self.connection.connect):
                    logger.info(f"Reconnected to {self.db_config.name}")
                    # Retry query after reconnection
                    result = await loop.run_in_executor(
                        None,
                        self.connection.execute_query,
                        state.sql_query
                    )
                    if result is not None:
                        self.db_consecutive_failures = 0
                        self.db_connection_disabled = False
            except Exception as e:
                logger.debug(f"Reconnection failed for {self.db_config.name}: {e}")
        
        return result
    
    async def _async_callback(self, db_name: str, table_column: str, old_value: Any, new_value: Any):
        """Wrapper to make callback async"""
        if asyncio.iscoroutinefunction(self.change_callback):
            await self.change_callback(db_name, table_column, old_value, new_value)
        else:
            self.change_callback(db_name, table_column, old_value, new_value)
    
    async def get_current_value(self, monitor_name: str) -> Optional[Any]:
        """Get current value for manual requests"""
        if monitor_name in self.monitor_states:
            state = self.monitor_states[monitor_name]
            return await self._get_table_value_async(state)
        return None
    
    def get_all_current_values(self) -> Dict[str, Any]:
        """Get all current values"""
        return {
            state.monitor_name: state.last_value
            for state in self.monitor_states.values()
        }