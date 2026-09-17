

import ollama
import json
from pydantic import BaseModel
from prompts.system_prompt import COACH_SYSTEM_PROMPT

# We can safely import our existing tools without modifying tools.py!
from tools import get_telugu_translation, save_user_mistake, review_past_mistakes

AVAILABLE_TOOLS = {
    "get_telugu_translation": get_telugu_translation,
    "save_user_mistake": save_user_mistake,
    "review_past_mistakes": review_past_mistakes 
}

# --- NEW IN STEP 9: Define the Structured Output Schema ---
class EvaluationResult(BaseModel):
    grammar_score: int
    vocabulary_score: int
    fluency_score: int
    detailed_feedback: str
    suggested_practice_topic: str

# Our memory manager from Step 8
def trim_memory(messages, max_messages=8):
    if len(messages) > max_messages:
        system_prompt = messages[0]
        recent_messages = messages[-(max_messages - 1):]
        return [system_prompt] + recent_messages
    return messages

def main():
    print("Welcome to Step 9: Structured Output English Coach! (Type 'quit' to stop)\n")
    messages = [{"role": "system", "content": COACH_SYSTEM_PROMPT}]

    while True:
        messages = trim_memory(messages, max_messages=8)
        
        user_input = input("\nYou: ")
        if user_input.lower() in ['quit', 'exit']:
            break

        messages.append({"role": "user", "content": user_input})
        
        # --- NEW IN STEP 9: Trigger mechanism ---
        # If the user types "evaluate" or "score", we switch to structured mode!
        wants_evaluation = "evaluate" in user_input.lower() or "score" in user_input.lower()

        while True:
            if wants_evaluation:
                # FORCE the model to output JSON based on our Pydantic class
                response = ollama.chat(
                    model="llama3.2",
                    messages=messages,
                    format=EvaluationResult.model_json_schema(), # <--- The Magic Line
                    tools=[get_telugu_translation, save_user_mistake, review_past_mistakes]
                )
            else:
                # Normal chat mode
                response = ollama.chat(
                    model="llama3.2",
                    messages=messages,
                    tools=[get_telugu_translation, save_user_mistake, review_past_mistakes] 
                )

            response_message = response['message']
            messages.append(response_message)

            # Exit condition for the autonomous loop
            if not response_message.get('tool_calls'):
                final_reply = response_message.get('content', '')
                
                # --- NEW IN STEP 9: Parsing the JSON ---
                if wants_evaluation:
                    try:
                        # Convert the JSON string back into a Python dictionary
                        eval_data = json.loads(final_reply)
                        print("\n=== OFFICIAL EVALUATION ===")
                        print(f"Grammar:    {eval_data['grammar_score']}/10")
                        print(f"Vocabulary: {eval_data['vocabulary_score']}/10")
                        print(f"Fluency:    {eval_data['fluency_score']}/10")
                        print(f"Feedback:   {eval_data['detailed_feedback']}")
                        print(f"Next Topic: {eval_data['suggested_practice_topic']}")
                        print("===========================")
                    except json.JSONDecodeError:
                        print(f"\nCoach (Raw Text fallback):\n{final_reply}")
                else:
                    print(f"\nCoach:\n{final_reply}")
                break 

            # Tool execution logic (Same as Step 7/8)
            for tool_call in response_message['tool_calls']:
                tool_name = tool_call['function']['name']
                tool_args = tool_call['function'].get('arguments', {})
                print(f"\n[ SYSTEM: Agent decided to use tool '{tool_name}'... ]")
                
                function_to_call = AVAILABLE_TOOLS.get(tool_name)
                if function_to_call:
                    try:
                        tool_result = function_to_call(**tool_args)
                        messages.append({"role": "tool", "content": str(tool_result)})
                    except Exception as e:
                        messages.append({"role": "tool", "content": f"Error: {e}"})
                else:
                    messages.append({"role": "tool", "content": f"Error: Tool not found."})

if __name__ == "__main__":
    main()


