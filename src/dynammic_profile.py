
import ollama
import json
from pydantic import BaseModel

# We import our existing tools and base prompt without modifying the old files
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

# --- NEW IN STEP 10: Mock Database Profile ---
# In a real app, this data would be fetched from your database when the user logs in.
USER_PROFILE = {
    "name": "Surya",
    "native_language": "Telugu",
    "career_goal": "Python/Django Backend Developer & MBA candidate",
    "english_level": "Intermediate",
    "interests": ["Coding challenges", "Database Management", "Software Engineering"]
}

def generate_dynamic_system_prompt(base_prompt: str, profile: dict) -> str:
    """
    Injects the user's database profile into the LLM's system instructions.
    """
    profile_context = f"""
    \n\n--- DYNAMIC USER CONTEXT ---
    Name: {profile['name']}
    Native Language: {profile['native_language']}
    Career Goals: {profile['career_goal']}
    Interests: {', '.join(profile['interests'])}
    
    AGENT INSTRUCTION: 
    You must tailor your examples, vocabulary, and communication practice to this user's 
    specific career goals and interests. When teaching grammar or new words, use sentences 
    related to their field (e.g., programming, business, or their specific interests) so 
    the learning is highly relevant to them.
    ----------------------------
    """
    return base_prompt + profile_context

def trim_memory(messages, max_messages=8):
    if len(messages) > max_messages:
        system_prompt = messages[0]
        recent_messages = messages[-(max_messages - 1):]
        return [system_prompt] + recent_messages
    return messages

def main():
    print("Welcome to Step 10: Personalized AI English Coach! (Type 'quit' to stop)\n")
    
    # --- NEW IN STEP 10: Initialize memory with the DYNAMIC prompt ---
    dynamic_prompt = generate_dynamic_system_prompt(COACH_SYSTEM_PROMPT, USER_PROFILE)
    messages = [{"role": "system", "content": dynamic_prompt}]

    while True:
        messages = trim_memory(messages, max_messages=8)
        
        user_input = input(f"\n{USER_PROFILE['name']}: ") # Personalized input prompt!
        if user_input.lower() in ['quit', 'exit']:
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


