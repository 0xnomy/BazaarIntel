# BazaarIntel

BazaarIntel is an AI-powered e-commerce analytics platform for Pakistani fashion brands. It automates data collection, SEO analytics, product analysis, and report generation using dynamic web scraping, LLMs, and agentic workflows.

## Features

- Agentic Workflow (LangGraph + LLaMA 4):
  - Automated pipeline: from user goal to scraping, SEO analysis, data storage, and report generation.
  - Robust planner node extracts brand and step from user goal, even if LLM output is ambiguous.
  - CLI and API integration for agent runs.

- Dynamic Web Scraping:
  - Scrapes product data from multiple brands using Playwright/BeautifulSoup.
  - Handles multiple base URLs per brand, case-insensitive brand matching.
  - Product data stored in SQLite (`products_data.db`).

- SEO Analytics:
  - Extracts and scores SEO keywords for each brand using LLM.
  - Calculates keyword density, content quality, uniqueness, and more.
  - Results saved to `output/seo_analytics.json` and `seo_keywords.json`.

- Interactive Dashboard:
  - Real-time product analytics (charts for price, count, distribution).
  - SEO analytics, brand comparison, and trend visualizations.
  - Agentic SQL/LLM query interface for custom data questions.

- Report Generation:
  - LLM-powered, context-restricted reports (only uses project data, not outside knowledge).
  - Follow-up Q&A and chat-based report generation.
  - Markdown output, rendered in frontend.

## Project Structure

```
bazaarintel/
├── agent/
│   └── agent_graph.py         # LangGraph agent pipeline (main agentic workflow)
├── main.py                    # FastAPI app entrypoint
├── scrapper.py                # Static/dynamic product scraper
├── seo_logic.py               # SEO scoring utilities
├── products_data.db           # SQLite database (products table)
├── output/
│   ├── query_history.json     # LLM query/explanation history
│   └── seo_analytics.json     # SEO analytics per brand
├── report_utils/
│   └── report_gen.py          # LLM-powered report generation
├── routers/
│   ├── agent.py               # Agentic SQL/LLM query API
│   ├── report.py              # Report generation/followup/chat APIs
│   ├── scrape.py              # Scraping API endpoints
│   ├── seo.py                 # SEO analytics API
│   └── trends.py              # Product analytics API
├── templates/
│   ├── dashboard.html         # Main dashboard UI
│   ├── report.html            # Report/chat UI
│   └── seo.html               # SEO analytics UI
├── requirements.txt           # Python dependencies
└── ...
```

## Setup & Installation

1. Clone the repo:
   ```sh
   git clone <repo-url>
   cd bazaarintel
   ```

2. Install dependencies:
   ```sh
   pip install -r requirements.txt
   ```

3. Set up environment variables:
   - Create a `.env` file in the root:
     ```
     GROQ_API_KEY=your_groq_api_key
     ```

4. Ensure SQLite DB exists:
   - The scraper and agent will create/populate `products_data.db` as needed.

## Agentic Workflow (LangGraph)

- Entry: `agent/agent_graph.py`
- How to run:
  ```sh
  python agent/agent_graph.py "Scrape 10 products from khaadi, do their seo and generate a report"
  # Or specify count:
  python agent/agent_graph.py "Scrape Sana Safinaz and generate SEO report" --count 20
  ```
- What happens:
  1. PlannerNode: LLM parses goal, extracts brand/step (robust fallback if LLM fails).
  2. ScrapeNode: Runs `scrapper.py` for the brand/count.
  3. SEOAnalysisNode: Calls SEO extraction/scoring.
  4. StoreDataNode: Verifies DB update.
  5. ReportNode: Generates report using only project data.
  6. EndNode: Workflow complete.
- Logs: CLI prints each step, errors, and final state.

## FastAPI Backend & Frontend

- Start the server:
  ```sh
  uvicorn main:app --reload
  ```
- Access dashboard:
  - Open [http://localhost:8000/dashboard](http://localhost:8000/dashboard)
- APIs:
  - `/api/scrape/{brand}`: Start scraping for a brand (with `count` param)
  - `/api/seo/keywords`: Get/generate SEO analytics
  - `/api/analytics/products`: Product analytics (for dashboard charts)
  - `/api/agent/query`: Agentic SQL/LLM queries
  - `/api/report/deep`: Generate LLM-powered report
  - `/api/report/followup`: Ask follow-up questions on a report
  - `/api/report/chat-generate`: Generate report from chat context

## Frontend Flow

- `dashboard.html`:
  - Brand/product analytics, scraping controls, agentic query UI.
  - Triggers scraping via `/api/scrape/{brand}`.
  - Shows analytics charts (Chart.js) from `/api/analytics/products`.
- `seo.html`:
  - SEO analytics, brand comparison, export, and trends.
  - Calls `/api/seo/keywords` for data.
- `report.html`:
  - Report is auto-generated on load, with chat Q&A for follow-up.
  - Calls `/api/report/deep`, `/api/report/followup`, `/api/report/chat-generate`.

## Database

- `products_data.db`: Main SQLite DB. Table: `products` (brand, title, price, description, ...)
- Populated by scraper and used for all analytics.

## Environment Variables

- `GROQ_API_KEY`: Required for all LLM (Groq/LLaMA 4) calls.

## Extending & Debugging

- Add new brands:
  - Update `scrape_struct.json` and the `known_brands` list in `agent_graph.py`.
- Debug agent:
  - Run `agent/agent_graph.py` directly for step-by-step CLI logs.
- Add new analytics:
  - Extend `routers/trends.py` or `seo_logic.py`.
- Frontend:
  - Edit `templates/` HTML files. All API endpoints are RESTful and return JSON.
- LLM prompt tuning:
  - Prompts are in `report_utils/report_gen.py`, `agent_graph.py`, and routers.

## Output Files

- `output/query_history.json`: LLM query/explanation history
- `output/seo_analytics.json`: SEO analytics per brand
- `result/report.txt`: Last generated report
- `seo_keywords.json`: Brand keyword cache

## Unused/Obsolete Files

- Remove any files not listed above if not referenced in code or templates.

## Support

For issues, open an issue or contact the maintainer.
