import aiohttp
from nissan_gtr.services.config_service import get_user_ntfy_topic


class NotificationService:
    def __init__(self):
        self.session = None

    async def get_session(self):
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session

    async def close_session(self):
        if self.session and not self.session.closed:
            await self.session.close()

    async def send_notification(self, user_name, message):
        topic = get_user_ntfy_topic(user_name)
        if topic:
            session = await self.get_session()
            try:
                async with session.post(
                    f"https://ntfy.sh/{topic}", data=message.encode(encoding="utf-8")
                ) as response:
                    pass  # Just fire and forget
            except Exception as e:
                print(f"Error sending notification: {e}")
