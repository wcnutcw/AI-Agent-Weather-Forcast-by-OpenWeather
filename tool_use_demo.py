# tool_use_demo.py
from tools.weather_tool import WeatherTool
from tools.time_tool import TimeTool
from tools.output_helper import Output
from bedrock_config import MODEL_ID, SYSTEM_PROMPT, AWS_REGION
import boto3

MAX_RECURSIONS = 5

class ToolUseDemo:
    def __init__(self):
        self.system_prompt = [{"text": SYSTEM_PROMPT}]
        self.tool_config = {"tools": [WeatherTool.get_tool_spec(), TimeTool.get_tool_spec()]}
        self.bedrockRuntimeClient = boto3.client("bedrock-runtime", region_name=AWS_REGION)

    def run(self):
        Output.header()
        conversation = []

        user_input = self._get_user_input()
        while user_input is not None:
            message = {"role": "user", "content": [{"text": user_input}]}
            conversation.append(message)
            bedrock_response = self._send_conversation_to_bedrock(conversation)
            self._process_model_response(bedrock_response, conversation, MAX_RECURSIONS)
            user_input = self._get_user_input()

        Output.footer()

    def _send_conversation_to_bedrock(self, conversation):
        Output.call_to_bedrock(conversation)
        return self.bedrockRuntimeClient.converse(
            modelId=MODEL_ID,
            messages=conversation,
            system=self.system_prompt,
            toolConfig=self.tool_config,
        )

    def _process_model_response(self, model_response, conversation, max_recursion):
        if max_recursion <= 0:
            print("Maximum recursion reached.")
            return

        message = model_response["output"]["message"]
        conversation.append(message)

        if model_response["stopReason"] == "tool_use":
            self._handle_tool_use(message, conversation, max_recursion)
        elif model_response["stopReason"] == "end_turn":
            Output.model_response(message["content"][0]["text"])

    def _handle_tool_use(self, model_response, conversation, max_recursion):
        tool_results = []
        for content_block in model_response["content"]:
            if "text" in content_block:
                Output.model_response(content_block["text"])
            if "toolUse" in content_block:
                tool_response = self._invoke_tool(content_block["toolUse"])
                tool_results.append({
                    "toolResult": {
                        "toolUseId": tool_response["toolUseId"],
                        "content": [{"json": tool_response["content"]}],
                    }
                })

        conversation.append({"role": "user", "content": tool_results})
        response = self._send_conversation_to_bedrock(conversation)
        self._process_model_response(response, conversation, max_recursion - 1)

    def _invoke_tool(self, payload):
        tool_name = payload["name"]
        if tool_name == "Weather_Tool":
            input_data = payload["input"]
            Output.tool_use(tool_name, input_data)
            response = WeatherTool.fetch_weather_data(input_data)
        elif tool_name == "Time_Tool":
            input_data = payload.get("input", {})
            Output.tool_use(tool_name, input_data)
            response = TimeTool.fetch_time_data(input_data)
        else:
            response = {"error": True, "message": f"Tool {tool_name} not found"}
        return {"toolUseId": payload["toolUseId"], "content": response}

    @staticmethod
    def _get_user_input(prompt="Your request"):
        Output.separator()
        user_input = input(f"{prompt} (x to exit): ")
        if user_input.lower() == "x":
            return None
        elif user_input == "":
            return ToolUseDemo._get_user_input("Please enter a request:")
        return user_input

if __name__ == "__main__":
    tool_use_demo = ToolUseDemo()
    tool_use_demo.run()
