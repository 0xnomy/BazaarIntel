from fastapi import APIRouter
import sqlite3
import json
import os
from langchain_groq import ChatGroq
from dotenv import load_dotenv
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from seo_logic import seo_scores

router = APIRouter()

@router.get("/api/brands")
def get_brands():
    with open("scrape_struct.json", "r", encoding="utf-8") as f:
        config = json.load(f)
    # Normalize to title case for consistency
    return [b.strip().title() for b in config.keys()]

load_dotenv()
LLM_MODEL = "meta-llama/llama-4-maverick-17b-128e-instruct"
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

SYSTEM_PROMPT = (
    "You are an expert SEO analyst for the Pakistani e-commerce market. "
    "Given a list of product descriptions for a specific brand, extract a concise, non-redundant set of high-impact SEO keywords and phrases "
    "that would help these products rank in Google and Pakistani e-commerce search. "
    "Focus on product types, materials, styles, and local search intent. "
    "Do not repeat keywords for the same brand. Return only a JSON list of keywords."
)

def get_brand_descriptions():
    conn = sqlite3.connect("products_data.db")
    c = conn.cursor()
    c.execute("SELECT brand, description FROM products WHERE description IS NOT NULL AND description != ''")
    brand_descs = {}
    for brand, desc in c.fetchall():
        norm_brand = brand.strip().title()
        brand_descs.setdefault(norm_brand, []).append(desc)
    conn.close()
    return brand_descs

def extract_keywords_for_brand(brand, descriptions):
    llm = ChatGroq(
        model=LLM_MODEL,
        api_key=GROQ_API_KEY,
        temperature=0.2,
        max_tokens=256
    )
    prompt = (
        f"{SYSTEM_PROMPT}\n\n"
        f"Brand: {brand}\n"
        f"Product Descriptions:\n" +
        "\n".join(f"- {desc}" for desc in descriptions) +
        "\n\nReturn the keywords as a JSON list."
    )
    response = llm.invoke(prompt)
    if hasattr(response, 'content'):
        response_text = response.content
    elif hasattr(response, 'text'):
        response_text = response.text
    else:
        response_text = str(response)
    try:
        keywords = json.loads(response_text)
        if isinstance(keywords, list):
            return keywords
    except Exception:
        import re
        match = re.search(r'\[.*\]', response_text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except Exception:
                pass
    return []

@router.get("/api/seo/keywords")
def seo_keywords():
    brand_descs = get_brand_descriptions()
    # Load cached or generated keywords if available
    if os.path.exists("seo_keywords.json"):
        try:
            with open("seo_keywords.json", "r", encoding="utf-8") as f:
                keyword_map = json.load(f)
        except Exception:
            keyword_map = {}
    else:
        keyword_map = {}
    # Normalize cache keys to title case
    keyword_map = {k.strip().title(): v for k, v in keyword_map.items()}
    result = {}
    for brand, descs in brand_descs.items():
        norm_brand = brand.strip().title()
        # Get keywords (from cache or generate)
        if norm_brand in keyword_map:
            keywords = keyword_map[norm_brand]
        else:
            keywords = extract_keywords_for_brand(norm_brand, descs)
            keyword_map[norm_brand] = keywords
        # Calculate SEO scores for each description
        scores = [seo_scores(desc, norm_brand, keyword_map, descs) for desc in descs]
        # Remove 'commercial_intent' from scores if present
        avg_scores = {k: round(sum(d[k] for d in scores) / len(scores), 2) for k in scores[0]} if scores else {}
        result[norm_brand] = {
            "keywords": keywords,
            "avg_scores": avg_scores,
            "sample_scores": scores[:3]
        }
    # Save updated keywords
    with open("seo_keywords.json", "w", encoding="utf-8") as f:
        json.dump(keyword_map, f, ensure_ascii=False, indent=2)
    # Save the result to outputs/seo_analytics.json
    os.makedirs("output", exist_ok=True)
    with open("output/seo_analytics.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    return result

@router.get("/api/products/count")
def get_product_count():
    conn = sqlite3.connect("products_data.db")
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM products")
    count = c.fetchone()[0]
    conn.close()
    return {"total_products": count}
