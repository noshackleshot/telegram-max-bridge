"""
Webhook handlers for processing incoming messages from GREEN-API (Max).
"""
import logging
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

from app.config import settings
from app.telegram_client import telegram_client

logger = logging.getLogger(__name__)


# Pydantic models for GREEN-API webhook payloads
class MessageData(BaseModel):
    """Message data from GREEN-API webhook."""
    typeWebhook: str
    instanceData: Optional[Dict[str, Any]] = None
    timestamp: Optional[int] = None
    idMessage: Optional[str] = None
    senderData: Optional[Dict[str, Any]] = None
    messageData: Optional[Dict[str, Any]] = None


class WebhookHandler:
    """Handler for processing webhooks from GREEN-API."""

    def __init__(self):
        """Initialize webhook handler."""
        self.target_chat_id = settings.max_chat_id
        logger.info(f"Webhook handler initialized. Target chat: {self.target_chat_id or 'ALL'}")

    def should_process_message(self, chat_id: Optional[str]) -> bool:
        """
        Check if message from this chat should be processed.

        Args:
            chat_id: Chat ID from incoming message

        Returns:
            bool: True if message should be processed
        """
        # If no specific chat filter is set, process all messages
        if not self.target_chat_id:
            return True

        # Process only messages from target chat
        return chat_id == self.target_chat_id

    async def handle_incoming_message(self, payload: Dict[str, Any]) -> Dict[str, str]:
        """
        Handle incoming webhook from GREEN-API.

        Args:
            payload: Webhook payload from GREEN-API

        Returns:
            Dict with status
        """
        try:
            # Parse webhook type
            webhook_type = payload.get("typeWebhook")
            logger.info(f"Received webhook type: {webhook_type}")

            # We're interested in incoming and outgoing message notifications
            if webhook_type not in ["incomingMessageReceived", "incomingCall", "outgoingMessageReceived", "outgoingAPIMessageReceived"]:
                logger.debug(f"Ignoring webhook type: {webhook_type}")
                return {"status": "ignored", "reason": "not_a_message"}

            # Log full payload for debugging outgoing messages
            if "outgoing" in webhook_type.lower():
                logger.info(f"Outgoing webhook payload: {payload}")

            # Extract message data
            message_data = payload.get("messageData", {})
            sender_data = payload.get("senderData", {})
            instance_data = payload.get("instanceData", {})

            # Get chat ID to check filter
            chat_id = sender_data.get("chatId") or sender_data.get("sender")

            if not self.should_process_message(chat_id):
                logger.info(f"Skipping message from chat {chat_id} (not target chat)")
                return {"status": "ignored", "reason": "chat_filter"}

            # Extract sender info
            sender_name = sender_data.get("senderName") or sender_data.get("name")
            sender_phone = sender_data.get("sender", "").replace("@c.us", "")

            # Process based on message type
            type_message = message_data.get("typeMessage")

            if type_message == "textMessage":
                await self._handle_text_message(message_data, sender_name, sender_phone)
            elif type_message == "extendedTextMessage":
                await self._handle_extended_text_message(message_data, sender_name, sender_phone)
            elif type_message == "imageMessage":
                await self._handle_image_message(message_data, sender_name, sender_phone)
            elif type_message == "videoMessage":
                await self._handle_video_message(message_data, sender_name, sender_phone)
            elif type_message == "documentMessage":
                await self._handle_document_message(message_data, sender_name, sender_phone)
            elif type_message == "audioMessage":
                await self._handle_audio_message(message_data, sender_name, sender_phone)
            elif type_message == "voiceMessage":
                await self._handle_voice_message(message_data, sender_name, sender_phone)
            else:
                logger.warning(f"Unsupported message type: {type_message}")
                return {"status": "unsupported", "type": type_message}

            return {"status": "success"}

        except Exception as e:
            logger.error(f"Error handling webhook: {e}", exc_info=True)
            return {"status": "error", "message": str(e)}

    async def _handle_text_message(
        self,
        message_data: Dict[str, Any],
        sender_name: Optional[str],
        sender_phone: Optional[str]
    ):
        """Handle text message."""
        text = message_data.get("textMessageData", {}).get("textMessage", "")
        if text:
            await telegram_client.send_text_message(text, sender_name, sender_phone)

    async def _handle_extended_text_message(
        self,
        message_data: Dict[str, Any],
        sender_name: Optional[str],
        sender_phone: Optional[str]
    ):
        """Handle extended text message (outgoing messages from GREEN-API)."""
        text = message_data.get("extendedTextMessageData", {}).get("text", "")
        if text:
            await telegram_client.send_text_message(text, sender_name, sender_phone)

    async def _handle_image_message(
        self,
        message_data: Dict[str, Any],
        sender_name: Optional[str],
        sender_phone: Optional[str]
    ):
        """Handle image message."""
        image_data = message_data.get("fileMessageData") or message_data.get("downloadUrl")
        if isinstance(image_data, dict):
            image_url = image_data.get("downloadUrl")
            caption = message_data.get("caption")
        else:
            image_url = image_data
            caption = None

        if image_url:
            await telegram_client.send_photo(image_url, caption, sender_name, sender_phone)

    async def _handle_video_message(
        self,
        message_data: Dict[str, Any],
        sender_name: Optional[str],
        sender_phone: Optional[str]
    ):
        """Handle video message."""
        video_data = message_data.get("fileMessageData") or message_data.get("downloadUrl")
        if isinstance(video_data, dict):
            video_url = video_data.get("downloadUrl")
            caption = message_data.get("caption")
        else:
            video_url = video_data
            caption = None

        if video_url:
            await telegram_client.send_video(video_url, caption, sender_name, sender_phone)

    async def _handle_document_message(
        self,
        message_data: Dict[str, Any],
        sender_name: Optional[str],
        sender_phone: Optional[str]
    ):
        """Handle document message."""
        doc_data = message_data.get("fileMessageData") or {}
        document_url = doc_data.get("downloadUrl")
        filename = doc_data.get("fileName") or "document"
        caption = message_data.get("caption")

        if document_url:
            await telegram_client.send_document(
                document_url, filename, caption, sender_name, sender_phone
            )

    async def _handle_audio_message(
        self,
        message_data: Dict[str, Any],
        sender_name: Optional[str],
        sender_phone: Optional[str]
    ):
        """Handle audio message (treat as document)."""
        audio_data = message_data.get("fileMessageData") or {}
        audio_url = audio_data.get("downloadUrl")
        filename = audio_data.get("fileName") or "audio.mp3"

        if audio_url:
            await telegram_client.send_document(
                audio_url, filename, "🎵 Audio", sender_name, sender_phone
            )

    async def _handle_voice_message(
        self,
        message_data: Dict[str, Any],
        sender_name: Optional[str],
        sender_phone: Optional[str]
    ):
        """Handle voice message (treat as document)."""
        voice_data = message_data.get("fileMessageData") or {}
        voice_url = voice_data.get("downloadUrl")
        filename = voice_data.get("fileName") or "voice.ogg"

        if voice_url:
            await telegram_client.send_document(
                voice_url, filename, "🎤 Voice message", sender_name, sender_phone
            )


# Global webhook handler instance
webhook_handler = WebhookHandler()
