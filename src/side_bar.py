# src/step13_fixed_web_agent.py

import streamlit as st
import ollama
import json
import os
from prompts.system_prompt import COACH_SYSTEM_PROMPT

# Reusing our existing tools safely!
from tools import get_telugu_translation, save_user_mistake, review_past_mistakes

AVAILABLE_TOOLS = {
    "get_telugu_translation": get_telugu_translation,
    "save_user_mistake": save_user_mistake,
    "review_past_mistakes": review_past_mistakes 
}

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
    """Loads clean dictionary messages from disk."""
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return []
    return []

# --- THE FIX IS HERE ---
def save_history(messages):
    """
    Sanitizes conversation messages into standard Python dicts 
    before saving, preventing Ollama Message serialization errors.
    """
    history_to_save = []
    
    for msg in messages:
        # Safe extraction whether msg is a dict or an Ollama Message object
        if isinstance(msg, dict):
            role = msg.get("role")
            content = msg.get("content", "")
        else:
            role = getattr(msg, "role", None)
            content = getattr(msg, "content", "")
            
        # We only persist conversational turns with actual text content
        if role in ["user", "assistant"] and content:
            history_to_save.append({
                "role": role,
                "content": content
            })

    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history_to_save, f, indent=4)

def trim_memory(messages, max_messages=12):
    if len(messages) > max_messages:
        sys_prompt = messages[0]
        recent = messages[-(max_messages - 1):]
        return [sys_prompt] + recent
    return messages

# --- UI Setup ---
st.set_page_config(page_title="AI Coach", page_icon="🎓", layout="wide")

# 1. SIDEBAR
with st.sidebar:
    st.header("👤 User Profile")
    st.write(f"**Name:** {USER_PROFILE['name']}")
    st.write(f"**Target Role:** {USER_PROFILE['career_goal']}")
    st.write(f"**Language:** {USER_PROFILE['native_language']}")
    
    st.divider()
    
    if st.button("🗑️ Clear Chat History", use_container_width=True):
        if os.path.exists(HISTORY_FILE):
            os.remove(HISTORY_FILE)
        st.session_state.messages = []
        st.rerun()

st.title("🎓 AI English Communication Coach")

# 2. INITIALIZE & RESTORE MEMORY
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "system", "content": generate_dynamic_system_prompt()}]
    past_history = load_history()
    st.session_state.messages.extend(past_history)

# 3. RENDER CHAT BUBBLES
for msg in st.session_state.messages:
    # Helper to read dict or object attributes safely
    role = msg.get("role") if isinstance(msg, dict) else getattr(msg, "role", "")
    content = msg.get("content") if isinstance(msg, dict) else getattr(msg, "content", "")
    
    if role in ["user", "assistant"] and content:
        with st.chat_message(role):
            st.markdown(content)

# 4. CHAT INPUT & RUNTIME
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

            # Check if there are tool calls
            tool_calls = response_message.get('tool_calls') if isinstance(response_message, dict) else getattr(response_message, 'tool_calls', None)

            if not tool_calls:
                final_reply = response_message.get('content', '') if isinstance(response_message, dict) else getattr(response_message, 'content', '')
                status_box.markdown(final_reply)
                
                # Auto-save clean data
                save_history(st.session_state.messages)
                break

            for tool_call in tool_calls:
                # Handle both dict and object structures for tool_call
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


