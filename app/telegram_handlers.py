"""
Telegram webhook handlers for processing incoming messages.
Receives messages from Telegram and forwards to Max via GREEN-API.
"""

import logging
from typing import Dict, Any, Optional, List
from aiogram import Bot, Dispatcher
from aiogram.types import Message, Update, PhotoSize
from aiogram.filters import CommandStart

from app.config import settings
from app.green_api_client import green_api_client

logger = logging.getLogger(__name__)


class TelegramWebhookHandler:
    """Handler for processing Telegram webhooks."""

    def __init__(self, bot: Bot):
        """
        Initialize Telegram webhook handler.

        Args:
            bot: aiogram Bot instance
        """
        self.bot = bot
        self.dispatcher = Dispatcher()
        self.target_chat_id = settings.telegram_chat_id
        self.max_target_chat = settings.max_target_chat_id

        # Register message handlers
        self._register_handlers()

        logger.info(f"Telegram webhook handler initialized")
        logger.info(f"Target Telegram chat: {self.target_chat_id or 'ALL'}")
        logger.info(f"Target Max chat: {self.max_target_chat}")

    def _register_handlers(self):
        """Register message handlers with dispatcher."""
        # Text messages
        self.dispatcher.message.register(
            self._handle_text_message,
            lambda message: message.text and not message.text.startswith("/"),
        )

        # Photos
        self.dispatcher.message.register(
            self._handle_photo_message, lambda message: message.photo is not None
        )

        # Videos
        self.dispatcher.message.register(
            self._handle_video_message, lambda message: message.video is not None
        )

        # Documents
        self.dispatcher.message.register(
            self._handle_document_message, lambda message: message.document is not None
        )

        # Voice messages
        self.dispatcher.message.register(
            self._handle_voice_message, lambda message: message.voice is not None
        )

        # Audio files
        self.dispatcher.message.register(
            self._handle_audio_message, lambda message: message.audio is not None
        )

    def should_process_message(self, chat_id: int) -> bool:
        """
        Check if message from this chat should be processed.

        Args:
            chat_id: Telegram chat ID

        Returns:
            bool: True if message should be processed
        """
        # If no specific chat filter is set, process all messages
        if not self.target_chat_id:
            return True

        # Process only messages from target chat
        return str(chat_id) == str(self.target_chat_id)

    async def handle_update(self, update_data: Dict[str, Any]) -> Dict[str, str]:
        """
        Handle incoming Telegram update.

        Args:
            update_data: Raw update data from Telegram

        Returns:
            Dict with status
        """
        try:
            # Parse update
            update = Update(**update_data)

            # Feed update to dispatcher
            await self.dispatcher.feed_update(bot=self.bot, update=update)

            return {"status": "success"}

        except Exception as e:
            logger.error(f"Error handling Telegram update: {e}", exc_info=True)
            return {"status": "error", "message": str(e)}

    def _get_sender_info(self, message: Message) -> tuple[Optional[str], Optional[str]]:
        """
        Extract sender information from message.

        Args:
            message: Telegram message

        Returns:
            tuple: (sender_name, sender_username)
        """
        sender = message.from_user
        if not sender:
            return None, None

        # Get full name
        sender_name = sender.full_name

        # Get username
        sender_username = sender.username

        return sender_name, sender_username

    async def _handle_text_message(self, message: Message):
        """Handle text message from Telegram."""
        try:
            # Check if should process
            if not self.should_process_message(message.chat.id):
                logger.debug(f"Skipping message from chat {message.chat.id}")
                return

            # Get sender info
            sender_name, sender_username = self._get_sender_info(message)

            # Get text
            text = message.text or ""

            logger.info(f"Processing text message from Telegram: {text[:50]}...")

            # Send to Max
            await green_api_client.send_text_message(
                chat_id=self.max_target_chat,
                text=text,
                sender_name=sender_name,
                sender_username=sender_username,
            )

        except Exception as e:
            logger.error(f"Error handling text message: {e}", exc_info=True)

    async def _handle_photo_message(self, message: Message):
        """Handle photo message from Telegram."""
        try:
            # Check if should process
            if not self.should_process_message(message.chat.id):
                logger.debug(f"Skipping photo from chat {message.chat.id}")
                return

            # Get sender info
            sender_name, sender_username = self._get_sender_info(message)

            # Get largest photo
            photo: PhotoSize = message.photo[-1]  # Last item is largest

            # Get file URL
            file = await self.bot.get_file(photo.file_id)
            file_url = f"https://api.telegram.org/file/bot{self.bot.token}/{file.file_path}"

            # Get caption
            caption = message.caption

            logger.info(f"Processing photo from Telegram: {photo.file_id}")

            # Send to Max
            await green_api_client.send_photo(
                chat_id=self.max_target_chat,
                photo_url=file_url,
                caption=caption,
                sender_name=sender_name,
                sender_username=sender_username,
            )

        except Exception as e:
            logger.error(f"Error handling photo message: {e}", exc_info=True)

    async def _handle_video_message(self, message: Message):
        """Handle video message from Telegram."""
        try:
            # Check if should process
            if not self.should_process_message(message.chat.id):
                logger.debug(f"Skipping video from chat {message.chat.id}")
                return

            # Get sender info
            sender_name, sender_username = self._get_sender_info(message)

            # Get video
            video = message.video

            # Get file URL
            file = await self.bot.get_file(video.file_id)
            file_url = f"https://api.telegram.org/file/bot{self.bot.token}/{file.file_path}"

            # Get caption
            caption = message.caption

            logger.info(f"Processing video from Telegram: {video.file_id}")

            # Send to Max
            await green_api_client.send_video(
                chat_id=self.max_target_chat,
                video_url=file_url,
                caption=caption,
                sender_name=sender_name,
                sender_username=sender_username,
            )

        except Exception as e:
            logger.error(f"Error handling video message: {e}", exc_info=True)

    async def _handle_document_message(self, message: Message):
        """Handle document message from Telegram."""
        try:
            # Check if should process
            if not self.should_process_message(message.chat.id):
                logger.debug(f"Skipping document from chat {message.chat.id}")
                return

            # Get sender info
            sender_name, sender_username = self._get_sender_info(message)

            # Get document
            document = message.document

            # Get file URL
            file = await self.bot.get_file(document.file_id)
            file_url = f"https://api.telegram.org/file/bot{self.bot.token}/{file.file_path}"

            # Get filename and caption
            filename = document.file_name or "document"
            caption = message.caption

            logger.info(f"Processing document from Telegram: {filename}")

            # Send to Max
            await green_api_client.send_document(
                chat_id=self.max_target_chat,
                document_url=file_url,
                filename=filename,
                caption=caption,
                sender_name=sender_name,
                sender_username=sender_username,
            )

        except Exception as e:
            logger.error(f"Error handling document message: {e}", exc_info=True)

    async def _handle_voice_message(self, message: Message):
        """Handle voice message from Telegram."""
        try:
            # Check if should process
            if not self.should_process_message(message.chat.id):
                logger.debug(f"Skipping voice from chat {message.chat.id}")
                return

            # Get sender info
            sender_name, sender_username = self._get_sender_info(message)

            # Get voice
            voice = message.voice

            # Get file URL
            file = await self.bot.get_file(voice.file_id)
            file_url = f"https://api.telegram.org/file/bot{self.bot.token}/{file.file_path}"

            logger.info(f"Processing voice message from Telegram: {voice.file_id}")

            # Send to Max as document
            await green_api_client.send_document(
                chat_id=self.max_target_chat,
                document_url=file_url,
                filename="voice.ogg",
                caption="🎤 Voice message",
                sender_name=sender_name,
                sender_username=sender_username,
            )

        except Exception as e:
            logger.error(f"Error handling voice message: {e}", exc_info=True)

    async def _handle_audio_message(self, message: Message):
        """Handle audio message from Telegram."""
        try:
            # Check if should process
            if not self.should_process_message(message.chat.id):
                logger.debug(f"Skipping audio from chat {message.chat.id}")
                return

            # Get sender info
            sender_name, sender_username = self._get_sender_info(message)

            # Get audio
            audio = message.audio

            # Get file URL
            file = await self.bot.get_file(audio.file_id)
            file_url = f"https://api.telegram.org/file/bot{self.bot.token}/{file.file_path}"

            # Get filename
            filename = audio.file_name or "audio.mp3"

            logger.info(f"Processing audio from Telegram: {filename}")

            # Send to Max as document
            await green_api_client.send_document(
                chat_id=self.max_target_chat,
                document_url=file_url,
                filename=filename,
                caption="🎵 Audio",
                sender_name=sender_name,
                sender_username=sender_username,
            )

        except Exception as e:
            logger.error(f"Error handling audio message: {e}", exc_info=True)


# Global handler instance will be created in main.py
telegram_webhook_handler: Optional[TelegramWebhookHandler] = None


def init_telegram_handler(bot: Bot) -> TelegramWebhookHandler:
    """
    Initialize global Telegram webhook handler.

    Args:
        bot: aiogram Bot instance

    Returns:
        TelegramWebhookHandler instance
    """
    global telegram_webhook_handler
    telegram_webhook_handler = TelegramWebhookHandler(bot)
    return telegram_webhook_handler
