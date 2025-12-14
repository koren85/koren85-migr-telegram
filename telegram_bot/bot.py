import asyncio
from typing import Dict, List, Any
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
from loguru import logger
from config.settings import Settings


class TelegramBot:
    """Telegram bot for database monitoring notifications"""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.app = None
        self.bot = None
        self.monitors = {}  # Will be set by main app
        self.authorized_chat_ids = set(settings.telegram.chat_ids)
    
    def set_monitors(self, monitors: Dict):
        """Set database monitors for manual queries"""
        self.monitors = monitors
    
    async def start_bot(self):
        """Start the Telegram bot"""
        try:
            # Create application
            self.app = Application.builder().token(self.settings.telegram.bot_token).build()
            self.bot = self.app.bot
            
            # Add handlers
            self.app.add_handler(CommandHandler("start", self._start_command))
            self.app.add_handler(CommandHandler("help", self._help_command))
            self.app.add_handler(CommandHandler("status", self._status_command))
            self.app.add_handler(CommandHandler("get", self._get_command))
            self.app.add_handler(CommandHandler("list", self._list_command))
            self.app.add_handler(CommandHandler("add_group", self._add_group_command))
            self.app.add_handler(CommandHandler("groups", self._groups_command))
            self.app.add_handler(CommandHandler("test_rules", self._test_rules_command))
            
            # Start bot
            await self.app.initialize()
            await self.app.start()
            await self.app.updater.start_polling()
            
            logger.info("Telegram bot started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start Telegram bot: {e}")
            raise
    
    async def stop_bot(self):
        """Stop the Telegram bot"""
        if self.app and self.app.updater:
            await self.app.updater.stop()
            await self.app.stop()
            await self.app.shutdown()
            logger.info("Telegram bot stopped")
    
    def _is_authorized(self, chat_id: int) -> bool:
        """Check if chat ID is authorized"""
        return chat_id in self.authorized_chat_ids
    
    def _is_admin(self, user_id: int) -> bool:
        """Check if user is admin (first chat_id in config is considered admin)"""
        if not self.authorized_chat_ids:
            return False
        admin_id = next(iter(self.authorized_chat_ids))
        return user_id == admin_id
    
    async def _start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        chat_id = update.effective_chat.id
        
        if not self._is_authorized(chat_id):
            await update.message.reply_text("❌ Вы не авторизованы для использования этого бота.")
            return
        
        welcome_text = """🤖 Бот мониторинга баз данных

Доступные команды:
/help - Показать помощь
/status - Статус мониторинга
/list - Список всех баз данных и таблиц
/get <db_name> <monitor_name> - Получить текущее значение

Бот автоматически отправляет уведомления при изменении отслеживаемых значений."""
        
        await update.message.reply_text(welcome_text)
    
    async def _help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        if not self._is_authorized(update.effective_chat.id):
            return
        
        help_text = """
📖 Помощь по командам:

🔹 /start - Запуск бота и приветствие
🔹 /help - Показать эту справку
🔹 /status - Статус всех мониторов БД
🔹 /list - Список всех баз данных и отслеживаемых таблиц
🔹 /get <db_name> <monitor_name> - Получить текущее значение

👑 Команды администратора:
🔹 /add_group - Добавить текущий чат в список уведомлений
🔹 /groups - Показать все авторизованные чаты
🔹 /test_rules - Принудительно протестировать все активные правила

Примеры:
/get voron_migr_db bdm_file_task_status
/get test_db health_monitor

Бот автоматически отправляет уведомления при изменении значений в отслеживаемых таблицах.
        """
        
        await update.message.reply_text(help_text)
    
    async def _status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command"""
        if not self._is_authorized(update.effective_chat.id):
            return
        
        if not self.monitors:
            await update.message.reply_text("❌ Мониторы не настроены")
            return
        
        status_text = "📊 Статус мониторинга:\n\n"
        
        for db_name, monitor in self.monitors.items():
            status_text += f"🔹 {db_name}: "
            status_text += "✅ Активен\n" if monitor.running else "❌ Остановлен\n"
            
            # Show current values
            values = monitor.get_all_current_values()
            for table_column, value in values.items():
                status_text += f"   • {table_column}: {value}\n"
            status_text += "\n"
        
        await update.message.reply_text(status_text)
    
    async def _list_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /list command"""
        if not self._is_authorized(update.effective_chat.id):
            return
        
        if not self.monitors:
            await update.message.reply_text("❌ Мониторы не настроены")
            return
        
        list_text = "📋 Список баз данных и таблиц:\n\n"
        
        for db_name, monitor in self.monitors.items():
            list_text += f"🔹 {db_name}\n"
            
            for state in monitor.monitor_states.values():
                list_text += f"   • {state.monitor_name} (проверка каждые {state.check_interval}с)\n"
            list_text += "\n"
        
        await update.message.reply_text(list_text)
    
    async def _get_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /get command"""
        if not self._is_authorized(update.effective_chat.id):
            return
        
        if len(context.args) != 2:
            await update.message.reply_text(
                "❌ Неверный формат команды.\n"
                "Используйте: /get <db_name> <monitor_name>\n"
                "Пример: /get voron_migr_db bdm_file_task_status"
            )
            return
        
        db_name = context.args[0]
        monitor_name = context.args[1]
        
        if db_name not in self.monitors:
            await update.message.reply_text(f"❌ База данных '{db_name}' не найдена")
            return
        
        try:
            monitor = self.monitors[db_name]
            
            value = await monitor.get_current_value(monitor_name)
            
            if value is not None:
                await update.message.reply_text(
                    f"📊 {db_name}.{monitor_name}\n"
                    f"Текущее значение: {value}"
                )
            else:
                await update.message.reply_text(f"❌ Не удалось получить значение для {monitor_name}")
        
        except Exception as e:
            logger.error(f"Error getting value for {monitor_name}: {e}")
            await update.message.reply_text(f"❌ Ошибка получения значения: {str(e)}")
    
    async def _add_group_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /add_group command - only for admins"""
        if not self._is_admin(update.effective_user.id):
            await update.message.reply_text("❌ Только администратор может добавлять группы")
            return
        
        chat_id = update.effective_chat.id
        chat_title = update.effective_chat.title or f"Chat {chat_id}"
        
        if chat_id in self.authorized_chat_ids:
            await update.message.reply_text(f"✅ Группа '{chat_title}' уже добавлена")
        else:
            self.authorized_chat_ids.add(chat_id)
            await update.message.reply_text(f"✅ Группа '{chat_title}' добавлена в список уведомлений")
            logger.info(f"Added group {chat_id} ({chat_title}) to authorized chats")
    
    async def _groups_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /groups command - show all authorized groups"""
        if not self._is_admin(update.effective_user.id):
            await update.message.reply_text("❌ Только администратор может просматривать список групп")
            return
        
        if not self.authorized_chat_ids:
            await update.message.reply_text("📋 Нет авторизованных чатов")
            return
        
        groups_text = "📋 Авторизованные чаты:\n\n"
        for chat_id in self.authorized_chat_ids:
            try:
                chat = await self.bot.get_chat(chat_id)
                chat_name = chat.title or chat.first_name or f"Chat {chat_id}"
                chat_type = "👥 Группа" if chat.type in ["group", "supergroup"] else "👤 Личный"
                groups_text += f"{chat_type} {chat_name} (ID: {chat_id})\n"
            except Exception:
                groups_text += f"❓ Неизвестный чат (ID: {chat_id})\n"
        
        await update.message.reply_text(groups_text)
    
    async def _test_rules_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /test_rules command - manually trigger rule evaluation"""
        if not self._is_admin(update.effective_user.id):
            await update.message.reply_text("❌ Только администратор может тестировать правила")
            return
        
        try:
            # Get notification engine from the app instance
            if hasattr(self, '_app_instance') and self._app_instance and hasattr(self._app_instance, 'notification_engine'):
                notification_engine = self._app_instance.notification_engine
                
                # Get all active rules
                active_rules = notification_engine.database.get_rules(active_only=True)
                if not active_rules:
                    await update.message.reply_text("❌ Нет активных правил для тестирования")
                    return
                
                await update.message.reply_text(f"🔄 Тестирую {len(active_rules)} активных правил...")
                
                # Test each rule with current monitor states
                tested_count = 0
                triggered_count = 0
                
                for rule in active_rules:
                    monitor_key = f"{rule.db_name}.{rule.monitor_name}"
                    
                    # Get current state
                    if monitor_key in notification_engine.monitor_states:
                        state = notification_engine.monitor_states[monitor_key]
                        current_value = state.current_value
                        previous_value = state.previous_value
                        
                        # Force evaluation of the rule
                        try:
                            would_trigger = await notification_engine._evaluate_condition(rule, state, previous_value, current_value)
                            tested_count += 1
                            
                            if would_trigger:
                                # Force send notification by temporarily disabling cooldown
                                original_cooldowns = state.notification_cooldowns.copy()
                                state.notification_cooldowns.clear()
                                
                                # Process the change
                                await notification_engine.process_value_change(
                                    rule.db_name, rule.monitor_name, previous_value, current_value
                                )
                                triggered_count += 1
                                
                                # Restore cooldowns if needed
                                state.notification_cooldowns = original_cooldowns
                                
                        except Exception as e:
                            logger.error(f"Error testing rule {rule.name}: {e}")
                
                result_message = f"✅ Тестирование завершено:\n"
                result_message += f"📊 Протестировано правил: {tested_count}\n"
                result_message += f"🔔 Сработало правил: {triggered_count}"
                
                await update.message.reply_text(result_message)
                
            else:
                await update.message.reply_text("❌ Система уведомлений недоступна")
                
        except Exception as e:
            logger.error(f"Error in test_rules command: {e}")
            await update.message.reply_text(f"❌ Ошибка тестирования правил: {str(e)}")
    
    async def send_change_notification(self, db_name: str, table_column: str, old_value: Any, new_value: Any):
        """Send notification about value change"""
        import datetime
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        message = f"""🔔 Изменение в базе данных

📊 База: {db_name}
📋 Монитор: {table_column}
🔄 Изменение: {old_value} → {new_value}
⏰ Время: {current_time}"""
        
        # Send to all authorized chats
        for chat_id in self.authorized_chat_ids:
            try:
                await self.bot.send_message(
                    chat_id=chat_id,
                    text=message
                )
            except Exception as e:
                logger.error(f"Failed to send notification to {chat_id}: {e}")