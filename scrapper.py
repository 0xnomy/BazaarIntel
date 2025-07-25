import asyncio
import platform
from playwright.async_api import async_playwright
import csv
import json
import re
from datetime import datetime
import sqlite3
import logging
import time
import os
from bs4 import BeautifulSoup
import argparse


SCROLL_COUNT = 3
SCROLL_WAIT = 2000 
EXTRA_SCROLL_WAIT = 1000  
DYNAMIC_WAIT = 5000 
SELECTOR_WAIT = 15000  
MAX_PRODUCTS = 50
FALLBACK_SELECTORS = [
    'a.is--href-replaced',
    'a[href*="/products/"]'
]

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

if platform.system() == "Windows":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

def clean_text(text: str) -> str:
    if not text:
        return ""
    return re.sub(r'\s+', ' ', text.strip())

def clean_price(price_text: str):
        if not price_text:
            return None
        price_clean = re.sub(r'PKR\s*', '', price_text.strip())
        price_clean = re.sub(r'[^\d.]', '', price_clean)
        if price_clean:
            try:
                return float(price_clean)
            except ValueError:
                numbers = re.findall(r'\d+\.?\d*', price_text)
                if numbers:
                    try:
                        return float(numbers[0])
                    except ValueError:
                        pass
        logger.warning(f"Could not parse price: {price_text}")
        return None

def load_config(config_path='scrape_struct.json'):
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)

async def extract_fields_from_product_page(page, product_page_conf):
    data = {}
    # Special logic for Khaadi: concatenate product-brand and product-name
    if 'khaadi' in page.url or 'khaadi' in (await page.title()).lower():
        brand_div = await page.query_selector('div.product-brand')
        name_h1 = await page.query_selector('h1.product-name')
        brand_text = clean_text(await brand_div.text_content()) if brand_div else ''
        name_text = clean_text(await name_h1.text_content()) if name_h1 else ''
        data['name'] = f"{brand_text} {name_text}".strip()
    else:
        # Name
        if 'name_selector' in product_page_conf:
            el = await page.query_selector(product_page_conf['name_selector'])
            if el:
                data['name'] = clean_text(await el.text_content())
    # Price
    if 'price_selector' in product_page_conf:
        el = await page.query_selector(product_page_conf['price_selector'])
        if el:
            data['price'] = clean_price(await el.text_content())
    # Description
    if 'description_selector' in product_page_conf:
        el = await page.query_selector(product_page_conf['description_selector'])
        if el:
            desc_html = await el.inner_html()
            # For Alkaram, remove disclaimer div if present
            if 'alkaram' in page.url or 'alkaramstudio' in page.url:
                soup = BeautifulSoup(desc_html, 'html.parser')
                disclaimer_div = soup.find('div', class_='tab--disclaimer')
                if disclaimer_div:
                    disclaimer_div.decompose()
                desc_text = soup.get_text(separator=' ', strip=True)
                data['description'] = clean_text(desc_text)
            else:
                data['description'] = clean_text(BeautifulSoup(desc_html, 'html.parser').get_text(separator=' ', strip=True))
    # Specifications (if any)
    if 'specifications_selector' in product_page_conf and 'spec_fields' in product_page_conf:
        spec_els = await page.query_selector_all(product_page_conf['specifications_selector'])
        for el in spec_els:
            text = clean_text(await el.text_content())
            for label, key in product_page_conf['spec_fields'].items():
                if label.lower() in text.lower():
                    data[key] = text
    # Material in description
    if product_page_conf.get('material_in_description') and 'description' in data:
        match = re.search(r'Material:?\s*([\w\s,]+)', data['description'], re.IGNORECASE)
        if match:
            data['material'] = match.group(1).strip()
    return data

async def robust_goto(page, url, max_retries=3, backoff=2):
    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"Navigating to {url} (attempt {attempt})")
            await page.goto(url, wait_until='domcontentloaded', timeout=60000)
            return True
        except Exception as e:
            logger.warning(f"Failed to load {url} (attempt {attempt}): {e}")
            if attempt < max_retries:
                await page.wait_for_timeout(backoff * 1000 * attempt)
            else:
                logger.error(f"Giving up on {url} after {max_retries} attempts.")
                return False

def log_scrape_status(i, total, url, success=True):
    if success:
        logger.info(f"Scraped product {i+1}/{total} from {url}")
    else:
        logger.warning(f"Failed to scrape product {url}")

DISCLAIMER_TEXT = (
    "Disclaimer: Due to the difference in lighting used during photoshoots, the color or texture of the actual product may slightly vary from the image."
)

def save_to_sqlite(data, filename):
    if not data:
        logger.warning("No data to save to SQLite")
        return
    filtered_data = []
    for row in data:
        desc = row.get('description', '').strip()
        if desc.startswith(DISCLAIMER_TEXT):
            logger.info("Skipping product with only disclaimer as description.")
            continue
        filtered_data.append(row)
    if not filtered_data:
        logger.warning("No valid data to save to SQLite after filtering disclaimers.")
        return
    conn = sqlite3.connect(filename)
    c = conn.cursor()
    # Dynamically create columns based on all keys
    all_keys = sorted({k for d in filtered_data for k in d.keys()})
    columns = ', '.join([f'"{k}" TEXT' for k in all_keys])
    c.execute(f'CREATE TABLE IF NOT EXISTS products ({columns})')
    # Add new columns if needed
    existing_cols = set(row[1] for row in c.execute('PRAGMA table_info(products)').fetchall())
    for k in all_keys:
        if k not in existing_cols:
            c.execute(f'ALTER TABLE products ADD COLUMN "{k}" TEXT')
    for row in filtered_data:
        placeholders = ', '.join(['?'] * len(all_keys))
        values = [str(row.get(k, '')) for k in all_keys]
        try:
            c.execute(f'INSERT INTO products ({', '.join([f'"{k}"' for k in all_keys])}) VALUES ({placeholders})', values)
        except Exception as e:
            logger.warning(f"Failed to insert row into SQLite: {e}")
    conn.commit()
    conn.close()
    logger.info(f"Data saved to SQLite database: {filename}")

async def scrape_brand(brand_name, config, browser, max_products=50):
    brand_conf = config[brand_name]
    base_urls = brand_conf['base_url']
    if isinstance(base_urls, str):
        base_urls = [base_urls]
    scraped_data = []
    failed_urls = []
    for base_url in base_urls:
        if len(scraped_data) >= max_products:
            break
        page = await browser.new_page()
        loaded = await robust_goto(page, base_url)
        if not loaded:
            failed_urls.append(base_url)
            await page.close()
            continue
        product_listing = brand_conf['product_listing']
        product_card_selector = product_listing['product_card_selector']
        product_link_attribute = product_listing['product_link_attribute']
        try:
            # Unified scroll logic
            if brand_name in ['khaadi', 'outfitters', 'breakout']:
                for _ in range(SCROLL_COUNT):
                    await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                    await page.wait_for_timeout(SCROLL_WAIT)
                    await page.wait_for_timeout(EXTRA_SCROLL_WAIT)  # Extra 1 second wait
            try:
                await page.wait_for_selector(product_card_selector, timeout=SELECTOR_WAIT)
            except Exception:
                logger.warning(f"Timeout waiting for selector '{product_card_selector}' on {base_url}")
            await page.wait_for_timeout(DYNAMIC_WAIT)
            selectors_to_try = [product_card_selector] + FALLBACK_SELECTORS
            cards = []
            for selector in selectors_to_try:
                cards = await page.query_selector_all(selector)
                if cards:
                    logger.info(f"Using selector '{selector}' found {len(cards)} cards on {base_url}")
                    break
                else:
                    logger.warning(f"No product cards found for selector '{selector}' on {base_url}")
            if not cards:
                logger.error(f"No product cards found for any selector on {base_url}")
            product_urls = set()
            for card in cards:
                try:
                    if product_link_attribute == 'parent_a_href':
                        parent_a = await card.evaluate_handle('el => el.closest("a")')
                        if parent_a:
                            href = await parent_a.get_property('href')
                            href_val = await href.json_value() if href else None
                            if href_val:
                                product_urls.add(href_val)
                    else:
                        href = await card.get_attribute(product_link_attribute) if product_link_attribute else await card.get_attribute('href')
                        if href:
                            if href.startswith('http'):
                                product_urls.add(href)
                            else:
                                from urllib.parse import urljoin
                                product_urls.add(urljoin(base_url, href))
                except Exception as e:
                    logger.warning(f"Error extracting product URL: {e}")
            # Only scrape up to the remaining needed products
            remaining = max_products - len(scraped_data)
            product_urls = list(product_urls)[:remaining]
            logger.info(f"Collected {len(product_urls)} unique product URLs on {base_url} (remaining needed: {remaining}).")
            for i, product_url in enumerate(product_urls):
                try:
                    prod_page = await browser.new_page()
                    loaded = await robust_goto(prod_page, product_url)
                    if not loaded:
                        failed_urls.append(product_url)
                        await prod_page.close()
                        log_scrape_status(i, len(product_urls), product_url, success=False)
                        continue
                    try:
                        data = await extract_fields_from_product_page(prod_page, brand_conf['product_page'])
                        data['url'] = product_url
                        data['brand'] = brand_conf['brand']
                        scraped_data.append(data)
                        log_scrape_status(i, len(product_urls), product_url, success=True)
                    except Exception as e:
                        logger.warning(f"Failed to extract fields for {product_url}: {e}")
                        failed_urls.append(product_url)
                        log_scrape_status(i, len(product_urls), product_url, success=False)
                    await prod_page.close()
                except Exception as e:
                    logger.warning(f"Failed to scrape product {product_url}: {e}")
                    failed_urls.append(product_url)
                    log_scrape_status(i, len(product_urls), product_url, success=False)
            await page.close()
        except Exception as e:
            logger.error(f"Error collecting product URLs for {brand_conf['brand']}: {e}")
            await page.close()
    if scraped_data:
        save_to_sqlite(scraped_data, 'products_data.db')
    return scraped_data, failed_urls

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--brand', type=str, help='Brand name to scrape')
    parser.add_argument('--count', type=int, default=50, help='Number of products to fetch')
    args = parser.parse_args()
    config = load_config()
    print("Available brands:", ', '.join(config.keys()))
    brand_name = args.brand
    if brand_name:
        brand_name = brand_name.strip().lower().replace(' ', '_')
    if not brand_name:
        brand_name = input("Enter brand name to scrape: ").strip().lower().replace(' ', '_')
    if brand_name not in config:
        print(f"Brand '{brand_name}' not found in config.")
        return
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=[
            '--no-sandbox',
            '--disable-dev-shm-usage',
            '--disable-gpu',
            '--disable-web-security',
            '--disable-features=VizDisplayCompositor',
            '--disable-background-timer-throttling',
            '--disable-backgrounding-occluded-windows',
            '--disable-renderer-backgrounding'
        ])
        data, failed_urls = await scrape_brand(brand_name, config, browser, max_products=args.count)
        logger.info(f"Total products scraped: {len(data)}")
        print(f"Total products scraped: {len(data)}")
        # Write scrape status for UI
        with open("scrape_status.json", "w") as f:
            json.dump({"brand": brand_name, "count": len(data), "finished": True, "timestamp": datetime.utcnow().isoformat() + 'Z'}, f)
        if failed_urls:
            logger.error(f"Failed URLs ({len(failed_urls)}):\n" + '\n'.join(failed_urls))
        else:
            logger.info("All URLs scraped successfully.")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
