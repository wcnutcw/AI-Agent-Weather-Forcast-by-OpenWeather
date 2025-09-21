# tools/time_tool.py
from datetime import datetime
import pytz

class TimeTool:
    @staticmethod
    def get_tool_spec():
        return {
            "toolSpec": {
                "name": "Time_Tool",
                "description": "Get the current local time for Thailand or any specified timezone.",
                "inputSchema": {
                    "json": {
                        "type": "object",
                        "properties": {
                            "timezone": {
                                "type": "string",
                                "description": "Timezone in TZ format, e.g., Asia/Bangkok. Default is Asia/Bangkok."
                            }
                        },
                        "required": []
                    }
                },
            }
        }

    @staticmethod
    def fetch_time_data(input_data):
        tz_name = input_data.get("timezone", "Asia/Bangkok")
        tz = pytz.timezone(tz_name)
        now = datetime.now(tz)
        return {
            "current_time": now.strftime("%Y-%m-%d %H:%M:%S"),
            "date": now.strftime("%d-%m-%Y"),
            "time": now.strftime("%H:%M:%S"),
            "timezone": tz_name
        }