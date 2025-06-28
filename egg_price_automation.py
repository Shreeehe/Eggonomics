from pathlib import Path

# Final and stable version of the egg_price_automation.py script
final_script = '''
#!/usr/bin/env python3

import requests
from datetime import datetime
import pandas as pd
from bs4 import BeautifulSoup
import os
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('egg_scraper.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class EggPriceScraper:
    def __init__(self, data_dir="egg_data"):
        self.url = "https://www.e2necc.com/home/eggprice"
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)

    def scrape_website(self):
        headers = {'User-Agent': 'Mozilla/5.0'}
        try:
            response = requests.get(self.url, headers=headers, timeout=30)
            response.raise_for_status()
            return BeautifulSoup(response.content, "html.parser")
        except Exception as e:
            logger.error(f"Failed to scrape website: {e}")
            raise

    def parse_table(self, soup):
        table = soup.find("table", {"border": "1px"})
        if not table:
            raise ValueError("Table not found")

        rows = table.find_all("tr")
        data = []
        for row in rows:
            cols = row.find_all(["td", "th"])
            cols = [col.get_text(strip=True) for col in cols]
            if cols:
                data.append(cols)

        df = pd.DataFrame(data[1:], columns=data[0])
        logger.info(f"Columns found: {df.columns.tolist()}")

        zone_col = next((col for col in df.columns if "zone" in col.lower() or "city" in col.lower()), None)
        if not zone_col:
            raise ValueError("❌ Could not find a column like 'Name Of Zone / Day'")

        df = df[df[zone_col] != "NECC SUGGESTED EGG PRICES"]
        df = df[df[zone_col] != "Prevailing Prices"]
        df = df[df[zone_col].notna()]
        df.rename(columns={zone_col: "Name Of Zone / Day"}, inplace=True)
        logger.info(f"Parsed {len(df)} city records")
        return df

    def get_clean_cities(self, df):
        cities = df["Name Of Zone / Day"].dropna().tolist()
        cities = [c for c in cities if "price" not in c.lower() and c.strip()]
        return sorted(set(cities))

    def get_monthly_csv_path(self, date=None):
        if date is None:
            date = datetime.now()
        return self.data_dir / f"egg_prices_{date.year}_{date.month:02d}.csv"

    def update_monthly_csv(self, df, cities):
        today = datetime.now()
        today_col = str(today.day)
        csv_path = self.get_monthly_csv_path(today)
        
        if "Name Of Zone / Day" not in df.columns:
            logger.error(f"🚨 Column missing! Available columns: {df.columns.tolist()}")
            raise ValueError("Column 'Name Of Zone / Day' is missing")

        city_df = df[df["Name Of Zone / Day"].isin(cities)].copy()

        price_col = next((col for col in city_df.columns if col != "Name Of Zone / Day"), None)
        if not price_col:
            raise ValueError("❌ No price column found")

        if csv_path.exists():
            monthly_df = pd.read_csv(csv_path)
            logger.info(f"Loaded existing file: {csv_path}")
            if today_col not in monthly_df.columns:
                monthly_df[today_col] = "-"
        else:
            logger.info(f"Creating new monthly file: {csv_path}")
            import calendar
            days = [str(i) for i in range(1, calendar.monthrange(today.year, today.month)[1] + 1)]
            columns = ["Name Of Zone / Day"] + days + ["Average"]
            monthly_df = pd.DataFrame([{col: "-" for col in columns} for _ in cities])
            monthly_df["Name Of Zone / Day"] = cities

        for _, row in city_df.iterrows():
            city = row["Name Of Zone / Day"]
            rate = row[price_col]
            mask = monthly_df["Name Of Zone / Day"] == city
            monthly_df.loc[mask, today_col] = rate

        def calc_avg(row):
            prices = []
            for col in row.index:
                if col.isdigit() and row[col] != "-" and pd.notna(row[col]):
                    try:
                        prices.append(float(row[col]))
                    except:
                        pass
            return round(sum(prices)/len(prices), 2) if prices else "-"

        monthly_df["Average"] = monthly_df.apply(calc_avg, axis=1)
        monthly_df.to_csv(csv_path, index=False, encoding="utf-8-sig")
        logger.info(f"✅ Saved to {csv_path}")
        return csv_path

    def run_daily_scrape(self):
        logger.info("Starting daily scrape...")
        soup = self.scrape_website()
        df = self.parse_table(soup)
        cities = self.get_clean_cities(df)
        return self.update_monthly_csv(df, cities)

def main():
    try:
        scraper = EggPriceScraper()
        path = scraper.run_daily_scrape()
        print(f"✅ Successfully updated: {path}")
    except Exception as e:
        print(f"❌ Scraping failed: {e}")
        return 1
    return 0

if __name__ == "__main__":
    exit(main())
'''

# Save it to file
final_path = Path("/mnt/data/egg_price_automation.py")
final_path.write_text(final_script)
final_path.name
