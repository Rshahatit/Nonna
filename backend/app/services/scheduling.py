"""Call scheduling service — checks for due calls and triggers them."""

import logging
from datetime import datetime, timezone

from app.services import firestore
from app.services.twilio_service import place_outbound_call

logger = logging.getLogger(__name__)

# Map day names to weekday numbers
DAY_MAP = {
    "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
    "friday": 4, "saturday": 5, "sunday": 6,
}


async def check_and_trigger_scheduled_calls() -> list[str]:
    """Check all elders for due calls and trigger outbound calls.

    Called periodically by Cloud Scheduler (every 15 minutes).
    Returns list of elder IDs that were called.
    """
    db = firestore.get_db()
    called = []

    async for doc in db.collection("elders").stream():
        elder_data = doc.to_dict()
        elder_id = doc.id
        schedule = elder_data.get("callSchedule", {})

        if not schedule.get("days") or not schedule.get("time"):
            continue

        try:
            tz_name = schedule.get("timezone", "America/New_York")
            # Check if today is a scheduled day
            import zoneinfo
            tz = zoneinfo.ZoneInfo(tz_name)
            now_local = datetime.now(tz)
            today_name = now_local.strftime("%A").lower()

            if today_name not in [d.lower() for d in schedule["days"]]:
                continue

            # Check if it's within the scheduled time window (±15 min)
            scheduled_time = schedule["time"]  # "HH:MM"
            hour, minute = map(int, scheduled_time.split(":"))
            scheduled_minutes = hour * 60 + minute
            current_minutes = now_local.hour * 60 + now_local.minute

            if abs(current_minutes - scheduled_minutes) > 15:
                continue

            # Check if elder already had a session today
            memory = await firestore.get_elder_memory(elder_id)
            if memory.last_session_date:
                last_local = memory.last_session_date.astimezone(tz)
                if last_local.date() == now_local.date():
                    continue

            # Place the call
            logger.info(f"Triggering scheduled call for elder {elder_id}")
            call_sid = await place_outbound_call(elder_id)
            if call_sid:
                called.append(elder_id)

        except Exception as e:
            logger.error(f"Error processing schedule for elder {elder_id}: {e}")

    return called
