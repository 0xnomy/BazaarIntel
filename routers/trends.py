from fastapi import APIRouter
import sqlite3

router = APIRouter()

@router.get("/api/trends/count")
def product_count_trend():
    conn = sqlite3.connect("products_data.db")
    c = conn.cursor()
    c.execute("SELECT DATE(scraped_date), COUNT(*) FROM products GROUP BY DATE(scraped_date)")
    data = [{"date": row[0], "count": row[1]} for row in c.fetchall()]
    conn.close()
    return data

@router.get("/api/trends/price")
def price_trend():
    conn = sqlite3.connect("products_data.db")
    c = conn.cursor()
    c.execute("SELECT DATE(scraped_date), AVG(price) FROM products GROUP BY DATE(scraped_date)")
    data = [{"date": row[0], "avg_price": row[1]} for row in c.fetchall()]
    conn.close()
    return data

@router.get("/api/analytics/products")
def product_analytics():
    conn = sqlite3.connect("products_data.db")
    c = conn.cursor()
    # Product count and average price per brand
    c.execute("SELECT brand, COUNT(*), AVG(CASE WHEN price IS NOT NULL AND price != '' AND price != 'None' THEN CAST(price AS FLOAT) END) FROM products GROUP BY brand")
    brand_stats = [
        {"brand": row[0], "count": row[1], "avg_price": round(row[2], 2) if row[2] is not None else None}
        for row in c.fetchall()
    ]
    # Price distribution buckets (PKR)
    buckets = [(0, 5000), (5000, 8000), (8000, 10000), (10000, float('inf'))]
    bucket_labels = ["< 5,000", "5,000-8,000", "8,000-10,000", "10,000+"]
    bucket_counts = [0] * len(buckets)
    c.execute("SELECT price FROM products WHERE price IS NOT NULL AND price != '' AND price != 'None'")
    for (price_str,) in c.fetchall():
        try:
            price = float(price_str)
            for i, (low, high) in enumerate(buckets):
                if low <= price < high:
                    bucket_counts[i] += 1
                    break
        except Exception:
            continue
    conn.close()
    return {
        "brand_stats": brand_stats,
        "price_distribution": {
            "labels": bucket_labels,
            "counts": bucket_counts
        }
    } 