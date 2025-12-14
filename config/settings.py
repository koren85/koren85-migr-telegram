from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
import yaml
from pathlib import Path


class TableConfig(BaseModel):
    name: str  # Display name for this monitoring task
    sql_query: str  # Custom SQL query to execute
    check_interval: int = 60
    
    # Legacy fields for backward compatibility
    table: Optional[str] = None
    column: Optional[str] = None


class DatabaseConfig(BaseModel):
    name: str
    driver: str
    url: str
    username: str
    password: str
    jar_path: str
    tables: List[TableConfig]


class TelegramConfig(BaseModel):
    bot_token: str
    chat_ids: List[int]


class LoggingConfig(BaseModel):
    level: str = "INFO"
    file: str = "logs/app.log"


class MonitoringConfig(BaseModel):
    startup_delay: int = 10
    max_retries: int = 3
    retry_delay: int = 5


class Settings(BaseModel):
    telegram: TelegramConfig
    databases: List[DatabaseConfig]
    logging: LoggingConfig = LoggingConfig()
    monitoring: MonitoringConfig = MonitoringConfig()

    @classmethod
    def load_from_file(cls, config_path: str = "config.yaml") -> "Settings":
        """Load settings from YAML file"""
        config_file = Path(config_path)
        if not config_file.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        with open(config_file, 'r', encoding='utf-8') as f:
            config_data = yaml.safe_load(f)
        
        return cls(**config_data)

    def get_database_by_name(self, name: str) -> Optional[DatabaseConfig]:
        """Get database configuration by name"""
        for db in self.databases:
            if db.name == name:
                return db
        return None