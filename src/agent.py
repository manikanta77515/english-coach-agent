# src/agent.py
import ollama
from prompts.system_prompt import COACH_SYSTEM_PROMPT
from tools import get_telugu_translation, save_user_mistake, review_past_mistakes

AVAILABLE_TOOLS = {
    "get_telugu_translation": get_telugu_translation,
    "save_user_mistake": save_user_mistake,
    "review_past_mistakes": review_past_mistakes 
}

def trim_memory(messages, max_messages=4):
    """
    Sliding Window Memory Manager.
    Prevents the conversation history from exceeding the LLM's context window limit.
    """
    # If our history is longer than our limit...
    if len(messages) > max_messages:
        print("\n[ SYSTEM: Memory getting full. Forgetting oldest messages... ]")
        
        # We MUST keep the System Prompt (which is always at index 0).
        system_prompt = messages[0]
        
        # We grab the most recent messages. 
        # (max_messages - 1) ensures we have room to add the system prompt back.
        recent_messages = messages[-(max_messages - 1):]
        
        # Combine them back together
        return [system_prompt] + recent_messages
        
    return messages

def main():
    print("Welcome to your Production-Ready AI English Coach! (Type 'quit' to stop)\n")
    messages = [{"role": "system", "content": COACH_SYSTEM_PROMPT}]

    while True:
        # --- 0. MEMORY MANAGEMENT ---
        # Trim memory BEFORE we ask for user input to ensure we don't crash
        messages = trim_memory(messages, max_messages=8)

        # --- 1. THE USER INPUT LOOP ---
        user_input = input("\nYou: ")
        if user_input.lower() in ['quit', 'exit']:
            break

        messages.append({"role": "user", "content": user_input})

        # --- 2. THE AUTONOMOUS AGENT LOOP ---
        while True:
            response = ollama.chat(
                model="llama3.2",
                messages=messages,
                tools=[get_telugu_translation, save_user_mistake, review_past_mistakes] 
            )

            response_message = response['message']
            messages.append(response_message)

            if not response_message.get('tool_calls'):
                final_reply = response_message.get('content', '')
                print(f"\nCoach:\n{final_reply}")
                break 

            for tool_call in response_message['tool_calls']:
                tool_name = tool_call['function']['name']
                tool_args = tool_call['function'].get('arguments', {})
                
                print(f"\n[ SYSTEM: Agent decided to use tool '{tool_name}'... ]")
                
                function_to_call = AVAILABLE_TOOLS.get(tool_name)
                
                if function_to_call:
                    try:
                        tool_result = function_to_call(**tool_args)
                        messages.append({
                            "role": "tool",
                            "content": str(tool_result)
                        })
                    except Exception as e:
                        messages.append({
                            "role": "tool",
                            "content": f"Error executing tool: {e}"
                        })
                else:
                    messages.append({
                        "role": "tool",
                        "content": f"Error: Tool {tool_name} not found."
                    })
            
            print("[ SYSTEM: Passing tool results back to the Agent's brain... ]")

if __name__ == "__main__":
    main()

