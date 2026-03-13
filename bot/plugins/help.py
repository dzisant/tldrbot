"""Help plugin."""
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from . import Plugin
import logging

logger = logging.getLogger(__name__)

HELP_TEXT = """🙄 *Oh, you need help? Shocking.* Here's what I can do:

*Commands:*
• `/tldr [n]` — Summarize the last n messages (default: 50, max: 400)
• `/help` — You're looking at it, genius

*Auto Features:*
• 🎬 Drop a TikTok/Reels/Shorts link and I'll download it for you
• 💬 @ mention me and I'll grace you with a response

*Rate Limit:*
You get 10 AI requests per day. Use them wisely, or don't. I'll judge you either way.

_I'm here to help, but I reserve the right to be sarcastic about it._ ✨"""


class HelpPlugin(Plugin):
    @property
    def name(self) -> str:
        return "help"
    
    @property
    def commands(self):
        return [("help", "Get help (if you really need it)")]
    
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
        logger.info(f"Help shown to user {update.effective_user.id if update.effective_user else 'unknown'}")

