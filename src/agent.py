# src/agent.py
import ollama
from prompts.system_prompt import COACH_SYSTEM_PROMPT
from tools import get_telugu_translation, save_user_mistake, review_past_mistakes

AVAILABLE_TOOLS = {
    "get_telugu_translation": get_telugu_translation,
    "save_user_mistake": save_user_mistake,
    "review_past_mistakes": review_past_mistakes 
}

def main():
    print("Welcome to your Autonomous AI English Coach! (Type 'quit' to stop)\n")
    messages = [{"role": "system", "content": COACH_SYSTEM_PROMPT}]

    while True:
        # --- 1. THE USER INPUT LOOP ---
        user_input = input("\nYou: ")
        if user_input.lower() in ['quit', 'exit']:
            break

        messages.append({"role": "user", "content": user_input})

        # --- 2. THE AUTONOMOUS AGENT LOOP ---
        while True:
            # We call Llama 3.2 inside the loop
            response = ollama.chat(
                model="llama3.2",
                messages=messages,
                tools=[get_telugu_translation, save_user_mistake, review_past_mistakes] 
            )

            response_message = response['message']
            messages.append(response_message)

            # 3. EXIT CONDITION: Did the AI output normal text instead of calling tools?
            if not response_message.get('tool_calls'):
                final_reply = response_message.get('content', '')
                print(f"\nCoach:\n{final_reply}")
                break # We break the inner loop, returning to the user input prompt

            # 4. ACTION CONDITION: The AI wants to use one (or multiple) tools
            for tool_call in response_message['tool_calls']:
                tool_name = tool_call['function']['name']
                tool_args = tool_call['function'].get('arguments', {})
                
                print(f"\n[ SYSTEM: Agent decided to use tool '{tool_name}'... ]")
                
                function_to_call = AVAILABLE_TOOLS.get(tool_name)
                
                if function_to_call:
                    try:
                        # Execute the tool
                        tool_result = function_to_call(**tool_args)
                        messages.append({
                            "role": "tool",
                            "content": str(tool_result)
                        })
                    except Exception as e:
                        # Error Handling: If a tool crashes, we tell the AI so it can try again or apologize!
                        messages.append({
                            "role": "tool",
                            "content": f"Error executing tool: {e}"
                        })
                else:
                    messages.append({
                        "role": "tool",
                        "content": f"Error: Tool {tool_name} not found."
                    })
            
            # 5. We DO NOT break here! The loop automatically goes back to the top,
            # sends the new tool results to Llama 3.2, and lets it decide what to do next.
            print("[ SYSTEM: Passing tool results back to the Agent's brain... ]")

if __name__ == "__main__":
    main()

