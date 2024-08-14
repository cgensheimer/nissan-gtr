import requests
from nissan_gtr.services.config_service import get_user_ntfy_topic

class NotificationService:
    async def send_notification(self, user_name, message):
        topic = get_user_ntfy_topic(user_name)
        if topic:
            requests.post(f"https://ntfy.sh/{topic}",
                data=message.encode(encoding='utf-8')
            )
