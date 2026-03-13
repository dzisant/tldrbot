"""Summarize plugin for /tldr command."""
from html import escape
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from . import Plugin
from ..core.ai import AIService
from ..core.rate_limiter import RateLimiter
from ..storage.memory import MemoryStorage
import logging

logger = logging.getLogger(__name__)


class SummarizePlugin(Plugin):
    def __init__(self, ai_service: AIService, rate_limiter: RateLimiter, memory: MemoryStorage):
        self.ai = ai_service
        self.rate_limiter = rate_limiter
        self.memory = memory
    
    @property
    def name(self) -> str:
        return "summarize"
    
    @property
    def commands(self):
        return [("tldr", "Пересказать последние сообщения")]
    
    def register(self, app: Application) -> None:
        app.add_handler(CommandHandler("tldr", self.summarize))
    
    async def summarize(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.message or not update.effective_chat or not update.effective_user:
            return
        
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        
        if not self.rate_limiter.can_use(user_id):
            await update.message.reply_text(self.rate_limiter.get_limit_message())
            return
        
        num_messages = 50
        if context.args:
            try:
                num_messages = min(max(int(context.args[0]), 1), 400)
            except ValueError:
                pass
        
        messages = self.memory.get_recent_messages(chat_id, num_messages)
        if not messages:
            await update.message.reply_text(
                "🤷 У меня нет сообщений, чтобы сделать пересказ. "
                "Либо вы только что меня добавили, либо все неожиданно притихли. "
                "И то, и другое настораживает."
            )
            return
        
        progress_msg = await update.message.reply_text(
            "⏳ <i>Анализирую ваш чат... Надеюсь, это того стоит.</i>",
            parse_mode="HTML"
        )
        
        self.rate_limiter.record_use(user_id)
        remaining = self.rate_limiter.remaining(user_id)
        
        combined_text = "\n".join(messages)
        summary = self.ai.get_summary(combined_text, len(messages))
        
        final_text = (
            f"📝 <b>Сводка</b> (последние {len(messages)} сообщений)\n\n{escape(summary)}"
        )
        if remaining <= 3:
            final_text += (
                f"\n\n⚠️ <i>Сегодня осталось {remaining} использований. Не трать всё сразу.</i>"
            )
        
        try:
            await progress_msg.edit_text(
                final_text,
                parse_mode="HTML"
            )
        except Exception as e:
            logger.warning(f"Не удалось отредактировать сообщение: {e}")
            await update.message.reply_text(final_text, parse_mode="HTML")
        
        self.memory.set_summary_context(chat_id, progress_msg.message_id, messages)
        
        logger.info(
            "Ответ пересказа для пользователя %s в чате %s: %s",
            user_id,
            chat_id,
            summary
        )
        logger.info(f"Пересказ создан для пользователя {user_id} в чате {chat_id} ({len(messages)} сообщений)")

