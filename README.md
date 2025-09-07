# BazaarIntel

BazaarIntel is an AI-powered e-commerce analytics platform for Pakistani fashion brands. It automates data collection, SEO analytics, product analysis, and report generation using dynamic web scraping, LLMs, and agentic workflows.

![BazaarIntel Dashboard](das.png)

## What It Does

- **Automated Pipeline**: From user goal to scraping, SEO analysis, data storage, and report generation
- **Dynamic Web Scraping**: Scrapes product data from multiple Pakistani fashion brands
- **SEO Analytics**: Extracts and scores SEO keywords using LLM analysis
- **Interactive Dashboard**: Real-time product analytics, brand comparison, and trend visualizations
- **Report Generation**: LLM-powered reports with follow-up Q&A capabilities

## How It Works

1. **Agentic Workflow** (LangGraph + LLaMA 4):
   - Planner node extracts brand and parameters from user goals
   - Automated pipeline: scrape → SEO analysis → data storage → report generation

2. **Data Collection**:
   - Uses Playwright for dynamic web scraping
   - Handles multiple base URLs per brand with case-insensitive matching
   - Stores product data in SQLite database

3. **SEO Analysis**:
   - LLM extracts high-impact keywords and phrases
   - Calculates keyword density, content quality, and uniqueness scores
   - Results cached in JSON files for performance

4. **API Endpoints**:
   - `/api/scrape/{brand}`: Trigger product scraping
   - `/api/seo/keywords`: Generate SEO analytics
   - `/api/analytics/products`: Get product analytics data
   - `/api/report/deep`: Generate comprehensive reports
   - `/api/agent/query`: Agentic SQL/LLM queries

## APIs Used

- **Groq API**: For LLaMA 4 model inference
- **Playwright**: Browser automation for web scraping
- **BeautifulSoup**: HTML parsing and data extraction

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Set up environment variables in `.env`:
   ```
   GROQ_API_KEY=your_groq_api_key
   ```

3. Start the server:
   ```bash
   uvicorn main:app --reload
   ```

4. Access dashboard at `http://localhost:8000`

## Project Structure

```
bazaarintel/
├── agent/agent_graph.py      # LangGraph agent pipeline
├── main.py                   # FastAPI application entrypoint
├── scrapper.py               # Product data scraper
├── seo_logic.py              # SEO scoring utilities
├── routers/                  # API endpoint modules
├── templates/                # HTML dashboard templates
├── report_utils/report_gen.py # LLM-powered report generation
├── products_data.db          # SQLite database
└── output/                   # Generated analytics and reports
```

## MIT License

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
