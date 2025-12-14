# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python application that monitors database tables and sends notifications via Telegram bot. The application:

- Connects to multiple databases using JDBC drivers (via JPype1)
- Monitors specific table values for changes
- Sends notifications to Telegram when values change
- Responds to manual requests for current values
- Supports multiple database configurations

## Architecture

- `main.py` - Main application entry point and orchestration
- `database/` - Database connection and monitoring logic
  - `monitor.py` - Core monitoring functionality
  - `connection.py` - Database connection management
- `telegram/` - Telegram bot integration
  - `bot.py` - Bot commands and message handling
- `config/` - Configuration management
  - `settings.py` - Configuration loading and validation
- `config.yaml` - Main configuration file with database and Telegram settings

## Development Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run the application
python main.py

# Run with specific config
python main.py --config custom_config.yaml

# Run in development mode with debug logging
python main.py --debug
```

## Configuration

The application uses `config.yaml` for configuration:
- Database connections (multiple databases supported)
- Telegram bot token and chat IDs
- Monitoring intervals and table configurations
- JDBC driver paths

## Key Dependencies

- `JPype1` - Java/JDBC integration for database connections
- `python-telegram-bot` - Modern async Telegram bot framework
- `PyYAML` - Configuration file parsing
- `asyncio` - Async/await support for concurrent operations
- `schedule` - Task scheduling for periodic monitoring

## Database Monitoring

The application monitors specified tables and columns, comparing current values with previously stored values. When changes are detected, notifications are sent via Telegram. Manual requests can force immediate value retrieval.