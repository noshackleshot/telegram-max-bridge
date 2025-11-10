"""
Main FastAPI application for Max to Telegram bridge.
Receives webhooks from GREEN-API and forwards messages to Telegram.
"""

import logging
import sys
from contextlib import asynccontextmanager
from typing import Any, Dict

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

import app.telegram_handlers as telegram_handlers
from app.config import settings
from app.handlers import webhook_handler
from app.telegram_client import telegram_client
from app.telegram_handlers import init_telegram_handler

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting Max to Telegram Bridge (Bidirectional)")
    logger.info(f"Max → Telegram: {'ENABLED' if settings.enable_max_to_telegram else 'DISABLED'}")
    logger.info(f"Telegram → Max: {'ENABLED' if settings.enable_telegram_to_max else 'DISABLED'}")

    # Validate settings
    if not settings.validate_settings():
        logger.error("Invalid configuration! Check your environment variables.")
        sys.exit(1)

    # Max → Telegram settings
    if settings.enable_max_to_telegram:
        logger.info(f"Telegram channel: {settings.telegram_channel_id}")
        logger.info(f"Max chat filter: {settings.max_chat_id or 'ALL CHATS'}")

    # Telegram → Max settings
    if settings.enable_telegram_to_max:
        # Initialize Telegram webhook handler
        init_telegram_handler(telegram_client.bot)
        logger.info(f"Telegram chat filter: {settings.telegram_chat_id or 'ALL CHATS'}")
        logger.info(f"Max target chat: {settings.max_target_chat_id}")

        # Register Telegram webhook if URL is configured
        if settings.telegram_webhook_url:
            try:
                await telegram_client.bot.set_webhook(
                    url=settings.telegram_webhook_url,
                    secret_token=settings.telegram_webhook_secret,
                    drop_pending_updates=True,
                )
                logger.info(f"Telegram webhook registered: {settings.telegram_webhook_url}")
            except Exception as e:
                logger.error(f"Failed to register Telegram webhook: {e}")
                logger.warning("Telegram → Max direction may not work without webhook registration")
        else:
            logger.warning(
                "TELEGRAM_WEBHOOK_URL not set. Telegram → Max will not work until webhook is registered manually."
            )

    logger.info("Application started successfully")

    yield

    # Shutdown
    logger.info("Shutting down application")

    # Delete Telegram webhook if enabled
    if settings.enable_telegram_to_max:
        try:
            await telegram_client.bot.delete_webhook(drop_pending_updates=True)
            logger.info("Telegram webhook deleted")
        except Exception as e:
            logger.error(f"Failed to delete Telegram webhook: {e}")

    await telegram_client.close()
    logger.info("Application stopped")


# Create FastAPI app
app = FastAPI(
    title="Max to Telegram Bridge",
    description="Forwards messages from Max messenger to Telegram channel via GREEN-API",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "running", "service": "max-to-telegram-bridge", "version": "1.0.0"}


@app.get("/health")
async def health_check():
    """Detailed health check."""
    return {
        "status": "healthy",
        "telegram_configured": bool(settings.telegram_bot_token),
        "max_configured": bool(settings.max_instance_id and settings.max_api_token),
        "directions": {
            "max_to_telegram": settings.enable_max_to_telegram,
            "telegram_to_max": settings.enable_telegram_to_max,
        },
        "max_to_telegram": {
            "enabled": settings.enable_max_to_telegram,
            "channel_id": settings.telegram_channel_id if settings.enable_max_to_telegram else None,
            "chat_filter": settings.max_chat_id or "all",
        },
        "telegram_to_max": {
            "enabled": settings.enable_telegram_to_max,
            "chat_filter": settings.telegram_chat_id or "all",
            "target_chat": settings.max_target_chat_id if settings.enable_telegram_to_max else None,
        },
    }


@app.post("/webhook")
async def webhook_endpoint(request: Request):
    """
    Webhook endpoint for receiving messages from GREEN-API (Max → Telegram).

    Expected format from GREEN-API:
    {
        "typeWebhook": "incomingMessageReceived",
        "instanceData": {...},
        "timestamp": 1234567890,
        "idMessage": "...",
        "senderData": {
            "chatId": "...",
            "sender": "...",
            "senderName": "..."
        },
        "messageData": {
            "typeMessage": "textMessage",
            "textMessageData": {
                "textMessage": "Hello"
            }
        }
    }
    """
    try:
        # Check if Max → Telegram is enabled
        if not settings.enable_max_to_telegram:
            logger.warning("Received Max webhook but Max → Telegram is disabled")
            return JSONResponse(
                content={"status": "disabled", "message": "Max → Telegram direction is disabled"},
                status_code=200,
            )

        # Parse JSON payload
        payload = await request.json()
        logger.debug(f"Received webhook: {payload}")

        # Verify webhook secret if configured
        if settings.webhook_secret:
            auth_header = request.headers.get("Authorization")
            if not auth_header or auth_header != f"Bearer {settings.webhook_secret}":
                logger.warning("Unauthorized webhook request")
                raise HTTPException(status_code=401, detail="Unauthorized")

        # Process webhook
        result = await webhook_handler.handle_incoming_message(payload)

        return JSONResponse(content=result, status_code=200)

    except Exception as e:
        logger.error(f"Error processing webhook: {e}", exc_info=True)
        return JSONResponse(content={"status": "error", "message": str(e)}, status_code=500)


@app.post("/telegram/webhook")
async def telegram_webhook_endpoint(request: Request):
    """
    Webhook endpoint for receiving messages from Telegram Bot API (Telegram → Max).

    Expected format from Telegram:
    {
        "update_id": 12345,
        "message": {
            "message_id": 123,
            "from": {...},
            "chat": {...},
            "text": "Hello"
        }
    }
    """
    try:
        # Check if Telegram → Max is enabled
        if not settings.enable_telegram_to_max:
            logger.warning("Received Telegram webhook but Telegram → Max is disabled")
            return JSONResponse(
                content={"status": "disabled", "message": "Telegram → Max direction is disabled"},
                status_code=200,
            )

        # Verify secret token if configured
        if settings.telegram_webhook_secret:
            secret_header = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
            if not secret_header or secret_header != settings.telegram_webhook_secret:
                logger.warning("Unauthorized Telegram webhook request")
                raise HTTPException(status_code=401, detail="Unauthorized")

        # Parse JSON payload
        update_data = await request.json()
        logger.debug(f"Received Telegram update: {update_data}")

        # Process update
        if telegram_handlers.telegram_webhook_handler:
            result = await telegram_handlers.telegram_webhook_handler.handle_update(update_data)
            return JSONResponse(content=result, status_code=200)
        else:
            logger.error("Telegram webhook handler not initialized")
            return JSONResponse(
                content={"status": "error", "message": "Handler not initialized"}, status_code=500
            )

    except Exception as e:
        logger.error(f"Error processing Telegram webhook: {e}", exc_info=True)
        return JSONResponse(content={"status": "error", "message": str(e)}, status_code=500)


@app.post("/test")
async def test_endpoint(request: Request):
    """Test endpoint for manual message sending."""
    try:
        data = await request.json()
        text = data.get("text", "Test message from Max bridge")
        sender_name = data.get("sender_name", "Test User")

        await telegram_client.send_text_message(text, sender_name=sender_name)

        return {"status": "success", "message": "Test message sent to Telegram"}

    except Exception as e:
        logger.error(f"Error in test endpoint: {e}", exc_info=True)
        return JSONResponse(content={"status": "error", "message": str(e)}, status_code=500)


def main():
    """Run the application."""
    logger.info(f"Starting server on {settings.webhook_host}:{settings.webhook_port}")

    uvicorn.run(
        "app.main:app",
        host=settings.webhook_host,
        port=settings.webhook_port,
        log_level=settings.log_level.lower(),
        access_log=True,
    )


if __name__ == "__main__":
    main()
