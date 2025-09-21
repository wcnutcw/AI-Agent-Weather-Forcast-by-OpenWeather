# RBH Weather AI Agent

A Streamlit-based AI agent that provides weather information and time data using AWS Bedrock and OpenWeather API.

## Features

- 🌤️ **Weather Information**: Get current weather and forecasts by city name or coordinates
- 🕐 **Time Information**: Get current time in various timezones
- 🤖 **AI Agent**: Intelligent tool selection based on user input
- 💬 **Chat Interface**: Interactive chat-based user interface
- 🛠️ **Tool Integration**: Seamless integration with Weather and Time tools

## Prerequisites

- Python 3.12 or higher
- AWS credentials configured (for Bedrock access)
- OpenWeather API key (for weather data)

## Installation

1. Clone or download this repository
2. Install required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up environment variables by creating a `.env` file in the root directory:
   ```env
   AWS_ACCESS_KEY_ID=your_aws_access_key
   AWS_SECRET_ACCESS_KEY=your_aws_secret_key
   REGION_NAME=ap-northeast-1
   API_OPEN_WEATHER=your_openweather_api_key
   ```

## Usage

### Option 1: Using the run script
```bash
python run_streamlit.py
```

### Option 2: Direct Streamlit command
```bash
cd streamlit_app
streamlit run main.py
```

The application will open in your browser at `http://localhost:8501`

## Example Queries

### Time Queries (ภาษาไทย)
- "ตอนนี้กี่โมงแล้ว"
- "เวลาเท่าไหร่"
- "วันนี้วันที่เท่าไหร่"

### Time Queries (English)
- "What time is it now?"
- "Current time"
- "Time in New York"

### Weather Queries (ภาษาไทย)
- "อากาศเป็นอย่างไร"
- "ฝนตกไหม"
- "อุณหภูมิวันนี้"

### Weather Queries (English)
- "What's the weather in Bangkok?"
- "Weather for 13.7563, 100.5018"
- "Temperature today"

## Project Structure

```
RBH_Weather/
├── streamlit_app/
│   └── main.py              # Main Streamlit application
├── backend/
│   └── agent_server.py      # FastAPI backend server
├── tools/
│   ├── weather_tool.py      # Weather tool implementation
│   ├── time_tool.py         # Time tool implementation
│   └── output_helper.py     # Output formatting utilities
├── bedrock_config.py        # AWS Bedrock configuration
├── env_setup.py            # Environment variable setup
├── requirements.txt        # Python dependencies
├── run_streamlit.py        # Run script for Streamlit app
└── README.md              # This file
```

## Tools

### Weather Tool
- Supports city name geocoding
- Supports latitude/longitude coordinates
- Provides daily forecasts (1-16 days)
- Fallback to current weather if forecast unavailable

### Time Tool
- Current time in various timezones
- Default timezone: Asia/Bangkok
- Formatted date and time output

## Configuration

The application uses the following configuration:
- **Model**: Claude 3 Haiku (via AWS Bedrock)
- **Region**: ap-northeast-1
- **Max Recursions**: 5
- **Default Timezone**: Asia/Bangkok

## Recent Improvements

### ✅ Fixed Issues (September 2024)
- **Tool Selection Logic**: Fixed incorrect tool selection for Thai time queries
- **Thai Language Support**: Added proper detection for Thai keywords
- **AWS Bedrock Integration**: Added real AWS Bedrock AI support with fallback to simple logic
- **Output Formatting**: Added proper tool execution display like `tool_use_demo.py`
- **Error Handling**: Improved error messages and user feedback

### 🔧 Tool Selection Logic
The system now properly detects:
- **Time queries**: "ตอนนี้กี่โมงแล้ว", "what time is it", etc. → Time_Tool
- **Weather queries**: "อากาศเป็นอย่างไร", "weather in Bangkok", etc. → Weather_Tool
- **Coordinates**: "13.7563, 100.5018" → Weather_Tool

## Troubleshooting

1. **AWS Credentials**: Ensure your AWS credentials are properly configured
2. **API Keys**: Verify your OpenWeather API key is valid
3. **Dependencies**: Make sure all required packages are installed
4. **Port Conflicts**: If port 8501 is in use, Streamlit will automatically use the next available port
5. **Thai Language**: If Thai queries don't work, check that your system supports UTF-8 encoding



## 📌 Important Notes (One Call 3.0)

If you see this in the JSON:

"daily_error": {
  "error": "unauthorized",
  "status_code": 401,
  "message": "Unauthorized: API key invalid or lacks One Call 3.0 access (One Call by Call subscription required)."
}


or if the reply says "No data", it means:

Your OpenWeather API key does not have access to One Call 3.0

You must subscribe to the "One Call by Call" plan separately

Otherwise, the system will fallback to current weather only



🔔 The application will inform users in Thai:

"ขณะนี้สามารถให้ข้อมูลอากาศปัจจุบันเท่านั้น (ไม่ได้สมัคร One Call 3.0)"

"ฉันขออภัยที่ไม่สามารถให้ข้อมูลการคาดการณ์สภาพอากาศในอนาคตที่บางแสนได้ เนื่องจากฉันไม่มีสิทธิ์เข้าถึงข้อมูลการพยากรณ์อากาศในระยะยาว ซึ่งต้องใช้การสมัครสมาชิกแบบเพิ่มเติม "
