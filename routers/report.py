from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
import os
import json
import sys
from pathlib import Path

# Import the generate_report function from report_utils/report_gen.py
sys.path.append(str(Path(__file__).parent.parent / "report_utils"))
from report_gen import generate_report

router = APIRouter()

@router.post("/api/report/deep")
async def deep_report(request: Request):
    try:
        data = await request.json()
        user_query = data.get("query", "")
        if not user_query:
            return JSONResponse({"error": "Query is required."}, status_code=400)
        # Load the latest outputs
        with open("output/seo_analytics.json", "r", encoding="utf-8") as f:
            seo_analytics = json.load(f)
        with open("output/query_history.json", "r", encoding="utf-8") as f:
            query_history = json.load(f)
        # Fetch latest products from DB (optionally filter by brand in query)
        import sqlite3, re
        conn = sqlite3.connect("products_data.db")
        c = conn.cursor()
        # Try to extract brand from user query
        match = re.search(r"from ([a-zA-Z0-9_\- ]+)", user_query, re.I)
        brand = match.group(1).strip().lower().replace(' ', '_') if match else None
        if brand:
            c.execute("SELECT * FROM products WHERE lower(trim(brand)) = ? ORDER BY rowid DESC LIMIT 20", (brand,))
        else:
            c.execute("SELECT * FROM products ORDER BY rowid DESC LIMIT 20")
        columns = [desc[0] for desc in c.description]
        products = [dict(zip(columns, row)) for row in c.fetchall()]
        conn.close()
        # Pass both SEO analytics, query history, and products to the report generator
        context = {
            "seo_analytics": seo_analytics,
            "query_history": query_history,
            "products": products
        }
        report = generate_report(user_query, seo_data=context, save=False)
        # Save the report to result/report.txt
        os.makedirs("result", exist_ok=True)
        with open("result/report.txt", "w", encoding="utf-8") as f:
            f.write(report)
        return {"report": report}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@router.post("/api/report/followup")
async def report_followup(request: Request):
    import os
    from langchain_groq import ChatGroq
    import json
    data = await request.json()
    report_text = data.get("report", "")
    user_question = data.get("question", "")
    if not report_text or not user_question:
        return JSONResponse({"error": "Report and question are required."}, status_code=400)
    groq_api_key = os.getenv("GROQ_API_KEY")
    llm = ChatGroq(
        model="meta-llama/llama-4-maverick-17b-128e-instruct",
        api_key=groq_api_key,
        temperature=0.2,
        max_tokens=512
    )
    prompt = (
        f"Here is the previous report:\n{report_text}\n\n"
        f"The user asks a follow-up question:\n\"{user_question}\"\n\n"
        "Please answer the follow-up, referencing ONLY the report and any relevant data above. "
        "IMPORTANT: Only use the information provided above. If the answer is not present in the context, reply with: 'I don't know based on the provided data.' Do not use any outside knowledge or make up information not present in the context."
    )
    response = llm.invoke(prompt)
    if hasattr(response, 'content'):
        answer = response.content.strip()
    elif hasattr(response, 'text'):
        answer = response.text.strip()
    else:
        answer = str(response).strip()
    return {"answer": answer}

@router.post("/api/report/chat-generate")
async def chat_generate_report(request: Request):
    import os
    from langchain_groq import ChatGroq
    data = await request.json()
    context = data.get("context", "")
    if not context:
        return JSONResponse({"error": "Chat context is required."}, status_code=400)
    groq_api_key = os.getenv("GROQ_API_KEY")
    llm = ChatGroq(
        model="meta-llama/llama-4-maverick-17b-128e-instruct",
        api_key=groq_api_key,
        temperature=0.2,
        max_tokens=1024
    )
    prompt = (
        "You are an expert e-commerce analytics assistant. The following is a conversation between a user and an AI about e-commerce analytics, SEO, and product data.\n"
        f"Conversation:\n{context}\n\n"
        "Based on this conversation, generate a detailed, plain-English report that answers the user's questions and summarizes the key insights. Reference any relevant SEO scores, analytics, or product data mentioned. Be concise, factual, and actionable.\n"
        "IMPORTANT: Only use the information provided above. If the answer is not present in the context, reply with: 'I don't know based on the provided data.' Do not use any outside knowledge or make up information not present in the context."
    )
    response = llm.invoke(prompt)
    if hasattr(response, 'content'):
        report = response.content.strip()
    elif hasattr(response, 'text'):
        report = response.text.strip()
    else:
        report = str(response).strip()
    return {"report": report} 