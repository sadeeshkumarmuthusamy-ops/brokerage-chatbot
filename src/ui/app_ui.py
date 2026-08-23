import uuid
import requests
import gradio as gr
from src.config.settings import settings

# Define your running FastAPI endpoint configuration
API_URL = settings.API_URL_PATH
DECISION_URL = f"{API_URL}/decision"

def send_message_to_api(message, history, session_id):
    """Sends the user text input and session ID directly to your FastAPI backend."""
    try:
        payload = {
            "session_id": session_id,
            "text": message,
        }
        response = requests.post(API_URL, json=payload, timeout=60)
        
        if response.status_code == 200:
            api_data = response.json()
            human_in_loop = api_data.get("human_in_loop") is True
            decision_data = api_data.get("decision_data", {})
            summary = decision_data.get("summary", api_data.get("response", ""))
            return (
                api_data.get("response", "⚠️ Error: Missing 'response' key from API response JSON."),
                gr.update(visible=human_in_loop),
                gr.update(value=f"### Approval required\n\n{summary}", visible=human_in_loop),
                gr.update(visible=human_in_loop),
                gr.update(visible=human_in_loop),
                decision_data if human_in_loop else {},
            )
        else:
            return (
                f"⚠️ API Server Error ({response.status_code}): {response.text}",
                gr.update(visible=False),
                gr.update(visible=False),
                gr.update(visible=False),
                gr.update(visible=False),
                {},
            )
            
    except requests.exceptions.ConnectionError:
        return (
            f"⚠️ UI Connection Error: Could not reach the API at {API_URL}. Is your FastAPI app running?",
            gr.update(visible=False),
            gr.update(visible=False),
            gr.update(visible=False),
            gr.update(visible=False),
            {},
        )


def submit_decision(session_id, decision_data, decision, history):
    """Send the user's approval decision to the API."""
    history = list(history or [])
    try:
        response = requests.post(
            DECISION_URL,
            json={
                "session_id": session_id,
                "query": decision_data.get("query", ""),
                "sql": decision_data.get("sql", decision_data.get("generated_sql", "")),
                "decision": decision,
                "decision_data": decision_data or {},
            },
            timeout=30,
        )
        if response.status_code == 200:
            result = response.json()
            decision_text = (
                f"Decision API response: {result.get('status', decision)}\n\n"
                f"Query: {result.get('query', decision_data.get('query', ''))}\n"
                f"SQL: {result.get('sql', decision_data.get('sql', ''))}\n"
                f"Rows updated: {result.get('rows_updated', 'Not executed')}"
            )
            history.append({"role": "assistant", "content": decision_text})
            return (
                history,
                gr.update(visible=True),
                gr.update(value=f"Decision submitted: {decision}", visible=True),
                gr.update(visible=False),
                gr.update(visible=False),
                {},
            )
        return (
            history,
            gr.update(visible=True),
            gr.update(value=f"Decision failed ({response.status_code}).", visible=True),
            gr.update(visible=True),
            gr.update(visible=True),
            decision_data,
        )
    except requests.RequestException:
        return (
            history,
            gr.update(visible=True),
            gr.update(value="Could not submit the decision.", visible=True),
            gr.update(visible=True),
            gr.update(visible=True),
            decision_data,
        )

# 4. Initialize a persistent unique session ID for this browser tab session
def generate_session():
    return str(uuid.uuid4())

# 5. Build a conversational chat layout interface using Gradio Blocks
with gr.Blocks(theme=gr.themes.Soft()) as chatbot_ui:
    # Invisible internal state storage engine to keep the session_id safe across messages
    session_state = gr.State(value=generate_session)
    
    gr.HTML("<h1 style='text-align: center; font-weight: 700;'>Brokerage Chatbot</h1>")
    gr.Markdown("Type your questions below. Chatbot will help you with details")
    
    # Visualizes the ongoing conversation history logs inside an interactive interface window
    chatbot_window = gr.Chatbot(
        label="Chat Conversation",
        layout="bubble",
        buttons=["copy_all"],
    )

    decision_data_state = gr.State(value={})
    with gr.Group(visible=False) as approval_panel:
        approval_summary = gr.Markdown()
        with gr.Row():
            approve_button = gr.Button("Approve", variant="primary", visible=False)
            reject_button = gr.Button("Reject", variant="stop", visible=False)
    
    # Interactive chat layout structure
    gr.ChatInterface(
        fn=send_message_to_api,
        chatbot=chatbot_window,
        additional_inputs=[session_state], # Passes the session_id into our connection function automatically
        additional_outputs=[approval_panel, approval_summary, approve_button, reject_button, decision_data_state],
        textbox=gr.Textbox(placeholder="Ask a question (e.g., 'get me all the vendors in USA')...", container=False, scale=7),
    )

    approve_button.click(
        fn=lambda session_id, decision_data, history: submit_decision(session_id, decision_data, "approved", history),
        inputs=[session_state, decision_data_state, chatbot_window],
        outputs=[chatbot_window, approval_panel, approval_summary, approve_button, reject_button, decision_data_state],
    )
    reject_button.click(
        fn=lambda session_id, decision_data, history: submit_decision(session_id, decision_data, "rejected", history),
        inputs=[session_state, decision_data_state, chatbot_window],
        outputs=[chatbot_window, approval_panel, approval_summary, approve_button, reject_button, decision_data_state],
    )

# 6. Launch the frontend UI service layer globally
if __name__ == "__main__":
    # Boots up on default frontend port 7860 to completely avoid clashing with port 8000
    chatbot_ui.launch(server_name="127.0.0.1", server_port=7860)
