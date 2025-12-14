import jpype
from typing import Optional, Any, Dict, Set
from loguru import logger
from config.settings import DatabaseConfig


class JVMManager:
    """Global JVM manager to ensure JVM is started only once"""
    _instance = None
    _jvm_started = False
    _jar_paths: Set[str] = set()
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def start_jvm(self, jar_path: str) -> None:
        """Start JVM with all required jar paths"""
        self._jar_paths.add(jar_path)
        
        if not self._jvm_started and not jpype.isJVMStarted():
            try:
                jpype.startJVM(classpath=list(self._jar_paths))
                self._jvm_started = True
                logger.info(f"JVM started with jars: {list(self._jar_paths)}")
            except Exception as e:
                logger.error(f"Failed to start JVM: {e}")
                raise
        elif not self._jvm_started and jpype.isJVMStarted():
            self._jvm_started = True
            logger.info("JVM was already running")


class DatabaseConnection:
    """Manages JDBC database connections"""
    
    def __init__(self, db_config: DatabaseConfig):
        self.config = db_config
        self.connection = None
        self._jvm_manager = JVMManager()
    
    def _start_jvm(self) -> None:
        """Start JVM if not already started"""
        try:
            self._jvm_manager.start_jvm(self.config.jar_path)
        except Exception as e:
            logger.error(f"Failed to start JVM for {self.config.name}: {e}")
            raise
    
    def connect(self) -> bool:
        """Establish database connection"""
        try:
            self._start_jvm()
            
            # Import JDBC classes
            DriverManager = jpype.JClass("java.sql.DriverManager")
            
            # Register driver
            jpype.JClass(self.config.driver)
            
            # Create connection
            self.connection = DriverManager.getConnection(
                self.config.url,
                self.config.username,
                self.config.password
            )
            
            logger.info(f"Connected to database: {self.config.name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to {self.config.name}: {e}")
            return False
    
    def disconnect(self) -> None:
        """Close database connection"""
        if self.connection:
            try:
                self.connection.close()
                logger.info(f"Disconnected from database: {self.config.name}")
            except Exception as e:
                logger.error(f"Error disconnecting from {self.config.name}: {e}")
            finally:
                self.connection = None
    
    def execute_query(self, sql: str) -> Optional[Any]:
        """Execute SQL query and return result"""
        if not self.connection:
            if not self.connect():
                return None
        
        try:
            statement = self.connection.createStatement()
            result_set = statement.executeQuery(sql)
            
            # Get first result if available
            if result_set.next():
                raw_value = result_set.getObject(1)
                # Convert to string if it's a Java object
                if raw_value is not None:
                    str_value = str(raw_value)
                    logger.debug(f"Query result: raw={type(raw_value)} '{raw_value}' -> str='{str_value}'")
                    return str_value
                else:
                    logger.debug(f"Query result: NULL")
                    return None
            else:
                logger.debug(f"Query returned no rows")
                return None
            
        except Exception as e:
            logger.error(f"Query execution failed on {self.config.name}: {e}")
            return None
        finally:
            if 'statement' in locals():
                statement.close()
    
    def get_table_value(self, table: str, column: str, where_clause: str = "") -> Optional[Any]:
        """Get specific value from table"""
        sql = f"SELECT {column} FROM {table}"
        if where_clause:
            sql += f" WHERE {where_clause}"
        sql += " LIMIT 1"
        
        return self.execute_query(sql)
    
    def is_connected(self) -> bool:
        """Check if connection is active"""
        if not self.connection:
            return False
        
        try:
            return not self.connection.isClosed()
        except Exception:
            return False