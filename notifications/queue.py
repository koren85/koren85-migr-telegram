"""
Notification Queue - manages telegram notifications with rate limiting and retry
"""
import asyncio
from typing import Optional, Callable, Dict, Any
from dataclasses import dataclass
from datetime import datetime
from loguru import logger


@dataclass
class NotificationTask:
    """Represents a notification to be sent"""
    chat_id: int
    message: str
    priority: str = 'medium'  # low, medium, high, critical
    retry_count: int = 0
    created_at: datetime = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()


class NotificationQueue:
    """
    Manages notification queue with:
    - Rate limiting (respects Telegram API limits)
    - Retry with exponential backoff
    - Priority handling (critical messages first)
    """

    def __init__(self, send_function: Callable, max_rate: int = 20):
        """
        Args:
            send_function: Async function to send message (chat_id, message) -> None
            max_rate: Maximum messages per second (default: 20 to stay under 30/sec limit)
        """
        self.send_function = send_function
        self.max_rate = max_rate
        self.min_interval = 1.0 / max_rate  # Minimum time between messages

        # Separate queues for different priorities
        self.queues: Dict[str, asyncio.Queue] = {
            'critical': asyncio.Queue(),
            'high': asyncio.Queue(),
            'medium': asyncio.Queue(),
            'low': asyncio.Queue()
        }

        self.running = False
        self.worker_task: Optional[asyncio.Task] = None
        self.last_send_time = 0

        # Statistics
        self.stats = {
            'sent': 0,
            'failed': 0,
            'retried': 0,
            'queued': 0
        }

    async def start(self):
        """Start queue worker"""
        if self.running:
            logger.warning("Notification queue already running")
            return

        self.running = True
        self.worker_task = asyncio.create_task(self._worker())
        logger.info(f"Notification queue started (rate limit: {self.max_rate} msg/sec)")

    async def stop(self):
        """Stop queue worker"""
        self.running = False
        if self.worker_task:
            self.worker_task.cancel()
            try:
                await self.worker_task
            except asyncio.CancelledError:
                pass
        logger.info("Notification queue stopped")

    async def enqueue(self, chat_id: int, message: str, priority: str = 'medium'):
        """Add notification to queue"""
        if priority not in self.queues:
            logger.warning(f"Invalid priority '{priority}', using 'medium'")
            priority = 'medium'

        task = NotificationTask(
            chat_id=chat_id,
            message=message,
            priority=priority
        )

        await self.queues[priority].put(task)
        self.stats['queued'] += 1
        logger.debug(f"Queued notification for chat {chat_id} (priority: {priority}, queue size: {self.queues[priority].qsize()})")

    async def _worker(self):
        """Worker that processes queue with rate limiting"""
        logger.info("Notification queue worker started")

        while self.running:
            try:
                # Get next task (priority order: critical > high > medium > low)
                task = await self._get_next_task()

                if task:
                    # Rate limiting: ensure minimum interval between sends
                    now = asyncio.get_event_loop().time()
                    time_since_last = now - self.last_send_time

                    if time_since_last < self.min_interval:
                        await asyncio.sleep(self.min_interval - time_since_last)

                    # Try to send
                    success = await self._send_with_retry(task)

                    if success:
                        self.stats['sent'] += 1
                        self.last_send_time = asyncio.get_event_loop().time()
                    else:
                        self.stats['failed'] += 1
                        logger.error(f"Failed to send notification after retries: {task.chat_id}")
                else:
                    # No tasks available, sleep briefly
                    await asyncio.sleep(0.1)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in notification queue worker: {e}")
                await asyncio.sleep(1)

        logger.info("Notification queue worker stopped")

    async def _get_next_task(self) -> Optional[NotificationTask]:
        """Get next task from queues (priority order)"""
        # Try each queue in priority order
        for priority in ['critical', 'high', 'medium', 'low']:
            queue = self.queues[priority]
            if not queue.empty():
                try:
                    return queue.get_nowait()
                except asyncio.QueueEmpty:
                    continue
        return None

    async def _send_with_retry(self, task: NotificationTask, max_retries: int = 3) -> bool:
        """Send notification with exponential backoff retry"""
        for attempt in range(max_retries + 1):
            try:
                await self.send_function(task.chat_id, task.message)

                if task.retry_count > 0:
                    logger.info(f"Successfully sent after {task.retry_count} retries: chat {task.chat_id}")

                return True

            except Exception as e:
                task.retry_count += 1
                self.stats['retried'] += 1

                if attempt < max_retries:
                    # Exponential backoff: 1s, 2s, 4s
                    backoff = 2 ** attempt
                    logger.warning(f"Failed to send to {task.chat_id} (attempt {attempt + 1}/{max_retries + 1}): {e}. Retrying in {backoff}s...")
                    await asyncio.sleep(backoff)
                else:
                    logger.error(f"Failed to send to {task.chat_id} after {max_retries + 1} attempts: {e}")
                    return False

        return False

    def get_stats(self) -> Dict[str, Any]:
        """Get queue statistics"""
        total_queued = sum(q.qsize() for q in self.queues.values())

        return {
            'running': self.running,
            'sent': self.stats['sent'],
            'failed': self.stats['failed'],
            'retried': self.stats['retried'],
            'total_queued': self.stats['queued'],
            'current_queued': total_queued,
            'queue_sizes': {
                priority: queue.qsize()
                for priority, queue in self.queues.items()
            }
        }
