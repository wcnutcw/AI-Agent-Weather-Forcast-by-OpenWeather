# tools/output_helper.py
class Output:
    @staticmethod
    def header():
        print("\n" + "="*80)
        print("Welcome to the Amazon Bedrock Tool Use demo!")
        print("="*80)
        print("This assistant provides current weather information for user-specified locations.")
        print("Example queries:")
        print("- What's the weather like in New York?")
        print("- Current weather for latitude 40.70, longitude -74.01")
        print("- To exit, type 'x' and press Enter.\n")

    @staticmethod
    def footer():
        print("\n" + "="*80)
        print("Thank you for using the demo!")
        print("="*80)

    @staticmethod
    def separator(char="-"):
        print(char * 80)

    @staticmethod
    def call_to_bedrock(conversation):
        if "toolResult" in conversation[-1]["content"][0]:
            print("Returning tool response to model...")
        else:
            print("Sending query to the model...")

    @staticmethod
    def tool_use(tool_name, input_data):
        print(f"Executing tool: {tool_name} with input: {input_data}")

    @staticmethod
    def model_response(message):
        print("Model response:")
        print(message)
