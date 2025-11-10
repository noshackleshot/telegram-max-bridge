"""
GREEN-API client for sending messages to Max messenger.
Uses GREEN-API REST endpoints for async operations.
"""

import logging
from typing import Optional
import aiohttp
from app.config import settings

logger = logging.getLogger(__name__)


class GreenApiClient:
    """Client for sending messages to Max via GREEN-API."""

    def __init__(self):
        """Initialize GREEN-API client."""
        self.instance_id = settings.max_instance_id
        self.api_token = settings.max_api_token
        # Extract server ID from instance ID (first 4 digits)
        server_id = str(self.instance_id)[:4]
        self.base_url = f"https://{server_id}.api.green-api.com/v3/waInstance{self.instance_id}"
        logger.info(
            f"GREEN-API client initialized for instance: {self.instance_id} (server: {server_id})"
        )

    def _format_chat_id(self, chat_id: str) -> str:
        """
        Format chat ID for GREEN-API (Max messenger).
        Max uses numeric chat IDs without suffixes.

        Groups: negative IDs (e.g., -69020002426896)
        Personal chats: positive IDs (e.g., 16958332)

        Args:
            chat_id: Chat ID (numeric) or with accidentally added suffix

        Returns:
            str: Clean numeric chat ID (e.g., -69020002426896 or 16958332)
        """
        # Remove any accidentally added WhatsApp-style suffixes
        # (Max doesn't use them, but users might add them by mistake)
        chat_id = chat_id.replace("@c.us", "").replace("@g.us", "")

        # Return clean numeric ID
        return chat_id

    async def send_text_message(
        self,
        chat_id: str,
        text: str,
        sender_name: Optional[str] = None,
        sender_username: Optional[str] = None,
    ) -> bool:
        """
        Send text message to Max chat.

        Args:
            chat_id: Target chat ID (phone number)
            text: Message text
            sender_name: Name of Telegram sender
            sender_username: Username of Telegram sender

        Returns:
            bool: True if message sent successfully
        """
        try:
            # Format chat ID
            formatted_chat_id = self._format_chat_id(chat_id)

            # Format message with sender info
            formatted_message = self._format_message(text, sender_name, sender_username)

            # Prepare API request
            url = f"{self.base_url}/sendMessage/{self.api_token}"
            payload = {"chatId": formatted_chat_id, "message": formatted_message}

            # Send request
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as response:
                    if response.status == 200:
                        result = await response.json()
                        logger.info(
                            f"Text message sent to Max: {text[:50]}... (ID: {result.get('idMessage')})"
                        )
                        return True
                    else:
                        error_text = await response.text()
                        logger.error(
                            f"Failed to send text to Max. Status: {response.status}, Error: {error_text}"
                        )
                        return False

        except Exception as e:
            logger.error(f"Error sending text message to Max: {e}", exc_info=True)
            return False

    async def send_file_by_url(
        self,
        chat_id: str,
        file_url: str,
        filename: str,
        caption: Optional[str] = None,
        sender_name: Optional[str] = None,
        sender_username: Optional[str] = None,
    ) -> bool:
        """
        Send file (photo, video, document) to Max chat by URL.

        Args:
            chat_id: Target chat ID (phone number)
            file_url: URL of the file to send
            filename: Name of the file
            caption: Optional caption
            sender_name: Name of Telegram sender
            sender_username: Username of Telegram sender

        Returns:
            bool: True if file sent successfully
        """
        try:
            # Format chat ID
            formatted_chat_id = self._format_chat_id(chat_id)

            # Format caption with sender info
            formatted_caption = self._format_message(
                caption or f"📎 {filename}", sender_name, sender_username
            )

            # Prepare API request
            url = f"{self.base_url}/sendFileByUrl/{self.api_token}"
            payload = {
                "chatId": formatted_chat_id,
                "urlFile": file_url,
                "fileName": filename,
                "caption": formatted_caption,
            }

            # Send request
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as response:
                    if response.status == 200:
                        result = await response.json()
                        logger.info(f"File sent to Max: {filename} (ID: {result.get('idMessage')})")
                        return True
                    else:
                        error_text = await response.text()
                        logger.error(
                            f"Failed to send file to Max. Status: {response.status}, Error: {error_text}"
                        )
                        return False

        except Exception as e:
            logger.error(f"Error sending file to Max: {e}", exc_info=True)
            return False

    async def send_photo(
        self,
        chat_id: str,
        photo_url: str,
        caption: Optional[str] = None,
        sender_name: Optional[str] = None,
        sender_username: Optional[str] = None,
    ) -> bool:
        """
        Send photo to Max chat.

        Args:
            chat_id: Target chat ID
            photo_url: URL of the photo
            caption: Optional caption
            sender_name: Name of Telegram sender
            sender_username: Username of Telegram sender

        Returns:
            bool: True if photo sent successfully
        """
        return await self.send_file_by_url(
            chat_id, photo_url, "photo.jpg", caption or "📷 Photo", sender_name, sender_username
        )

    async def send_video(
        self,
        chat_id: str,
        video_url: str,
        caption: Optional[str] = None,
        sender_name: Optional[str] = None,
        sender_username: Optional[str] = None,
    ) -> bool:
        """
        Send video to Max chat.

        Args:
            chat_id: Target chat ID
            video_url: URL of the video
            caption: Optional caption
            sender_name: Name of Telegram sender
            sender_username: Username of Telegram sender

        Returns:
            bool: True if video sent successfully
        """
        return await self.send_file_by_url(
            chat_id, video_url, "video.mp4", caption or "🎥 Video", sender_name, sender_username
        )

    async def send_document(
        self,
        chat_id: str,
        document_url: str,
        filename: str,
        caption: Optional[str] = None,
        sender_name: Optional[str] = None,
        sender_username: Optional[str] = None,
    ) -> bool:
        """
        Send document to Max chat.

        Args:
            chat_id: Target chat ID
            document_url: URL of the document
            filename: Document filename
            caption: Optional caption
            sender_name: Name of Telegram sender
            sender_username: Username of Telegram sender

        Returns:
            bool: True if document sent successfully
        """
        return await self.send_file_by_url(
            chat_id,
            document_url,
            filename,
            caption or f"📄 {filename}",
            sender_name,
            sender_username,
        )

    def _format_message(
        self, text: str, sender_name: Optional[str] = None, sender_username: Optional[str] = None
    ) -> str:
        """
        Format message with sender information.

        Args:
            text: Original message text
            sender_name: Sender name
            sender_username: Sender username

        Returns:
            str: Formatted message
        """
        sender_info = []

        if sender_name:
            sender_info.append(f"👤 {sender_name}")
        if sender_username:
            sender_info.append(f"@{sender_username}")

        if sender_info:
            header = " | ".join(sender_info)
            return f"📨 *From Telegram:* {header}\n\n{text}"

        return text


# Global GREEN-API client instance
green_api_client = GreenApiClient()
