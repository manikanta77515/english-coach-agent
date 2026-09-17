# src/step14_multi_agent_dashboard.py

import streamlit as st
import ollama
import json
import os
from pydantic import BaseModel
from prompts.system_prompt import COACH_SYSTEM_PROMPT

# Reusing our existing tools safely
from tools import get_telugu_translation, save_user_mistake, review_past_mistakes

AVAILABLE_TOOLS = {
    "get_telugu_translation": get_telugu_translation,
    "save_user_mistake": save_user_mistake,
    "review_past_mistakes": review_past_mistakes 
}

# --- NEW IN STEP 14: The Evaluator Schema (Agent 2) ---
class EvaluationResult(BaseModel):
    grammar_score: int
    vocabulary_score: int
    fluency_score: int
    detailed_feedback: str
    suggested_practice_topic: str

# --- Backend Config ---
HISTORY_FILE = "chat_history.json"
USER_PROFILE = {
    "name": "Surya",
    "native_language": "Telugu",
    "career_goal": "Python/Django Backend Developer & MBA candidate",
    "interests": ["Coding challenges", "Database Management"]
}

def generate_dynamic_system_prompt():
    context = (
        f"\n\n--- DYNAMIC USER CONTEXT ---\n"
        f"Name: {USER_PROFILE['name']}\n"
        f"Goals: {USER_PROFILE['career_goal']}\n"
        f"Interests: {', '.join(USER_PROFILE['interests'])}\n"
        f"AGENT INSTRUCTION: Tailor examples and practice to this user's profile."
    )
    return COACH_SYSTEM_PROMPT + context

def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return []
    return []

def save_history(messages):
    history_to_save = []
    for msg in messages:
        if isinstance(msg, dict):
            role, content = msg.get("role"), msg.get("content", "")
        else:
            role, content = getattr(msg, "role", None), getattr(msg, "content", "")
            
        if role in ["user", "assistant"] and content:
            history_to_save.append({"role": role, "content": content})

    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history_to_save, f, indent=4)

def trim_memory(messages, max_messages=12):
    if len(messages) > max_messages:
        return [messages[0]] + messages[-(max_messages - 1):]
    return messages

# --- NEW IN STEP 14: The Evaluator Agent Logic ---
def run_background_evaluator(messages):
    """
    Acts as a SECOND AI Agent. It reads the chat history and outputs strict JSON.
    """
    eval_prompt = {
        "role": "system", 
        "content": "You are a strict English Language Assessor. Analyze the user's messages in this conversation. Score their grammar, vocabulary, and fluency out of 10. You MUST respond in valid JSON."
    }
    
    # We strip out system prompts and tools, giving Agent 2 only the raw conversation
    clean_history = []
    for msg in messages:
        role = msg.get("role") if isinstance(msg, dict) else getattr(msg, "role", "")
        content = msg.get("content") if isinstance(msg, dict) else getattr(msg, "content", "")
        if role in ["user", "assistant"] and content:
            clean_history.append({"role": role, "content": content})
            
    response = ollama.chat(
        model="llama3.2",
        messages=[eval_prompt] + clean_history,
        format=EvaluationResult.model_json_schema() # Force JSON output!
    )
    
    # Convert the JSON string from Llama 3.2 into a Python dictionary
    return json.loads(response['message']['content'])


# --- UI Setup ---
st.set_page_config(page_title="AI Coach", page_icon="🎓", layout="wide")

with st.sidebar:
    st.header("👤 User Profile")
    st.write(f"**Name:** {USER_PROFILE['name']}")
    st.write(f"**Target Role:** {USER_PROFILE['career_goal']}")
    
    st.divider()
    
    # --- NEW IN STEP 14: The Trigger for Agent 2 ---
    st.subheader("📈 Performance")
    if st.button("📊 Generate Progress Report", type="primary", use_container_width=True):
        # Prevent evaluation if there is no chat history yet
        if len(st.session_state.messages) < 3:
            st.warning("Chat more with the Coach first!")
        else:
            with st.spinner("Agent 2 is analyzing your English..."):
                try:
                    report = run_background_evaluator(st.session_state.messages)
                    st.success("Report Ready!")
                    
                    # Draw a beautiful UI scoreboard
                    col1, col2, col3 = st.columns(3)
                    col1.metric("Grammar", f"{report['grammar_score']}/10")
                    col2.metric("Vocab", f"{report['vocabulary_score']}/10")
                    col3.metric("Fluency", f"{report['fluency_score']}/10")
                    
                    st.info(f"**Feedback:** {report['detailed_feedback']}")
                    st.warning(f"**Focus On:** {report['suggested_practice_topic']}")
                except Exception as e:
                    st.error(f"Evaluation failed: {e}")

    st.divider()
    
    if st.button("🗑️ Clear Chat History", use_container_width=True):
        if os.path.exists(HISTORY_FILE):
            os.remove(HISTORY_FILE)
        st.session_state.messages = []
        st.rerun()

st.title("🎓 AI English Communication Coach")

# INITIALIZE MEMORY
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "system", "content": generate_dynamic_system_prompt()}]
    st.session_state.messages.extend(load_history())

# RENDER CHAT
for msg in st.session_state.messages:
    role = msg.get("role") if isinstance(msg, dict) else getattr(msg, "role", "")
    content = msg.get("content") if isinstance(msg, dict) else getattr(msg, "content", "")
    if role in ["user", "assistant"] and content:
        with st.chat_message(role):
            st.markdown(content)

# CHAT INPUT (Agent 1: The Coach)
if user_input := st.chat_input(f"Type your message here, {USER_PROFILE['name']}..."):
    
    st.session_state.messages = trim_memory(st.session_state.messages)
    
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        status_box = st.empty()
        status_box.markdown("🤔 *Thinking...*")
        
        while True:
            response = ollama.chat(
                model="llama3.2",
                messages=st.session_state.messages,
                tools=[get_telugu_translation, save_user_mistake, review_past_mistakes]
            )

            response_message = response['message']
            st.session_state.messages.append(response_message)

            tool_calls = response_message.get('tool_calls') if isinstance(response_message, dict) else getattr(response_message, 'tool_calls', None)

            if not tool_calls:
                final_reply = response_message.get('content', '') if isinstance(response_message, dict) else getattr(response_message, 'content', '')
                status_box.markdown(final_reply)
                save_history(st.session_state.messages)
                break

            for tool_call in tool_calls:
                func_data = tool_call.get('function', {}) if isinstance(tool_call, dict) else getattr(tool_call, 'function', {})
                tool_name = func_data.get('name') if isinstance(func_data, dict) else getattr(func_data, 'name', '')
                tool_args = func_data.get('arguments', {}) if isinstance(func_data, dict) else getattr(func_data, 'arguments', {})

                status_box.markdown(f"🛠️ *Using tool: `{tool_name}`...*")
                
                function_to_call = AVAILABLE_TOOLS.get(tool_name)
                if function_to_call:
                    try:
                        tool_result = function_to_call(**tool_args)
                        st.session_state.messages.append({"role": "tool", "content": str(tool_result)})
                    except Exception as e:
                        st.session_state.messages.append({"role": "tool", "content": f"Error: {e}"})
                else:
                    st.session_state.messages.append({"role": "tool", "content": "Error: Tool not found."})



