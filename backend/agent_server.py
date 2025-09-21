# backend/agent_server.py
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Dict, Any
from tools.weather_tool import WeatherTool
from tools.time_tool import TimeTool
from bedrock_config import SYSTEM_PROMPT
import uuid

app = FastAPI(title="AI Agent ToolUse Demo")

MAX_RECURSIONS = 5

class UserMessage(BaseModel):
    text: str

# ---------------- AI Agent ----------------
def decide_tool_ai(user_text: str) -> Dict[str, Any]:
    """
    AI Agent วิเคราะห์เองเพื่อเลือก Tool
    heuristic: ถ้ามีเลข lat/lon หรือ city -> Weather_Tool, else -> Time_Tool
    """
    import re
    latlon_match = re.findall(r"(-?\d+\.?\d*)", user_text)
    city_match = re.findall(r"[ก-๙a-zA-Z\s]{2,20}", user_text)

    if latlon_match and len(latlon_match) >= 2:
        return {"name": "Weather_Tool", "input": {"latitude": latlon_match[0], "longitude": latlon_match[1], "cnt": 3}, "toolUseId": str(uuid.uuid4())}
    elif city_match:
        city = city_match[0].strip()
        return {"name": "Weather_Tool", "input": {"city": city, "cnt": 3}, "toolUseId": str(uuid.uuid4())}

    # fallback
    return {"name": "Time_Tool", "input": {"timezone": "Asia/Bangkok"}, "toolUseId": str(uuid.uuid4())}

def invoke_tool(payload: Dict[str, Any]) -> Dict[str, Any]:
    tool_name = payload["name"]
    input_data = payload.get("input", {})
    tool_id = payload["toolUseId"]

    if tool_name == "Weather_Tool":
        result = WeatherTool.fetch_weather_data(input_data)
    elif tool_name == "Time_Tool":
        result = TimeTool.fetch_time_data(input_data)
    else:
        result = {"error": True, "message": f"Tool {tool_name} not found"}

    return {"toolUseId": tool_id, "content": result}

def process_agent(user_text: str, recursion: int = MAX_RECURSIONS) -> Dict[str, Any]:
    if recursion <= 0:
        return {"error": "max_recursion", "message": "Maximum recursion reached."}

    tool_payload = decide_tool_ai(user_text)
    tool_result = invoke_tool(tool_payload)
    return {
        "user_input": user_text,
        "tool_called": tool_payload["name"],
        "tool_input": tool_payload.get("input", {}),
        "tool_result": tool_result["content"],
        "system_prompt": SYSTEM_PROMPT
    }

# ---------------- FastAPI endpoint ----------------
@app.post("/chat_agent")
def chat_agent(msg: UserMessage):
    response = process_agent(msg.text, MAX_RECURSIONS)
    return response
