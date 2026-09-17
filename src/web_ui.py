# src/step12_web_ui.py

import streamlit as st
import ollama
from prompts.system_prompt import COACH_SYSTEM_PROMPT

# Import our existing tools without modifying tools.py!
from tools import get_telugu_translation, save_user_mistake, review_past_mistakes

AVAILABLE_TOOLS = {
    "get_telugu_translation": get_telugu_translation,
    "save_user_mistake": save_user_mistake,
    "review_past_mistakes": review_past_mistakes 
}

# 1. UI Configuration
st.set_page_config(page_title="AI English Coach", page_icon="🎓", layout="centered")
st.title("🎓 AI English Communication Coach")
st.caption("Powered by Llama 3.2 and Ollama (Local Execution)")

# 2. Initialize Memory using Streamlit's Session State
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "system", "content": COACH_SYSTEM_PROMPT}]

# 3. Render the existing conversation history to the screen
for msg in st.session_state.messages:
    # We DO NOT want to show the hidden system prompt or raw tool data to the user
    if msg["role"] not in ["system", "tool"]:
        
        # Sometimes the AI sends a blank message when it calls a tool. We hide those.
        if msg["role"] == "assistant" and not msg.get("content"):
            continue
            
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

# 4. Handle User Input
if user_input := st.chat_input("Type your message here..."):
    
    # Immediately show the user's message on the screen
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    # 5. The Autonomous ReAct Loop (Running inside the UI)
    with st.chat_message("assistant"):
        # A dynamic text placeholder so we can show what the bot is doing!
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

            # Exit Condition: No more tools to call
            if not response_message.get('tool_calls'):
                final_reply = response_message.get('content', '')
                status_box.markdown(final_reply) # Replace the "Thinking" text with the final answer!
                break

            # Action Condition: The AI wants to use a tool
            for tool_call in response_message['tool_calls']:
                tool_name = tool_call['function']['name']
                tool_args = tool_call['function'].get('arguments', {})
                
                # Update the UI to tell the user what the agent is doing in the background
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


