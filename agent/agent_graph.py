import os
import sys
import json
from dataclasses import dataclass
from langgraph.graph import StateGraph
from langchain_groq import ChatGroq
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from report_utils import report_gen
from routers import scrape as scrape_router
from routers import seo as seo_router
from dotenv import load_dotenv
load_dotenv()
import scrapper
import seo_logic
import subprocess

# --- Path helpers ---
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DB_PATH = os.path.join(BASE_DIR, 'products_data.db')
SEO_ANALYTICS_PATH = os.path.join(BASE_DIR, 'output', 'seo_analytics.json')
QUERY_HISTORY_PATH = os.path.join(BASE_DIR, 'output', 'query_history.json')
REPORT_PATH = os.path.join(BASE_DIR, 'result', 'report.txt')

@dataclass
class BazaarIntelState:
    goal: str
    brand: str = ""
    step: str = ""
    result: str = ""
    count: int = 50

# LLM for planning
llm = ChatGroq(
    model="meta-llama/llama-4-maverick-17b-128e-instruct",
    api_key=os.getenv("GROQ_API_KEY"),
    temperature=0.2,
    max_tokens=512
)

def extract_count_from_goal(goal: str, default: int = 50) -> int:
    import re
    # Look for patterns like 'scrape 10 products', 'scrape 20', etc.
    match = re.search(r"scrape\s+(\d+)", goal, re.I)
    if match:
        return int(match.group(1))
    match = re.search(r"(\d+)\s+products", goal, re.I)
    if match:
        return int(match.group(1))
    return default

def planner_node(state: BazaarIntelState):
    import json, re
    # --- Step 1: Extract brand and count if not set ---
    if not state.brand:
        known_brands = ["khaadi", "outfitters", "sana safinaz", "alkaram", "breakout", "gul ahmed", "nishat", "maria b", "bareeze", "generation"]
        goal_lower = state.goal.lower()
        if "outfitter" in goal_lower and "outfitters" not in goal_lower:
            state.brand = "outfitters"
        else:
            for b in known_brands:
                if b in goal_lower.replace('_', ' ').replace('-', ' '):
                    state.brand = b.replace(' ', '_')
                    break
        if not state.brand:
            match = re.search(r"from ([a-zA-Z0-9_\- ]+)", state.goal, re.I)
            if match:
                state.brand = match.group(1).strip().lower().replace(' ', '_')
    # --- Step 2: Extract count if not set or if default ---
    if not state.count or state.count == 50:
        state.count = extract_count_from_goal(state.goal, default=50)
    # --- Step 3: Determine next step based on current state ---
    # The agentic workflow is: scrape -> seo -> store -> report -> end
    next_step = None
    if not state.step or state.step == "":
        next_step = "scrape" if state.brand else "end"
    elif state.step == "scrape":
        next_step = "seo"
    elif state.step == "seo":
        next_step = "store"
    elif state.step == "store":
        next_step = "report"
    elif state.step == "report":
        next_step = "end"
    else:
        next_step = "end"
    state.step = next_step
    print(f"\n== {state.step.upper()} {state.brand.upper() if state.brand else ''} (count={state.count}) ==")
    return state

def scrape_node(state: BazaarIntelState):
    print(f"[SCRAPE] Scraping {state.count} products for {state.brand.title()}...")
    result = subprocess.run(
        [sys.executable, os.path.join(BASE_DIR, 'scrapper.py'), '--brand', state.brand, '--count', str(state.count)],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"[SCRAPE] ERROR: Scraper failed for {state.brand.title()} (exit code {result.returncode})")
        state.result = f"Scraper failed for {state.brand} (exit code {result.returncode})"
        return state
    print(f"[SCRAPE] Done: {state.count} products scraped for {state.brand.title()}.")
    state.result = f"Scraped products for {state.brand}"
    return state

def seo_node(state: BazaarIntelState):
    print(f"[SEO] Running SEO analysis for {state.brand.title()}...")
    seo_router.seo_keywords()
    print(f"[SEO] SEO analysis complete for {state.brand.title()}.")
    state.result = "SEO analysis complete"
    return state

def store_node(state: BazaarIntelState):
    print(f"[STORE] Verifying data storage...")
    import sqlite3
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM products")
    count = c.fetchone()[0]
    conn.close()
    print(f"[STORE] Data stored: {count} total products in database.")
    state.result = f"Data stored in products_data.db (total products: {count})"
    return state

def report_node(state: BazaarIntelState):
    print(f"[REPORT] Generating report...")
    with open(SEO_ANALYTICS_PATH, "r", encoding="utf-8") as f:
        seo_analytics = json.load(f)
    try:
        with open(QUERY_HISTORY_PATH, "r", encoding="utf-8") as f:
            query_history = json.load(f)
    except Exception:
        query_history = []
    # Fetch products for the brand (most recent N)
    import sqlite3
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM products WHERE brand = ? ORDER BY rowid DESC LIMIT ?", (state.brand, state.count))
    columns = [desc[0] for desc in c.description]
    products = [dict(zip(columns, row)) for row in c.fetchall()]
    conn.close()
    # Pass products to report generator
    report = report_gen.generate_report(state.goal, seo_data={
        "seo_analytics": seo_analytics,
        "query_history": query_history,
        "products": products
    }, save=True)
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"[REPORT] Report generated and saved to result/report.txt.")
    state.result = "Report generated and saved"
    return state

def end_node(state: BazaarIntelState):
    print("\n================ WORKFLOW SUMMARY ================" )
    print(f"Goal: {state.goal}")
    print(f"Brand: {state.brand.title() if state.brand else 'N/A'}")
    print(f"Products Scraped: {state.count}")
    print(f"Final Step: {state.step}")
    print(f"Result: {state.result}")
    print("=================================================")
    state.result = "Agent workflow complete."
    return state

# --- Build the LangGraph ---
graph = StateGraph(BazaarIntelState)
graph.add_node("PlannerNode", planner_node)
graph.add_node("ScrapeNode", scrape_node)
graph.add_node("SEOAnalysisNode", seo_node)
graph.add_node("StoreDataNode", store_node)
graph.add_node("ReportNode", report_node)
graph.add_node("EndNode", end_node)

graph.add_conditional_edges(
    "PlannerNode",
    lambda s: s.step,
    {
        "scrape": "ScrapeNode",
        "seo": "SEOAnalysisNode",
        "store": "StoreDataNode",
        "report": "ReportNode",
        "end": "EndNode"
    }
)

graph.add_edge("ScrapeNode", "PlannerNode")
graph.add_edge("SEOAnalysisNode", "PlannerNode")
graph.add_edge("StoreDataNode", "PlannerNode")
graph.add_edge("ReportNode", "PlannerNode")

graph.set_entry_point("PlannerNode")

agent_graph = graph.compile()

def run_agent(goal: str, count: int = 50):
    """
    Run the agentic workflow for a given goal and product count.
    Example: run_agent("Scrape Sana Safinaz and generate SEO report", count=10)
    This can be called from the dashboard backend.
    """
    state = BazaarIntelState(goal=goal, count=count)
    result = agent_graph.invoke(state)
    print("Final result:", result['result'])
    return result

# Example call:
if __name__ == "__main__":
    import sys
    goal = "Scrape Sana Safinaz and generate SEO report"
    count = 50
    if len(sys.argv) > 1:
        goal = sys.argv[1]
    if len(sys.argv) > 2:
        try:
            count = int(sys.argv[2])
        except Exception:
            pass
    run_agent(goal, count) 