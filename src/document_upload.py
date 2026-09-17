# src/step15_document_upload.py

import streamlit as st
import ollama
import json
import os
from pydantic import BaseModel
from prompts.system_prompt import COACH_SYSTEM_PROMPT
from tools import get_telugu_translation, save_user_mistake, review_past_mistakes

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

HISTORY_FILE = "chat_history.json"
USER_PROFILE = {
    "name": "Surya",
    "native_language": "Telugu",
    "career_goal": "Python/Django Backend Developer & MBA candidate",
    "interests": ["Coding challenges", "Database Management"]
}

# --- NEW IN STEP 15: We added doc_text parameter ---
def generate_dynamic_system_prompt(doc_text=""):
    context = (
        f"\n\n--- DYNAMIC USER CONTEXT ---\n"
        f"Name: {USER_PROFILE['name']}\n"
        f"Goals: {USER_PROFILE['career_goal']}\n"
        f"Interests: {', '.join(USER_PROFILE['interests'])}\n"
        f"AGENT INSTRUCTION: Tailor examples and practice to this user's profile."
    )
    
    # If a document was uploaded, we inject it directly into the AI's brain!
    if doc_text:
        context += (
            f"\n\n--- UPLOADED DOCUMENT CONTEXT ---\n"
            f"The user has uploaded a relevant document (Resume, Job Description, etc.). "
            f"Use this text to roleplay interviews, give writing feedback, or tailor your coaching:\n\n"
            f"{doc_text}\n"
            f"-----------------------------------"
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

def run_background_evaluator(messages):
    eval_prompt = {
        "role": "system", 
        "content": "You are a strict English Language Assessor. Score grammar, vocabulary, and fluency out of 10 based on the chat. Respond in valid JSON."
    }
    clean_history = []
    for msg in messages:
        role = msg.get("role") if isinstance(msg, dict) else getattr(msg, "role", "")
        content = msg.get("content") if isinstance(msg, dict) else getattr(msg, "content", "")
        if role in ["user", "assistant"] and content:
            clean_history.append({"role": role, "content": content})
            
    response = ollama.chat(
        model="llama3.2",
        messages=[eval_prompt] + clean_history,
        format=EvaluationResult.model_json_schema()
    )
    return json.loads(response['message']['content'])


# --- UI Setup ---
st.set_page_config(page_title="AI Coach", page_icon="🎓", layout="wide")

with st.sidebar:
    st.header("👤 User Profile")
    st.write(f"**Name:** {USER_PROFILE['name']}")
    st.write(f"**Target Role:** {USER_PROFILE['career_goal']}")
    
    st.divider()
    
    # --- NEW IN STEP 15: The File Uploader ---
    st.subheader("📄 Upload Context")
    uploaded_file = st.file_uploader("Upload a Resume or Job Description (.txt)", type=["txt"])
    
    document_content = ""
    if uploaded_file is not None:
        # Read the file contents as text
        document_content = uploaded_file.getvalue().decode("utf-8")
        st.success("Document loaded into Agent memory!")
    
    st.divider()
    
    st.subheader("📈 Performance")
    if st.button("📊 Generate Progress Report", type="primary", use_container_width=True):
        if len(st.session_state.messages) < 3:
            st.warning("Chat more with the Coach first!")
        else:
            with st.spinner("Agent 2 is analyzing..."):
                try:
                    report = run_background_evaluator(st.session_state.messages)
                    st.success("Report Ready!")
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

# --- NEW IN STEP 15: Always update the System Prompt on load! ---
# We do this so that if a user uploads a file midway through a chat, the AI instantly knows about it.
current_system_prompt = generate_dynamic_system_prompt(document_content)

if "messages" not in st.session_state or len(st.session_state.messages) == 0:
    st.session_state.messages = [{"role": "system", "content": current_system_prompt}]
    st.session_state.messages.extend(load_history())
else:
    # Overwrite the old system prompt with the newly generated one!
    st.session_state.messages[0]["content"] = current_system_prompt

# RENDER CHAT
for msg in st.session_state.messages:
    role = msg.get("role") if isinstance(msg, dict) else getattr(msg, "role", "")
    content = msg.get("content") if isinstance(msg, dict) else getattr(msg, "content", "")
    if role in ["user", "assistant"] and content:
        with st.chat_message(role):
            st.markdown(content)

# CHAT INPUT
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


