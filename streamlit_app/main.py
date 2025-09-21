# streamlit_app/main.py
import streamlit as st
import requests
import json
from typing import Dict, Any, List
import sys
import os

# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.weather_tool import WeatherTool
from tools.time_tool import TimeTool
from tools.output_helper import Output
from bedrock_config import MODEL_ID, SYSTEM_PROMPT, AWS_REGION, MAX_RECURSIONS

# Page configuration
st.set_page_config(
    page_title="RBH Weather AI Agent",
    page_icon="🌤️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better UI
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .chat-message {
        padding: 1rem;
        margin: 0.5rem 0;
        border-radius: 10px;
        border-left: 4px solid #1f77b4;
    }
    .user-message {
        background-color: #e3f2fd;
        margin-left: 2rem;
    }
    .assistant-message {
        background-color: #f5f5f5;
        margin-right: 2rem;
    }
    .tool-info {
        background-color: #fff3e0;
        padding: 0.5rem;
        border-radius: 5px;
        margin: 0.5rem 0;
        font-size: 0.9rem;
    }
    .error-message {
        background-color: #ffebee;
        color: #c62828;
        padding: 1rem;
        border-radius: 5px;
        margin: 0.5rem 0;
    }
</style>
""", unsafe_allow_html=True)

class BedrockAgent:
    def __init__(self):
        self.system_prompt = [{"text": SYSTEM_PROMPT}]
        self.tool_config = {"tools": [WeatherTool.get_tool_spec(), TimeTool.get_tool_spec()]}
        try:
            import boto3
            self.bedrockRuntimeClient = boto3.client("bedrock-runtime", region_name=AWS_REGION)
            self.use_bedrock = True
        except Exception as e:
            st.warning(f"⚠️ AWS Bedrock not available: {e}. Using simple logic instead.")
            self.bedrockRuntimeClient = None
            self.use_bedrock = False

    def process_conversation(self, conversation: List[Dict[str, Any]], max_recursion: int = MAX_RECURSIONS) -> Dict[str, Any]:
        """
        Process conversation with Bedrock AI, handling tool use and recursion
        """
        if max_recursion <= 0:
            return {"error": "max_recursion", "message": "Maximum recursion reached."}

        try:
            if self.use_bedrock:
                return self._process_with_bedrock(conversation, max_recursion)
            else:
                return self._process_simple_agent(conversation)
        except Exception as e:
            return {"error": "processing_error", "message": str(e)}
    
    def _process_with_bedrock(self, conversation: List[Dict[str, Any]], max_recursion: int) -> Dict[str, Any]:
        """Process using real AWS Bedrock AI"""
        # Send conversation to Bedrock
        bedrock_response = self._send_conversation_to_bedrock(conversation)
        
        # Process the response
        return self._process_model_response(bedrock_response, conversation, max_recursion)

    def _send_conversation_to_bedrock(self, conversation: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Send conversation to Bedrock AI"""
        return self.bedrockRuntimeClient.converse(
            modelId=MODEL_ID,
            messages=conversation,
            system=self.system_prompt,
            toolConfig=self.tool_config,
        )

    def _process_model_response(self, model_response: Dict[str, Any], conversation: List[Dict[str, Any]], max_recursion: int) -> Dict[str, Any]:
        """Process model response and handle tool use"""
        message = model_response["output"]["message"]
        conversation.append(message)

        if model_response["stopReason"] == "tool_use":
            return self._handle_tool_use(message, conversation, max_recursion)
        elif model_response["stopReason"] == "end_turn":
            return {
                "success": True,
                "response": message["content"][0]["text"] if message["content"] else "",
                "conversation": conversation,
                "tool_called": None,  # No tool used in final response
                "tool_input": None,
                "tool_result": None
            }
        else:
            return {
                "success": True,
                "response": "Model response processed",
                "conversation": conversation,
                "tool_called": None,
                "tool_input": None,
                "tool_result": None
            }

    def _handle_tool_use(self, model_response: Dict[str, Any], conversation: List[Dict[str, Any]], max_recursion: int) -> Dict[str, Any]:
        """Handle tool use from model response"""
        tool_results = []
        tool_info = {
            "tool_called": None,
            "tool_input": None,
            "tool_result": None
        }
        
        for content_block in model_response["content"]:
            if "toolUse" in content_block:
                tool_use = content_block["toolUse"]
                tool_response = self._invoke_tool(tool_use)
                
                # Store tool information for display
                tool_info = {
                    "tool_called": tool_use["name"],
                    "tool_input": tool_use.get("input", {}),
                    "tool_result": tool_response["content"]
                }
                
                tool_results.append({
                    "toolResult": {
                        "toolUseId": tool_response["toolUseId"],
                        "content": [{"json": tool_response["content"]}],
                    }
                })

        if tool_results:
            conversation.append({"role": "user", "content": tool_results})
            response = self._send_conversation_to_bedrock(conversation)
            result = self._process_model_response(response, conversation, max_recursion - 1)
            
            # Add tool information to the result
            if result.get("success"):
                result.update(tool_info)
            
            return result
        
        return {"error": "no_tool_use", "message": "No tool use found in response"}
    
    def _process_simple_agent(self, conversation: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Simple agent processing - fallback when Bedrock is not available"""
        if not conversation:
            return {"error": "no_conversation", "message": "No conversation provided"}
        
        # Get the last user message
        last_message = conversation[-1]
        if last_message["role"] != "user":
            return {"error": "invalid_message", "message": "Last message must be from user"}
        
        user_text = last_message["content"][0]["text"]
        
        # Simple fallback logic - just use weather tool for any query
        import uuid
        tool_payload = {"name": "Weather_Tool", "input": {"city": "Bangkok", "cnt": 3}, "toolUseId": str(uuid.uuid4())}
        tool_result = self._invoke_tool(tool_payload)
        
        return {
            "success": True,
            "response": self._format_response(tool_result, tool_payload),
            "tool_called": tool_payload["name"],
            "tool_input": tool_payload.get("input", {}),
            "tool_result": tool_result["content"],
            "show_tool_details": True
        }
    

    def _invoke_tool(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Invoke the specified tool"""
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
    
    def _format_response(self, tool_result: Dict[str, Any], tool_payload: Dict[str, Any]) -> str:
        """Format the tool result into a user-friendly response"""
        tool_name = tool_payload["name"]
        result = tool_result["content"]
        
        if tool_name == "Time_Tool":
            if result.get("error"):
                return f"❌ Error getting time: {result.get('message', 'Unknown error')}"
            return f"🕐 Current time in {result.get('timezone', 'Asia/Bangkok')}: {result.get('current_time', 'N/A')}"
        
        elif tool_name == "Weather_Tool":
            if result.get("error"):
                return f"❌ Error getting weather: {result.get('message', 'Unknown error')}"
            
            weather_data = result.get("weather_data", {})
            
            # Check for API key error
            if "daily_error" in weather_data and weather_data["daily_error"].get("error") == "request_error":
                if "401" in weather_data["daily_error"].get("message", ""):
                    return "❌ **API Key Error:** OpenWeather API key is invalid or expired. Please check your API key configuration."
            
            if "daily_forecast" in weather_data:
                forecast = weather_data["daily_forecast"]
                if "list" in forecast and forecast["list"]:
                    # Format multi-day forecast
                    forecast_text = "🌤️ **พยากรณ์อากาศ 3 วันข้างหน้า:**\n\n"
                    for i, day in enumerate(forecast["list"][:3], 1):
                        temp = day.get("temp", {})
                        weather = day.get("weather", [{}])[0]
                        date = day.get("dt_txt", f"Day {i}")
                        
                        forecast_text += f"**วันที่ {i}:** {weather.get('description', 'N/A')}\n"
                        forecast_text += f"   อุณหภูมิ: {temp.get('day', 'N/A')}°C (สูงสุด {temp.get('max', 'N/A')}°C, ต่ำสุด {temp.get('min', 'N/A')}°C)\n"
                        forecast_text += f"   ความชื้น: {day.get('humidity', 'N/A')}%\n"
                        forecast_text += f"   ความเร็วลม: {day.get('speed', 'N/A')} m/s\n\n"
                    
                    return forecast_text
                else:
                    return "🌤️ Weather data received but no forecast available"
            elif "current_weather" in weather_data:
                current = weather_data["current_weather"]
                if "weather" in current and current["weather"]:
                    weather = current["weather"][0]
                    temp = current.get("main", {}).get("temp", "N/A")
                    feels_like = current.get("main", {}).get("feels_like", "N/A")
                    humidity = current.get("main", {}).get("humidity", "N/A")
                    pressure = current.get("main", {}).get("pressure", "N/A")
                    wind_speed = current.get("wind", {}).get("speed", "N/A")
                    
                    return f"🌤️ **สภาพอากาศปัจจุบัน:** {weather.get('description', 'N/A')}\n" \
                           f"   อุณหภูมิ: {temp}°C (รู้สึกเหมือน {feels_like}°C)\n" \
                           f"   ความชื้น: {humidity}%\n" \
                           f"   ความกดอากาศ: {pressure} hPa\n" \
                           f"   ความเร็วลม: {wind_speed} m/s"
                else:
                    return "🌤️ Current weather data received"
            else:
                return "🌤️ Weather data received"
        
        return "✅ Tool executed successfully"

# Initialize the agent
@st.cache_resource
def get_agent():
    return BedrockAgent()

def main():
    # Header
    st.markdown('<h1 class="main-header">🌤️ RBH Weather AI Agent</h1>', unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        st.header("🔧 Configuration")
        st.info(f"**Model:** {MODEL_ID}")
        st.info(f"**Region:** {AWS_REGION}")
        st.info(f"**Max Recursions:** {MAX_RECURSIONS}")
        
        st.header("🛠️ Available Tools")
        st.write("**Weather Tool**")
        st.write("- Get weather by city name")
        st.write("- Get weather by coordinates")
        st.write("- Daily forecast support")
        
        st.write("**Time Tool**")
        st.write("- Get current time")
        st.write("- Support multiple timezones")
        st.write("- Default: Asia/Bangkok")
        
        st.header("💡 Example Queries")
        st.write("- What's the weather in Bangkok?")
        st.write("- Weather for 13.7563, 100.5018")
        st.write("- What time is it now?")
        st.write("- Time in New York")
        st.write("- สภาพอากาศในอีก 3 วันข้างหน้า ที่บางแสน")
        
        # Tool Execution Log
        st.header("🔧 Tool Execution Log")
        if "tool_log" in st.session_state and st.session_state.tool_log:
            for i, log_entry in enumerate(st.session_state.tool_log[-5:], 1):  # Show last 5 entries
                with st.expander(f"Tool {i}: {log_entry['tool']}"):
                    st.write(f"**Input:** {log_entry['input']}")
                    st.write(f"**Timestamp:** {log_entry['timestamp']}")
        else:
            st.write("No tools executed yet")
        
        # Clear tool log button
        if st.button("🗑️ Clear Tool Log"):
            st.session_state.tool_log = []
            st.rerun()
    
    # Initialize session state
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    if "agent" not in st.session_state:
        st.session_state.agent = get_agent()
    
    if "message_count" not in st.session_state:
        st.session_state.message_count = 0
    
    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            
            # Show tool information if available
            if "tool_info" in message:
                with st.expander("🔧 Tool Details"):
                    st.json(message["tool_info"])
    
    # Chat input
    if prompt := st.chat_input("Ask about weather or time..."):
        # Increment message count
        st.session_state.message_count += 1
        
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Process with agent
        with st.chat_message("assistant"):
            with st.spinner("Processing your request..."):
                try:
                    conversation = [{"role": "user", "content": [{"text": prompt}]}]
                    
                    # Show "Sending query to the model..." like tool_use_demo.py
                    st.info("📤 Sending query to the model...")
                    
                    result = st.session_state.agent.process_conversation(conversation)
                    
                    if result.get("success"):
                        # Show tool execution details if available
                        tool_called = result.get("tool_called")
                        tool_input = result.get("tool_input")
                        
                        if tool_called:
                            # Show tool execution like tool_use_demo.py
                            st.info(f"🔧 Executing tool: {tool_called} with input: {tool_input}")
                            
                            # Add tool execution to sidebar log
                            if "tool_log" not in st.session_state:
                                st.session_state.tool_log = []
                            
                            tool_log_entry = {
                                "tool": tool_called,
                                "input": tool_input,
                                "timestamp": st.session_state.get("message_count", 0)
                            }
                            st.session_state.tool_log.append(tool_log_entry)
                        
                        response = result.get("response", "No response generated")
                        
                        # Show model response like tool_use_demo.py
                        if st.session_state.agent.use_bedrock:
                            st.info("🤖 Model response:")
                        
                        st.markdown(response)
                        
                        # Tool information will be shown in chat history, not here
                        
                        # Add assistant message to chat history
                        message_data = {
                            "role": "assistant", 
                            "content": response
                        }
                        
                        # Add tool info only if tool was used
                        if tool_called:
                            message_data["tool_info"] = {
                                "tool_called": tool_called,
                                "tool_input": tool_input,
                                "raw_result": result.get("tool_result")
                            }
                        
                        st.session_state.messages.append(message_data)
                    else:
                        error_msg = result.get("message", "Unknown error occurred")
                        st.error(f"❌ Error: {error_msg}")
                        st.session_state.messages.append({
                            "role": "assistant", 
                            "content": f"❌ Error: {error_msg}"
                        })
                        
                except Exception as e:
                    error_msg = f"An error occurred: {str(e)}"
                    st.error(f"❌ {error_msg}")
                    st.session_state.messages.append({
                        "role": "assistant", 
                        "content": f"❌ {error_msg}"
                    })
    
    # Clear chat button
    if st.button("🗑️ Clear Chat"):
        st.session_state.messages = []
        st.rerun()

if __name__ == "__main__":
    main()
