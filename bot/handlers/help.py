"""
Help command handler and inline query handler.
"""
from telegram import Update, InlineQueryResultArticle, InputTextMessageContent
from uuid import uuid4
from telegram.ext import ContextTypes
import logging
from handlers.base import BaseHandler

logger = logging.getLogger(__name__)


class HelpHandler(BaseHandler):
    """Handler for /help command and inline queries."""
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command."""
        self.log_analytics(update, "help_command")

        help_text = (
            "🤖 *Добро пожаловать в TLDR Bot!* 🤖\n\n"
            "Я помогаю пересказывать разговоры и выделять главное. Вот что я умею:\n\n"
            "*Команды:*\n"
            "• `/tldr [number]` — Пересказать последние [number] сообщений (по умолчанию: 50)\n"
            "• `/dl [URL]` — Скачать TikTok, Reels, Shorts и т. п. (в разработке: иногда может не работать)\n"
            "• `/switch_model <provider>` — Сменить модель ИИ\n"
            "• `/set_api_key <provider> <key>` — Установить свой API-ключ провайдера (BYOK)\n"
            "    Допустимые провайдеры: `openai`, `groq`, `deepseek`\n"
            "• `/clear_api_key <provider>` — Удалить свой API-ключ провайдера\n"
            "    Допустимые провайдеры: `openai`, `groq`, `deepseek`\n"
            "• `/list_providers` — Показать все допустимые имена провайдеров\n"
            "• `/set_receipt_model <model>` — Выбрать модель OpenAI для разбора чека\n"
            "\n*Доступные модели:*\n"
            "• `openai-mini` — GPT-4o mini\n"
            "• `openai-4o` — GPT-4o\n"
            "• `openai-4.1` — GPT-4.1 (turbo)\n"
            "• `groq` — Llama 3 (8bn) на groq\n"
            "• `deepseek` — DeepSeek V3\n"
            "\n*Возможности:*\n"
            "• Отвечать на пересказы вопросами для более глубоких выводов\n"
            "• Смотреть анализ настроения в пересказах\n"
            "• Получать ключевые события из разговоров\n"
            "\n*Текущая модель:* " + str(self.ai_service.get_current_model())
        )

        await self.safe_reply(update, context, help_text, parse_mode="Markdown")

    async def inline_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle inline queries."""
        if not hasattr(update, "inline_query") or update.inline_query is None:
            logger.warning("В обновлении не найден inline_query для обработчика inline_query.")
            return

        query = getattr(update.inline_query, "query", "")
        results = [
            InlineQueryResultArticle(
                id=str(uuid4()),
                title="Пересказать разговор",
                input_message_content=InputTextMessageContent(f"/tldr"),
                description="Сделать пересказ разговора в групповом чате",
            ),
            InlineQueryResultArticle(
                id=str(uuid4()),
                title="Старт",
                input_message_content=InputTextMessageContent(f"/start"),
                description="Запустить бота",
            ),
            InlineQueryResultArticle(
                id=str(uuid4()),
                title="Помощь",
                input_message_content=InputTextMessageContent(f"/help"),
                description="Показать справку",
            ),
        ]

        if hasattr(update.inline_query, "answer") and callable(update.inline_query.answer):
            await update.inline_query.answer(results)
        else:
            logger.warning("inline_query.answer недоступен в update.inline_query.")

