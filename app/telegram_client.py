"""
Telegram client for sending messages to Telegram channel.
Uses aiogram for async operations.
"""

import logging
import os
import tempfile
from typing import Optional

import aiohttp
from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from aiogram.types import FSInputFile

from app.config import settings

logger = logging.getLogger(__name__)


class TelegramClient:
    """Client for sending messages to Telegram channel."""

    def __init__(self):
        """Initialize Telegram bot."""
        self.bot = Bot(token=settings.telegram_bot_token)
        self.channel_id = settings.telegram_channel_id
        logger.info(f"Telegram client initialized for channel: {self.channel_id}")

    async def send_text_message(
        self, text: str, sender_name: Optional[str] = None, sender_phone: Optional[str] = None
    ) -> bool:
        """
        Send text message to Telegram channel.

        Args:
            text: Message text
            sender_name: Name of the sender from Max
            sender_phone: Phone number of the sender

        Returns:
            bool: True if message sent successfully
        """
        try:
            # Format message with sender info
            formatted_message = self._format_message(text, sender_name, sender_phone)

            await self.bot.send_message(
                chat_id=self.channel_id, text=formatted_message, parse_mode="HTML"
            )
            logger.info(f"Text message sent to Telegram: {text[:50]}...")
            return True

        except TelegramAPIError as e:
            logger.error(f"Failed to send text message to Telegram: {e}")
            return False

    async def send_photo(
        self,
        photo_url: str,
        caption: Optional[str] = None,
        sender_name: Optional[str] = None,
        sender_phone: Optional[str] = None,
    ) -> bool:
        """
        Send photo to Telegram channel.

        Args:
            photo_url: URL of the photo
            caption: Photo caption
            sender_name: Name of the sender from Max
            sender_phone: Phone number of the sender

        Returns:
            bool: True if photo sent successfully
        """
        try:
            formatted_caption = self._format_message(
                caption or "📷 Photo", sender_name, sender_phone
            )

            # Download photo and send
            temp_file = await self._download_file(photo_url)
            if temp_file:
                photo = FSInputFile(temp_file)
                await self.bot.send_photo(
                    chat_id=self.channel_id,
                    photo=photo,
                    caption=formatted_caption,
                    parse_mode="HTML",
                )
                os.unlink(temp_file)  # Clean up temp file
                logger.info(f"Photo sent to Telegram: {photo_url[:50]}...")
                return True
            return False

        except TelegramAPIError as e:
            logger.error(f"Failed to send photo to Telegram: {e}")
            return False

    async def send_document(
        self,
        document_url: str,
        filename: Optional[str] = None,
        caption: Optional[str] = None,
        sender_name: Optional[str] = None,
        sender_phone: Optional[str] = None,
    ) -> bool:
        """
        Send document to Telegram channel.

        Args:
            document_url: URL of the document
            filename: Document filename
            caption: Document caption
            sender_name: Name of the sender from Max
            sender_phone: Phone number of the sender

        Returns:
            bool: True if document sent successfully
        """
        try:
            formatted_caption = self._format_message(
                caption or f"📄 {filename or 'Document'}", sender_name, sender_phone
            )

            # Download document and send
            temp_file = await self._download_file(document_url)
            if temp_file:
                document = FSInputFile(temp_file, filename=filename)
                await self.bot.send_document(
                    chat_id=self.channel_id,
                    document=document,
                    caption=formatted_caption,
                    parse_mode="HTML",
                )
                os.unlink(temp_file)  # Clean up temp file
                logger.info(f"Document sent to Telegram: {filename}")
                return True
            return False

        except TelegramAPIError as e:
            logger.error(f"Failed to send document to Telegram: {e}")
            return False

    async def send_video(
        self,
        video_url: str,
        caption: Optional[str] = None,
        sender_name: Optional[str] = None,
        sender_phone: Optional[str] = None,
    ) -> bool:
        """
        Send video to Telegram channel.

        Args:
            video_url: URL of the video
            caption: Video caption
            sender_name: Name of the sender from Max
            sender_phone: Phone number of the sender

        Returns:
            bool: True if video sent successfully
        """
        try:
            formatted_caption = self._format_message(
                caption or "🎥 Video", sender_name, sender_phone
            )

            # Download video and send
            temp_file = await self._download_file(video_url)
            if temp_file:
                video = FSInputFile(temp_file)
                await self.bot.send_video(
                    chat_id=self.channel_id,
                    video=video,
                    caption=formatted_caption,
                    parse_mode="HTML",
                )
                os.unlink(temp_file)  # Clean up temp file
                logger.info(f"Video sent to Telegram: {video_url[:50]}...")
                return True
            return False

        except TelegramAPIError as e:
            logger.error(f"Failed to send video to Telegram: {e}")
            return False

    def _format_message(
        self, text: str, sender_name: Optional[str] = None, sender_phone: Optional[str] = None
    ) -> str:
        """
        Format message with sender information.

        Args:
            text: Original message text
            sender_name: Sender name
            sender_phone: Sender phone (not used, kept for compatibility)

        Returns:
            str: Formatted message
        """
        if sender_name:
            header = f"👤 <b>{sender_name}</b>"
            return f"{header}\n\n{text}"
        return text

    async def _download_file(self, url: str) -> Optional[str]:
        """
        Download file from URL to temporary file.

        Args:
            url: File URL

        Returns:
            Optional[str]: Path to temporary file or None if failed
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        # Create temporary file
                        suffix = os.path.splitext(url)[1] or ""
                        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                            content = await response.read()
                            tmp.write(content)
                            return tmp.name
            return None
        except Exception as e:
            logger.error(f"Failed to download file from {url}: {e}")
            return None

    async def close(self):
        """Close bot session."""
        await self.bot.session.close()
        logger.info("Telegram client closed")


# Global telegram client instance
telegram_client = TelegramClient()
