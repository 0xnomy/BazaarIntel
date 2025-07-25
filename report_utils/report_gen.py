import os
import json
from dotenv import load_dotenv
from langchain_groq import ChatGroq

def explain_seo_issues(metrics, description=None):
    load_dotenv()
    groq_api_key = os.getenv("GROQ_API_KEY")
    llm = ChatGroq(
        model="meta-llama/llama-4-maverick-17b-128e-instruct",
        api_key=groq_api_key,
        temperature=0.2,
        max_tokens=256
    )
    prompt = (
        "Here are the SEO metrics for a product/brand:\n"
        f"{json.dumps(metrics, indent=2)}\n"
        "Please summarize the main SEO strengths and weaknesses in plain English. "
        "Suggest 2-3 actionable improvements."
    )
    if description:
        prompt += f"\nProduct/Brand Description:\n{description}"
    response = llm.invoke(prompt)
    if hasattr(response, 'content'):
        return response.content.strip()
    elif hasattr(response, 'text'):
        return response.text.strip()
    else:
        return str(response).strip()

def generate_report(user_query, seo_data=None, save=False):
    import json
    seo_analytics = seo_data.get("seo_analytics", {}) if seo_data else {}
    query_history = seo_data.get("query_history", []) if seo_data else []
    products = seo_data.get("products", []) if seo_data else []
    # Prepare product summary for prompt
    if products:
        product_lines = []
        for p in products:
            line = f"- {p.get('title', 'No title')} | Price: {p.get('price', 'N/A')} | Desc: {p.get('description', '')[:60]}..."
            product_lines.append(line)
        product_summary = '\n'.join(product_lines)
        product_section = f"\nPRODUCTS SCRAPED (most recent {len(products)}):\n" + product_summary
    else:
        product_section = "\nNo product data available.\n"
    # Extract only avg_scores from seo_analytics
    reduced_seo_analytics = {}
    for brand, data in seo_analytics.items():
        avg_scores = data.get("avg_scores")
        if avg_scores:
            reduced_seo_analytics[brand] = avg_scores
    # Extract only explanation from each query_history entry
    explanations = [q.get("explanation") for q in query_history if q.get("explanation")]
    # Build prompt
    prompt = f"""
You are an e-commerce analytics assistant. The user query is: '{user_query}'

SEO ANALYTICS (avg_scores):\n{json.dumps(reduced_seo_analytics, indent=2)}\n\nQUERY HISTORY EXPLANATIONS:\n{json.dumps(explanations, indent=2)}\n{product_section}

IMPORTANT: When the user asks for the 'best', 'top', or 'most' (e.g., best brand, top product), use the available metrics (such as highest average SEO score, price, or other relevant data) to make a clear, data-driven recommendation or ranking. State your reasoning clearly and concisely. Only say 'I don't know based on the provided data.' if there is truly no way to decide from the context. Do not over-explain or hedge; be direct and actionable.
"""
    # Call LLM (existing logic)
    from langchain_groq import ChatGroq
    import os
    llm = ChatGroq(
        model="meta-llama/llama-4-maverick-17b-128e-instruct",
        api_key=os.getenv("GROQ_API_KEY"),
        temperature=0.2,
        max_tokens=1024
    )
    response = llm.invoke(prompt)
    if hasattr(response, 'content'):
        report = response.content.strip()
    elif hasattr(response, 'text'):
        report = response.text.strip()
    else:
        report = str(response).strip()
    if save:
        with open("result/report.txt", "w", encoding="utf-8") as f:
            f.write(report)
    return report
