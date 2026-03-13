"""
Model management handlers: switch_model, set_api_key, clear_api_key, list_providers, set_receipt_model.
"""
from telegram import Update
from telegram.ext import ContextTypes
import logging
import os
from services.ai import StrategyRegistry
from services.ai.openai_strategy import OpenAIStrategy
from services.ai.groq_strategy import GroqAIStrategy
from services.ai.deepseek_strategy import DeepSeekStrategy
from config.settings import OpenAIConfig, GroqAIConfig, DeepSeekAIConfig
from utils.user.user_api_keys import set_user_api_key, clear_user_api_key, get_user_api_key
from handlers.base import BaseHandler

logger = logging.getLogger(__name__)

# Allowed OpenAI models for receipt parsing
ALLOWED_RECEIPT_MODELS = [
    OpenAIConfig.MINI_MODEL,
    OpenAIConfig.O4_MODEL,
    OpenAIConfig.FOUR_ONE_MODEL,
]


class ModelHandler(BaseHandler):
    """Handler for model switching and API key management."""
    
    def __init__(self, ai_service=None):
        super().__init__(ai_service)
        self.user_selected_model = {}  # {user_id: provider_name}
        self.user_receipt_model = {}  # {user_id: openai_model_name}
    
    def _get_user_strategy(self, user_id: int, provider: str):
        """Return a strategy for the provider, using user key if available."""
        provider = provider.lower()
        return self._resolve_strategy(
            user_id,
            provider,
            {
                "openai-mini": (OpenAIConfig, OpenAIStrategy, OpenAIConfig.MINI_MODEL),
                "openai-4o": (OpenAIConfig, OpenAIStrategy, OpenAIConfig.O4_MODEL),
                "openai-4.1": (OpenAIConfig, OpenAIStrategy, OpenAIConfig.FOUR_ONE_MODEL),
                "groq": (GroqAIConfig, GroqAIStrategy),
                "deepseek": (DeepSeekAIConfig, DeepSeekStrategy),
            },
        )

    def _resolve_strategy(self, user_id: int, provider: str, config_map: dict):
        """Helper function to resolve API key and model for a given provider."""
        if provider not in config_map:
            raise ValueError(f"Неизвестный провайдер: {provider}")

        mapping = config_map[provider]
        if len(mapping) == 3:
            config_class, strategy_class, model = mapping
        else:
            config_class, strategy_class = mapping
            model = getattr(config_class, 'MODEL', '')

        # Use a shared key for all OpenAI models
        key_provider = 'openai' if provider.startswith('openai') else provider
        user_key = get_user_api_key(user_id, key_provider)
        key = user_key if user_key is not None else (config_class.API_KEY if getattr(config_class, 'API_KEY', None) is not None else "")

        return strategy_class(key, model)
    
    async def switch_model(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /switch_model command."""
        self.log_analytics(update, "switch_model_command")

        if not context.args or len(context.args) < 1 or not isinstance(context.args[0], str):
            await self.safe_reply(update, context, "Пожалуйста, укажите имя модели.")
            return

        new_model = context.args[0].lower()
        available_models = StrategyRegistry.available_strategies()
        
        if new_model not in available_models:
            await self.safe_reply(update, context, f"Некорректное имя модели. Доступные модели: {', '.join(available_models)}")
            return

        user = update.effective_user
        # Save user model selection
        if user is not None:
            self.user_selected_model[user.id] = new_model

        try:
            # Use user's key if available
            strategy = self._get_user_strategy(user.id if user is not None else 0, new_model)
            self.ai_service.set_strategy(strategy)
            await self.safe_reply(update, context, f"Модель переключена на {new_model}")

        except Exception as e:
            logger.error(f"Ошибка переключения модели: {str(e)}")
            await self.safe_reply(update, context, f"Не удалось переключить модель: {str(e)}")

    async def set_api_key(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /set_api_key command."""
        user = update.effective_user
        if user is None or update.message is None:
            return
        
        args = context.args
        if not args or len(args) != 2:
            await update.message.reply_text("Использование: /set_api_key <provider> <key>")
            return
        
        provider, key = args
        provider = provider.lower()
        available_models = StrategyRegistry.available_strategies()
        
        if provider not in available_models:
            await update.message.reply_text(
                f"❗ Некорректный провайдер '{provider}'.\n"
                f"Пожалуйста, используйте один из: {', '.join(f'`{m}`' for m in available_models)}\n"
                "Можно также использовать /list_providers, чтобы увидеть все варианты."
            )
            return
        
        set_user_api_key(user.id, provider, key)
        await update.message.reply_text(f"API-ключ для {provider} успешно установлен! Будущие запросы будут использовать ваш ключ.")

    async def clear_api_key(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /clear_api_key command."""
        user = update.effective_user
        if user is None or update.message is None:
            return
        
        args = context.args
        if not args or len(args) != 1:
            await update.message.reply_text("Использование: /clear_api_key <provider>")
            return
        
        provider = args[0].lower()
        available_models = StrategyRegistry.available_strategies()
        
        if provider not in available_models:
            await update.message.reply_text(
                f"❗ Некорректный провайдер '{provider}'.\n"
                f"Пожалуйста, используйте один из: {', '.join(f'`{m}`' for m in available_models)}\n"
                "Можно также использовать /list_providers, чтобы увидеть все варианты."
            )
            return
        
        clear_user_api_key(user.id, provider)
        await update.message.reply_text(f"API-ключ для {provider} очищен. Бот будет использовать ключ по умолчанию.")

    async def list_providers(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /list_providers command."""
        available_models = StrategyRegistry.available_strategies()
        msg = (
            "🗝️ *Допустимые провайдеры для BYOK и переключения моделей:*\n\n"
            + "\n".join(f"• `{m}`" for m in available_models)
            + "\n\nИспользуйте эти имена для `/set_api_key`, `/clear_api_key` и `/switch_model`."
        )
        await self.safe_reply(update, context, msg, parse_mode="Markdown")

    async def set_receipt_model(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /set_receipt_model command."""
        user = update.effective_user
        if user is None or update.message is None:
            return

        if not context.args or len(context.args) != 1:
            await update.message.reply_text(
                f"Использование: /set_receipt_model <model>\nДоступно: {', '.join(ALLOWED_RECEIPT_MODELS)}"
            )
            return

        model_name = context.args[0]
        if model_name not in ALLOWED_RECEIPT_MODELS:
            await update.message.reply_text(
                f"Некорректное имя модели. Выберите из: {', '.join(ALLOWED_RECEIPT_MODELS)}"
            )
            return

        self.user_receipt_model[user.id] = model_name
        await update.message.reply_text(f"Модель для разбора чека установлена на {model_name}.")
    
    def get_receipt_model(self, user_id: int) -> str:
        """Get the receipt model for a user, or default."""
        return self.user_receipt_model.get(user_id, os.getenv('OPENAI_MODEL', OpenAIConfig.MINI_MODEL))

