# LangSmith evaluations

Add these variables to the repository `.env` file. The evaluator loads that file automatically:

```powershell
LANGSMITH_API_KEY="your-langsmith-key"
LANGSMITH_PROJECT="brokerage-chatbot-evals"
LANGSMITH_DATASET="brokerage-chatbot-smoke"
CHATBOT_API_URL="http://127.0.0.1:8000/api/v1/brokeragent/broker-chat"
```

Set `LANGSMITH_TRACING=true` as well when starting the API if you want LangChain and LangGraph traces sent to the same project.

Start the API, then run the evaluator from the repository root:

```powershell
python evals/langsmith_eval.py
```

The first run creates the `brokerage-chatbot-smoke` dataset. Later runs reuse it and create a new experiment. Add verified expected answers or keywords to `SEED_EXAMPLES` in `langsmith_eval.py` before treating the scores as a quality gate.
