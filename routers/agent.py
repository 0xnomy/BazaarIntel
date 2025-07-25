from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
import os
import sqlite3
import re
import json
import re
from dotenv import load_dotenv
from langchain.chat_models import init_chat_model

# --- AGENTIC WORKFLOW IMPORT ---
from agent.agent_graph import run_agent

load_dotenv()

router = APIRouter()

groq_api_key = os.getenv("GROQ_API_KEY")
llm = init_chat_model("meta-llama/llama-4-maverick-17b-128e-instruct", model_provider="groq")

DB_PATH = "products_data.db"

STRICT_SQL_PROMPT = (
    "ONLY output a valid SQLite SQL query for this question. "
    "Do NOT explain, do NOT show your reasoning, do NOT output anything except the SQL query. "
    "The table is called 'products'."
)

def get_products_table_columns():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(products);")
    columns = [row[1] for row in cursor.fetchall()]
    conn.close()
    return columns

def extract_first_sql_statement(text):
    # Find the first line that looks like a valid SQL statement
    for line in text.splitlines():
        line = line.strip()
        if re.match(r'^(SELECT|INSERT|UPDATE|DELETE|WITH)\b', line, re.IGNORECASE):
            # If it doesn't end with a semicolon, add one
            if not line.endswith(';'):
                line += ';'
            return line
    # fallback: try to extract a SQL statement ending with a semicolon
    match = re.search(r'(SELECT|INSERT|UPDATE|DELETE|WITH)[^;]+;', text, re.IGNORECASE | re.DOTALL)
    if match:
        return match.group(0)
    return ""

@router.post("/api/agent/query")
async def agent_query(request: Request):
    try:
        data = await request.json()
        user_query = data.get('query', '')
        if not user_query:
            return JSONResponse({'error': 'Query is required'}, status_code=400)
        # Special case: if the user asks for total products, always return COUNT(*)
        if re.search(r"total products|how many products|number of products|count of products", user_query, re.I):
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as total FROM products")
            total = cursor.fetchone()[0]
            conn.close()
            explanation = f"There are {total} products in the database."
            return {'result': [{'total_products': total}], 'explanation': explanation}
        # Get products table columns
        columns = get_products_table_columns()
        columns_str = ", ".join(columns)
        # Prepend columns to the SQL generation prompt
        llm_query = (
            f"The 'products' table has the following columns: {columns_str}\n"
            + STRICT_SQL_PROMPT + "\n" + user_query
        )
        # Get the SQL from the LLM, handling both string and object return types
        if hasattr(llm, 'invoke'):
            sql = llm.invoke(llm_query)
            if hasattr(sql, 'content'):
                sql = sql.content
        else:
            sql = llm(llm_query)
        sql = extract_first_sql_statement(sql)
        if not sql:
            return JSONResponse({'error': 'Could not extract a valid SQL statement from the LLM output.'}, status_code=500)
        print(f"[Agent SQL] {sql}")
        # Actually run the SQL on the real database
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        try:
            cursor.execute(sql)
            rows = cursor.fetchall()
            # Try to get column names
            col_names = [desc[0] for desc in cursor.description] if cursor.description else []
            conn.close()
            # Return as list of dicts if possible
            if col_names:
                result = [dict(zip(col_names, row)) for row in rows]
            else:
                result = rows
            # Generate explanation using the LLM
            plain_text_result = ''
            if isinstance(result, list) and result and isinstance(result[0], dict):
                keys = list(result[0].keys())
                plain_text_result += ' | '.join(keys) + '\n'
                plain_text_result += ' | '.join(['---'] * len(keys)) + '\n'
                for row in result:
                    plain_text_result += ' | '.join(str(row[k]) if row[k] is not None else 'No data' for k in keys) + '\n'
            elif isinstance(result, list):
                plain_text_result = ', '.join(str(x) for x in result)
            elif isinstance(result, dict):
                plain_text_result = '\n'.join(f"{k}: {v}" for k, v in result.items())
            else:
                plain_text_result = str(result)
            explanation_prompt = f"""
You are a data assistant. The user asked: "{user_query}"
The 'products' table has the following columns: {columns_str}
Here is the SQL query that was run: {sql}
Here is the result (as plain text): {plain_text_result}

Write ONLY a concise, plain-English summary of the result for the user.
DO NOT include any reasoning, explanation, or self-talk.
DO NOT say what you are doing—just state the answer.
DO NOT use markdown, bullet points, or numbered lists.
If prices are shown, always refer to them as PKR (Pakistani Rupees).
If a price value is missing or null, say 'No price available'.
Check for the case of the brand name. The user may have used the brand name in a different case.

Example:
Result: [{{'brand': 'Outfitters', 'most_expensive_price': '9990.0'}}, ...]
Summary: Outfitters' most expensive product is PKR 9,990. Sana Safinaz: PKR 9,869. Alkaram Studio: PKR 6,490. Breakout: PKR 5,499. Khaadi: No price available.
"""
            if hasattr(llm, 'invoke'):
                explanation = llm.invoke(explanation_prompt)
                if hasattr(explanation, 'content'):
                    explanation = explanation.content
            else:
                explanation = llm(explanation_prompt)
            explanation = explanation.replace("₹", "PKR ").replace("INR", "PKR")
            explanation = re.sub(r"(?im)^(okay,|i need to|looking at|let me|the user asked|here is|i see|i should|i will|let's|to answer|first,|now,|so,|in summary:|summary:).*?\.\s*", "", explanation)
            explanation = explanation.strip()
            # Save to outputs/query_history.json
            import os, json
            os.makedirs("output", exist_ok=True)
            history_path = "output/query_history.json"
            try:
                with open(history_path, "r", encoding="utf-8") as f:
                    history = json.load(f)
            except Exception:
                history = []
            history.append({
                "query": user_query,
                "sql": sql,
                "result": result,
                "explanation": explanation
            })
            with open(history_path, "w", encoding="utf-8") as f:
                json.dump(history, f, ensure_ascii=False, indent=2)
            return {'result': result, 'explanation': explanation}
        except Exception as e:
            conn.close()
            return JSONResponse({'error': f'SQL execution failed: {e}', 'sql': sql}, status_code=500)
    except Exception as e:
        return JSONResponse({'error': str(e)}, status_code=500)

@router.post("/api/agentic/run")
async def run_agentic(request: Request):
    data = await request.json()
    goal = data.get("goal", "")
    count = int(data.get("count", 50))
    if not goal:
        return JSONResponse({"error": "Goal is required."}, status_code=400)
    result = run_agent(goal, count)
    # Return details (result/result.result is a dict or object)
    report_path = "result/report.txt"
    report = ""
    if os.path.exists(report_path):
        with open(report_path, encoding="utf-8") as f:
            report = f.read()
    return {
        "result": getattr(result, "result", str(result)),
        "brand": getattr(result, "brand", ""),
        "count": getattr(result, "count", 0),
        "goal": getattr(result, "goal", goal),
        "step": getattr(result, "step", ""),
        "report": report
    }

@router.get("/api/agent/schema")
async def get_database_schema():
    """
    Get database schema information to help users understand available data
    """
    try:
        # Get table names
        table_names = db.get_usable_table_names()
        
        schema_info = {}
        for table in table_names:
            # Get table info
            table_info = db.get_table_info([table])
            schema_info[table] = table_info
        
        return {
            "tables": table_names,
            "schema": schema_info,
            "status": "success"
        }
    except Exception as e:
        logger.error(f"Error getting schema: {e}")
        return JSONResponse({
            'error': f'Error retrieving database schema: {str(e)}'
        }, status_code=500)

@router.get("/api/agent/sample-queries")
async def get_sample_queries():
    """
    Provide sample queries to help users understand what they can ask
    """
    sample_queries = [
        "Show me all products with price greater than $100",
        "What are the top 5 most expensive products?",
        "How many products are in each category?",
        "What's the average price of products?",
        "Show me products that contain 'laptop' in the name",
        "Which category has the most products?",
        "What's the price range of products in the electronics category?"
    ]
    
    return {
        "sample_queries": sample_queries,
        "status": "success"
    }