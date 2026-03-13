"""Help plugin."""
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from . import Plugin
import logging

logger = logging.getLogger(__name__)

HELP_TEXT = """🙄 *О, тебе нужна помощь? Шокирующе.* Вот что я умею:

*Команды:*
• `/tldr [n]` — Пересказать последние n сообщений (по умолчанию: 50, максимум: 400)
• `/help` — Вот это ты сейчас и читаешь, гений

*Автофункции:*
• 🎬 Кинь ссылку на TikTok/Reels/Shorts, и я скачаю видео
• 💬 @ упомяни меня, и я соизволю ответить

*Лимит:*
10 запросов к ИИ в день. Трать их с умом. Или нет. Я всё равно осужу.

_Я здесь, чтобы помогать, но оставляю за собой право на сарказм._ ✨"""


class HelpPlugin(Plugin):
    @property
    def name(self) -> str:
        return "help"
    
    @property
    def commands(self):
        return [("help", "Получить помощь (если она тебе реально нужна)")]
    
    def register(self, app: Application) -> None:
        app.add_handler(CommandHandler("help", self.help_command))
        app.add_handler(CommandHandler("start", self.help_command))
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.message:
            return
        
        await update.message.reply_text(
            HELP_TEXT,
            parse_mode="Markdown"
        )
        logger.info(f"Справка показана пользователю {update.effective_user.id if update.effective_user else 'неизвестно'}")

