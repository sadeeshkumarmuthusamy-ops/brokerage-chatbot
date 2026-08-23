import uuid
import requests
import gradio as gr

# Define your running FastAPI endpoint configuration
API_URL = "http://127.0.0.1:8000/api/v1/brokeragent/broker-chat"

def send_message_to_api(message, history, session_id):
    """Sends the user text input and session ID directly to your FastAPI backend."""
    # 1. Match your exact API payload keys
    # 2. Fire the network request to your running server
    try:
        payload = {
            "session_id": session_id,
            "text": message,
        }
        response = requests.post(API_URL, json=payload, timeout=60)
        
        if response.status_code == 200:
            # 3. Handle the incoming output key from the API
            api_data = response.json()
            return api_data.get("response", "⚠️ Error: Missing 'response' key in API response JSON.")
        else:
            return f"⚠️ API Server Error ({response.status_code}): {response.text}"
            
    except requests.exceptions.ConnectionError:
        return f"⚠️ UI Connection Error: Could not reach the API at {API_URL}. Is your FastAPI app running?"

# 4. Initialize a persistent unique session ID for this browser tab session
def generate_session():
    return str(uuid.uuid4())

# 5. Build a conversational chat layout interface using Gradio Blocks
with gr.Blocks(theme=gr.themes.Soft()) as chatbot_ui:
    # Invisible internal state storage engine to keep the session_id safe across messages
    session_state = gr.State(value=generate_session)
    
    gr.Markdown("Brokerage Chatbot")
    gr.Markdown("Type your questions below. Chatbot will help you with details")
    
    # Visualizes the ongoing conversation history logs inside an interactive interface window
    chatbot_window = gr.Chatbot(
        label="Chat Conversation",
        layout="bubble",
        buttons=["copy_all"],
    )
    
    # Interactive chat layout structure
    gr.ChatInterface(
        fn=send_message_to_api,
        chatbot=chatbot_window,
        additional_inputs=[session_state], # Passes the session_id into our connection function automatically
        textbox=gr.Textbox(placeholder="Ask a question (e.g., 'get me all the vendors in USA')...", container=False, scale=7),
    )

# 6. Launch the frontend UI service layer globally
if __name__ == "__main__":
    # Boots up on default frontend port 7860 to completely avoid clashing with port 8000
    chatbot_ui.launch(server_name="127.0.0.1", server_port=7860)
