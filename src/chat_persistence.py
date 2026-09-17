# src/step11_chat_persistence.py

import ollama
import json
import os
from pydantic import BaseModel

# Importing from our completely untouched previous files!
from tools import get_telugu_translation, save_user_mistake, review_past_mistakes
from prompts.system_prompt import COACH_SYSTEM_PROMPT

AVAILABLE_TOOLS = {
    "get_telugu_translation": get_telugu_translation,
    "save_user_mistake": save_user_mistake,
    "review_past_mistakes": review_past_mistakes 
}

class EvaluationResult(BaseModel):
    grammar_score: int
    vocabulary_score: int
    fluency_score: int
    detailed_feedback: str
    suggested_practice_topic: str

USER_PROFILE = {
    "name": "Surya",
    "native_language": "Telugu",
    "career_goal": "Python/Django Backend Developer & MBA candidate",
    "english_level": "Intermediate",
    "interests": ["Coding challenges", "Database Management", "Software Engineering"]
}

# --- NEW IN STEP 11: History Management ---
HISTORY_FILE = "chat_history.json"

def save_history(messages):
    """Saves the conversation to a JSON file, excluding the dynamic system prompt."""
    # List comprehension to keep only user, assistant, and tool messages
    history_to_save = [msg for msg in messages if msg.get("role") != "system"]
    
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history_to_save, f, indent=4)
    print(f"\n[ SYSTEM: Successfully saved {len(history_to_save)} messages to {HISTORY_FILE}. ]")

def load_history():
    """Loads past conversation history from the JSON file."""
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                history = json.load(f)
            print(f"[ SYSTEM: Loaded {len(history)} past messages from your previous session! ]")
            return history
        except json.JSONDecodeError:
            print("[ SYSTEM: History file is corrupted. Starting a fresh session. ]")
    return []
# ------------------------------------------

def generate_dynamic_system_prompt(base_prompt: str, profile: dict) -> str:
    profile_context = f"""
    \n\n--- DYNAMIC USER CONTEXT ---
    Name: {profile['name']}
    Native Language: {profile['native_language']}
    Career Goals: {profile['career_goal']}
    Interests: {', '.join(profile['interests'])}
    
    AGENT INSTRUCTION: 
    Tailor your examples, vocabulary, and communication practice to this user's 
    specific career goals and interests.
    ----------------------------
    """
    return base_prompt + profile_context

def trim_memory(messages, max_messages=12): # Increased to 12 so we can see loaded history!
    if len(messages) > max_messages:
        system_prompt = messages[0]
        recent_messages = messages[-(max_messages - 1):]
        return [system_prompt] + recent_messages
    return messages

def main():
    print("Welcome to Step 11: Persistent AI English Coach! (Type 'quit' to stop)\n")
    
    # 1. Generate the fresh dynamic prompt
    dynamic_prompt = generate_dynamic_system_prompt(COACH_SYSTEM_PROMPT, USER_PROFILE)
    messages = [{"role": "system", "content": dynamic_prompt}]

    # 2. Load past history (if any) and append it to our messages list
    messages.extend(load_history())

    while True:
        messages = trim_memory(messages, max_messages=12)
        
        user_input = input(f"\n{USER_PROFILE['name']}: ")
        
        if user_input.lower() in ['quit', 'exit']:
            # --- NEW IN STEP 11: Save right before the program closes ---
            save_history(messages)
            print("Coach: Great job today! See you next time.")
            break

        messages.append({"role": "user", "content": user_input})
        wants_evaluation = "evaluate" in user_input.lower() or "score" in user_input.lower()

        while True:
            if wants_evaluation:
                response = ollama.chat(
                    model="llama3.2",
                    messages=messages,
                    format=EvaluationResult.model_json_schema(),
                    tools=[get_telugu_translation, save_user_mistake, review_past_mistakes]
                )
            else:
                response = ollama.chat(
                    model="llama3.2",
                    messages=messages,
                    tools=[get_telugu_translation, save_user_mistake, review_past_mistakes] 
                )

            response_message = response['message']
            messages.append(response_message)

            if not response_message.get('tool_calls'):
                final_reply = response_message.get('content', '')
                
                if wants_evaluation:
                    try:
                        eval_data = json.loads(final_reply)
                        print(f"\n=== OFFICIAL EVALUATION FOR {USER_PROFILE['name'].upper()} ===")
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


