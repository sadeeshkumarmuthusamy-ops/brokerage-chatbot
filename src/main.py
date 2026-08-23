# from logging import log
# import sys
# from pathlib import Path

# ROOT = Path(__file__).resolve().parent.parent
# if str(ROOT) not in sys.path:
#     sys.path.insert(0, str(ROOT))

# # from graph.workflow import create_workflow
# from src.api.server import app


# def main():
#     import uvicorn
#     # log.info("Starting the FastAPI server...")
#     uvicorn.run(app, host="127.0.0.1", port=8000)

# if __name__ == "__main__":
#     main()

import multiprocessing
import sys
import time
from pathlib import Path

import uvicorn

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Import your existing FastAPI app and Gradio UI components
# (Adjust these import names to match your actual filenames)
from src.api.server import app as fastapi_app
from src.ui.app_ui import chatbot_ui as gradio_app

def run_api():
    """Target process to run the FastAPI server."""
    uvicorn.run(fastapi_app, host="127.0.0.1", port=8000, log_level="info")

def run_ui():
    """Target process to run the Gradio UI frontend."""
    # Prevent the UI from starting instantly before the API finishes warming up
    time.sleep(1.5) 
    gradio_app.launch(server_name="127.0.0.1", server_port=7860, prevent_thread_lock=False)

if __name__ == "__main__":
    # 1. Initialize distinct process workers
    api_process = multiprocessing.Process(target=run_api, name="FastAPI-Backend")
    ui_process = multiprocessing.Process(target=run_ui, name="Gradio-Frontend")
    
    print("🚀 Starting API and UI services in parallel...")
    
    # 2. Start both execution engines concurrently
    api_process.start()
    ui_process.start()
    
    try:
        # 3. Keep the main process alive while child workers execute tasks
        api_process.join()
        ui_process.join()
    except KeyboardInterrupt:
        print("\n🛑 Shutting down parallel services safely...")
        api_process.terminate()
        ui_process.terminate()
        api_process.join()
        ui_process.join()
        print("✅ System offline.")
