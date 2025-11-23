import logging
import os
import asyncio
import re
from dotenv import load_dotenv
from telegram import Update
from telegram.error import BadRequest
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
from ai_agent import AIAgent

# Load environment variables
load_dotenv()

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


def _strip_markdown(text: str) -> str:
    """
    Very simple Markdown cleaner used as a last-resort fallback
    when Telegram refuses to parse entities.

    For now we just remove the most common formatting symbols so
    the user does not see raw '*' and '`' characters.
    """
    if not isinstance(text, str):
        return text
    # Remove *, _, ` which are often used for bold/italic/code.
    return re.sub(r"[*_`]", "", text)

# Initialize AI Agent
try:
    github_token = os.getenv('GITHUB_TOKEN')
    agent = AIAgent(github_token)
except Exception as e:
    logger.error(f"Failed to initialize AI Agent: {e}")
    agent = None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handler for the /start command.
    """
    chat_id = update.effective_chat.id

    # Reset chat session on start
    if agent:
        context.user_data['chat'] = agent.start_chat()
        
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=(
            "Привіт! Я AI-рекрутер бот. 🤖\n\n"
            "Я можу аналізувати GitHub-профілі та допомагати оцінювати кандидатів.\n"
            "Просто надішліть мені GitHub-нік або посилання на профіль (наприклад, `https://github.com/torvalds`) "
            "і сформулюйте, що саме вас цікавить."
        ),
        parse_mode="Markdown",
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handler for text messages.
    """
    message = update.effective_message
    if not message or not message.text:
        logger.info("Received update without a text message. Skipping handling.")
        return

    user_text = message.text
    chat_id = update.effective_chat.id

    if not agent:
        await context.bot.send_message(chat_id=chat_id, text="Error: AI Agent is not initialized. Please check server logs.")
        return

    # Get or create chat session
    if 'chat' not in context.user_data:
        context.user_data['chat'] = agent.start_chat()
    
    chat_session = context.user_data['chat']
    # Single "typing" notification before heavy work
    await context.bot.send_chat_action(chat_id=chat_id, action="typing")

    # If the message looks like a GitHub profile / link, let the user know
    # that a potentially longer GitHub investigation is starting.
    lowered = (user_text or "").lower()
    if "github.com" in lowered or lowered.startswith("github.com/"):
        await context.bot.send_message(
            chat_id=chat_id,
            text="🔎 Досліджую GitHub-профіль, це може зайняти кілька секунд...",
        )

    try:
        # Send message to Gemini (Gemini chat session already містить історію діалогу)
        loop = asyncio.get_running_loop()

        response = await loop.run_in_executor(
            None,
            chat_session.send_message,
            user_text
        )

        # Try to send with Markdown; if Telegram can't parse entities,
        # fall back to plain text so the user still gets a response.
        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text=response.text,
                parse_mode="Markdown",
            )
        except BadRequest as e:
            if "Can't parse entities" in str(e):
                logger.warning(f"Markdown parse failed, sending without formatting: {e}")
                cleaned = _strip_markdown(response.text)
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=cleaned,
                )
            else:
                raise

    except Exception as e:
        logger.error(f"Error processing message: {e}")
        await context.bot.send_message(
            chat_id=chat_id,
            text="Сталася помилка під час обробки запиту. Будь ласка, спробуйте ще раз пізніше."
        )

if __name__ == '__main__':
    token = os.getenv('TELEGRAM_TOKEN')
    if not token:
        print("Error: TELEGRAM_TOKEN not found in environment variables.")
        exit(1)

    application = ApplicationBuilder().token(token).build()
    
    # Add handlers
    start_handler = CommandHandler('start', start)
    message_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message)
    
    application.add_handler(start_handler)
    application.add_handler(message_handler)
    
    print("AI Recruiter Bot is running...")
    application.run_polling()
