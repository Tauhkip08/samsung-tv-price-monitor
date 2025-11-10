import os, re, time, logging
from decimal import Decimal
from datetime import datetime
from dotenv import load_dotenv
import requests
from bs4 import BeautifulSoup
import schedule
import smtplib
from email.message import EmailMessage

load_dotenv()

# Configuration
TARGET_PRICE = Decimal("1300.00")
CHECK_INTERVAL_MIN = 180  # every 3 hours
HEADERS = {"User-Agent": "Mozilla/5.0"}
LOGFILE = "price_monitor.log"

logging.basicConfig(filename=LOGFILE, level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(message)s")

PRODUCT_PAGES = {
    "Costco": "https://www.costco.ca/samsung-qn75q8faafxzc-75-qled-q8f-4k-smart-tv.product.html",
    "BestBuy": "https://www.bestbuy.ca/en-ca/product/samsung-qn75q8faafxzc-75-qled-q8f-4k-smart-tv/17123456",
    "Samsung": "https://www.samsung.com/ca/tvs/qled-tv/qn75q8faafxzc/",
    "TheBrick": "https://www.thebrick.com/products/samsung-qn75q8faafxzc-75-qled-q8f-4k-smart-tv",
    "Walmart": "https://www.walmart.ca/en/ip/samsung-qn75q8faafxzc-75-qled-q8f-4k-smart-tv/6000201234567"
}

PRICE_SELECTORS = {
    "Costco": {"css": ".product-price, .price, .priceLarge"},
    "BestBuy": {"css": ".priceView-hero-price .price, .priceSummary .price"},
    "Samsung": {"css": ".product-price, .price, .productPrice"},
    "TheBrick": {"css": ".price, .price-display, .product-price"},
    "Walmart": {"css": ".price-characteristic, .price-group .price"}
}

SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")
TO_EMAIL = os.getenv("TO_EMAIL")

def parse_price(text):
    m = re.search(r"([0-9\.,]+)", text.replace(",", ""))
    return Decimal(m.group(1)) if m else None

def fetch_price(url, store):
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, "lxml")
        selectors = PRICE_SELECTORS.get(store, {}).get("css", "").split(",")
        for sel in selectors:
            el = soup.select_one(sel.strip())
            if el:
                price = parse_price(el.get_text())
                if price:
                    return price
    except Exception as e:
        logging.warning(f"{store} fetch error: {e}")
    return None

def send_email(subject, body):
    try:
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = SMTP_USER
        msg["To"] = TO_EMAIL
        msg.set_content(body)
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as s:
            s.starttls()
            s.login(SMTP_USER, SMTP_PASS)
            s.send_message(msg)
        logging.info("Email sent")
    except Exception as e:
        logging.error(f"Email error: {e}")

def check_prices():
    alerts = []
    for store, url in PRODUCT_PAGES.items():
        price = fetch_price(url, store)
        logging.info(f"{store}: {price}")
        if price and price <= TARGET_PRICE:
            alerts.append(f"{store}: ${price} CAD\n{url}")
    if alerts:
        body = "\n\n".join(alerts)
        send_email("Samsung TV Price Alert", body)

def main():
    check_prices()
    schedule.every(CHECK_INTERVAL_MIN).minutes.do(check_prices)
    while True:
        schedule.run_pending()
        time.sleep(60)

if __name__ == "__main__":
    main()
