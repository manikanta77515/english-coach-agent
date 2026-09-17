# Local AI English Communication Agent

An autonomous, multi-agent conversational coaching platform powered locally by **Llama 3.2** and **Ollama**.

## Architecture Highlights
- **Engine:** Llama 3.2 via official Ollama Python SDK (zero cloud dependency, 100% private execution).
- **Core Loop:** ReAct (Reason + Act) autonomous execution loop with multi-tool dispatching.
- **Tools:**
  - `get_telugu_translation`: Word translation support.
  - `save_user_mistake`: Persistent error logging.
  - `review_past_mistakes`: RAG-based error retrieval and personalized quizzing.
- **Memory Management:** Sliding window context truncation protecting system instructions against context overflow.
- **Multi-Agent Evaluation:** Secondary evaluator agent enforcing strict Pydantic JSON schema output for performance scorecards.
- **Interface:** Streamlit web app with dynamic user profile injection, session persistence, and document upload for resume/job description context.

## Setup Instructions

1. **Clone the repository:**
   ```bash
   git clone <your-repo-url>
   cd english-coach-agent

