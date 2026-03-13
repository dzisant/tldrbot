"""
Bill splitting conversation handlers for /splitbill command.
"""
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
import logging
import os
from io import BytesIO
from config.settings import OpenAIConfig
from services.bill_splitter import (
    extract_receipt_data_from_image,
    parse_payment_context_with_llm,
    calculate_split,
    format_split_results,
)
from handlers.base import BaseHandler, RECEIPT_IMAGE, CONFIRMATION

logger = logging.getLogger(__name__)


class BillSplitHandler(BaseHandler):
    """Handler for bill splitting conversation flow."""
    
    def __init__(self, ai_service=None, model_handler=None):
        super().__init__(ai_service)
        self.model_handler = model_handler  # Reference to ModelHandler for receipt model
    
    async def split_bill_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Entry point for bill splitting: ask user to send receipt photo with caption."""
        self.log_analytics(update, "split_bill_start")

        user = update.effective_user
        receipt_model = self.model_handler.get_receipt_model(user.id if user is not None else 0) if self.model_handler else os.getenv('OPENAI_MODEL', OpenAIConfig.MINI_MODEL)
        
        await self.safe_reply(
            update,
            context,
            "Чтобы разделить счёт, отправьте фото чека *с подписью*, кто за что платил.\n\n"
            "Пример подписи:\n"
            "Алиса: Бургер, Картошка фри\n"
            "Боб: Салат\n"
            "Общее: Напитки\n\n"
            "(Убедитесь, что названия в подписи примерно соответствуют чеку.)",
            parse_mode="Markdown"
        )
        await self.safe_reply(
            update,
            context,
            f"Для разбора чека используется модель OpenAI {receipt_model}."
        )
        return RECEIPT_IMAGE

    async def split_bill_photo_with_context(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle receipt photo with context caption."""
        message = getattr(update, "message", None)
        if not message or not getattr(message, "photo", None) or not getattr(message, "caption", None):
            await self.safe_reply(
                update,
                context,
                "Пожалуйста, отправьте *фото чека* с *подписью*, кто за что платил.",
                parse_mode="Markdown"
            )
            return RECEIPT_IMAGE

        photo_file = await message.photo[-1].get_file()
        image_stream = BytesIO()
        await photo_file.download_to_memory(image_stream)
        image_stream.seek(0)
        image_bytes = image_stream.read()
        user_context_text = message.caption

        user = update.effective_user
        receipt_model = self.model_handler.get_receipt_model(user.id if user is not None else 0) if self.model_handler else os.getenv('OPENAI_MODEL', OpenAIConfig.MINI_MODEL)
        
        await self.safe_reply(update, context, f"Обрабатываю чек и контекст с помощью {receipt_model}...")

        # Extract receipt data
        receipt_data = await extract_receipt_data_from_image(image_bytes, receipt_model)
        if not receipt_data:
            await self.safe_reply(
                update,
                context,
                "Извините, не удалось извлечь данные из этого чека. Попробуйте ещё раз с более чётким изображением."
            )
            return RECEIPT_IMAGE

        # Parse context and prepare confirmation
        parsing_result = parse_payment_context_with_llm(
            user_context_text,
            receipt_data.items,
            self.ai_service
        )

        # Handle parsing errors (returns error message string)
        if isinstance(parsing_result, str):
            await self.safe_reply(
                update,
                context,
                f"Не удалось разобрать контекст: {parsing_result}\nПопробуйте ещё раз с более понятной подписью."
            )
            return RECEIPT_IMAGE

        # Unpack parsing results
        assignments, shared_items, participants = parsing_result

        # Defensive: ensure context.user_data is a dict
        if not hasattr(context, "user_data") or context.user_data is None:
            context.user_data = {}

        # Store intermediate data for confirmation
        context.user_data['bill_split'] = {
            'receipt_data': receipt_data,
            'assignments': assignments,
            'shared_items': shared_items,
            'participants': participants,
        }

        # Build confirmation summary
        lines = ["Я разобрал ваш чек так:"]
        # Assigned items per person
        for person, items in assignments.items():
            item_names = ", ".join(item.name for item in items)
            lines.append(f"- {person}: {item_names}")
        # Shared items
        if shared_items:
            shared_names = ", ".join(item.name for item in shared_items)
            lines.append(f"- Общее: {shared_names}")
        # Participants
        if participants:
            parts = ", ".join(participants)
            lines.append(f"Участники: {parts}")
        lines.append("\nОтветьте 'confirm', чтобы подтвердить разделение, отправьте новое фото с подписью, чтобы повторить, или /cancel для отмены.")

        await self.safe_reply(update, context, "\n".join(lines))
        return CONFIRMATION

    async def split_bill_confirm(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Finalize bill split after user confirmation."""
        # Defensive: ensure context.user_data is a dict
        if not hasattr(context, "user_data") or context.user_data is None:
            context.user_data = {}

        data = context.user_data.get('bill_split') if isinstance(context.user_data, dict) else None

        if not data:
            await self.safe_reply(
                update,
                context,
                "Нет активной операции разделения счёта. Используйте /splitbill, чтобы начать."
            )
            return ConversationHandler.END

        receipt_data = data['receipt_data']
        assignments = data['assignments']
        shared_items = data['shared_items']
        participants = data['participants']

        # Perform calculation
        split_result = calculate_split(
            assignments,
            shared_items,
            participants,
            receipt_data.total_amount,
            receipt_data.service_charge,
            receipt_data.tax_amount
        )
        
        if isinstance(split_result, str):
            await self.safe_reply(update, context, f"Ошибка расчёта: {split_result}")
            if isinstance(context.user_data, dict):
                context.user_data.pop('bill_split', None)
            return ConversationHandler.END

        # Format and send final results
        final_message = format_split_results(
            split_result,
            receipt_data.total_amount,
            receipt_data.service_charge,
            receipt_data.tax_amount
        )
        await self.safe_reply(update, context, final_message, parse_mode="Markdown")
        
        # Clean up
        if isinstance(context.user_data, dict):
            context.user_data.pop('bill_split', None)
        return ConversationHandler.END

    async def split_bill_cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Cancel the bill-splitting flow."""
        # Optionally clean up any stored data
        if hasattr(context, "user_data") and isinstance(context.user_data, dict):
            context.user_data.pop('bill_split', None)
        await self.safe_reply(update, context, "Разделение счёта отменено.")
        return ConversationHandler.END

