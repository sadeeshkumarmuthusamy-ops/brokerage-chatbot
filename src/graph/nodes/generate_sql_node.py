from src.config.settings import settings
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from src.languagemodels.llmprovider import get_llm_instance
from src.rag.schema_retrival import get_relevant_schemas
from src.graph.state.agentstate import AgentState


def generate_sql_from_question(state: AgentState) -> AgentState:
    """Generates SQL query from a natural language question using RAG approach."""
    if state.get("is_input_safe") is False:
        print(f"Input safety check failed for question: '{state.get('user_query', '')}'. Aborting SQL generation.")
        return {"user_query": state.get("user_query", ""), "sql_error": "Input safety check failed."}
    
    question = state.get("user_query", "")
    sql_query = state.get("generated_sql", "")
    sql_errors = state.get("sql_error", "")

    if sql_errors and sql_query:
        print(f"SQL errors detected: {sql_errors}. Retrying SQL generation for question '{question}'.")
        user_prompt = f"""Previous SQL generation attempt resulted in errors: {sql_errors}. 
        previous SQL query: {sql_query}. Please generate a corrected SQL query for the following question: '{question}'."""
    else:
        user_prompt = f"Natural Language Query: {question}\n\nGenerated SQL:"

    context = get_relevant_schemas(question, num_tables=4)
    sql_generation_prompt = ChatPromptTemplate.from_messages([
        ("system", (
            "You are an expert SQL engineer. Your task is to generate valid SQL statements "
            "based ONLY on the provided database table schemas and a natural language query.\n\n"
            "### RULES:\n"
            "1. Return ONLY the raw SQL code. Do not wrap it in markdown code blocks like ```sql.\n"
            "2. Only use the tables and columns explicitly defined in the context below.\n"
            "3. Pay close attention to PRIMARY KEY and FOREIGN KEY notes to perform accurate joins.\n\n"
            "### DATABASE SCHEMA CONTEXT:\n{schema_context}"
        )),
        ("human", user_prompt)
    ])

    if not context.strip():
        return {"user_query": question}

    llm = get_llm_instance(settings.GROQ_LLM_PROVIDER)
    sql_chain = sql_generation_prompt | llm | StrOutputParser()

    sql_query = sql_chain.invoke({
        "schema_context": context,
        "user_query": question
    })
    print(f"Generated SQL query for question '{question}':\n{sql_query}")
    return {
        "user_query": question,
        "db_schema": context,
        "generated_sql": sql_query,
        "sql_error": "",
    }