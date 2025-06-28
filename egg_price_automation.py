from pathlib import Path

# Create the full updated `egg_price_automation.py` content with debug logging
updated_script = '''#!/usr/bin/env python3
"""
Automated Egg Price Scraper for Raspberry Pi or GitHub Actions
Scrapes NECC egg prices daily and maintains monthly CSV files
"""

import requests
from datetime import datetime
import pandas as pd
from bs4 import BeautifulSoup
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
        try:
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(self.url, headers=headers, timeout=30)
            response.raise_for_status()
            return BeautifulSoup(response.content, "html.parser")
        except Exception as e:
            logger.error(f"Failed to scrape website: {e}")
            raise
    
    def parse_table(self, soup):
        try:
            table = soup.find("table", {"border": "1px"})
            rows = table.find_all("tr")
            data = [[col.get_text(strip=True) for col in row.find_all(["td", "th"])] for row in rows if row]
            df = pd.DataFrame(data[1:], columns=data[0])
            logger.warning(f"🧪 DEBUG: Scraped columns → {df.columns.tolist()}")

            zone_col = [col for col in df.columns if "zone" in col.lower() or "city" in col.lower()]
            if not zone_col:
                raise ValueError("❌ Could not find 'Zone / Day' column dynamically.")
            zone_col = zone_col[0]

            df = df[df[zone_col] != "NECC SUGGESTED EGG PRICES"]
            df = df[df[zone_col] != "Prevailing Prices"]
            df = df[df[zone_col].notna()]
            df.rename(columns={zone_col: "Name Of Zone / Day"}, inplace=True)
            logger.info(f"Parsed {len(df)} city records")
            return df
        except Exception as e:
            logger.error(f"Failed to parse table: {e}")
            raise

    def get_clean_cities(self, df):
        cities = df["Name Of Zone / Day"].dropna().tolist()
        cities = [city for city in cities if "egg price" not in city.lower() and "price" not in city.lower()]
        return sorted(set(cities))
    
    def get_monthly_csv_path(self, date=None):
        if date is None:
            date = datetime.now()
        return self.data_dir / f"egg_prices_{date.year}_{date.month:02d}.csv"

    def update_monthly_csv(self, df, cities):
        today = datetime.now()
        today_col = str(today.day)
        csv_path = self.get_monthly_csv_path(today)

        try:
            city_df = df[df["Name Of Zone / Day"].isin(cities)].copy()
            if csv_path.exists():
                monthly_df = pd.read_csv(csv_path)
                logger.info(f"Loaded existing monthly file: {csv_path}")
                if today_col not in monthly_df.columns:
                    monthly_df[today_col] = "-"
                for _, row in city_df.iterrows():
                    city = row["Name Of Zone / Day"]
                    if "Average" in row and row["Average"] != "-":
                        mask = monthly_df["Name Of Zone / Day"] == city
                        if mask.any():
                            monthly_df.loc[mask, today_col] = row["Average"]
                        else:
                            new_row = {col: "-" for col in monthly_df.columns}
                            new_row["Name Of Zone / Day"] = city
                            new_row[today_col] = row["Average"]
                            monthly_df = pd.concat([monthly_df, pd.DataFrame([new_row])], ignore_index=True)
            else:
                logger.info(f"Creating new monthly file: {csv_path}")
                import calendar
                days = [str(i) for i in range(1, calendar.monthrange(today.year, today.month)[1] + 1)]
                columns = ["Name Of Zone / Day"] + days + ["Average"]
                monthly_data = []
                for city in cities:
                    row = {col: "-" for col in columns}
                    row["Name Of Zone / Day"] = city
                    if city in df["Name Of Zone / Day"].values:
                        avg = df[df["Name Of Zone / Day"] == city]["Average"].values[0]
                        row[today_col] = avg
                    monthly_data.append(row)
                monthly_df = pd.DataFrame(monthly_data)

            def calc_avg(row):
                values = [float(row[str(i)]) for i in range(1, 32) if str(i) in row and row[str(i)] != "-" and pd.notna(row[str(i)])]
                return round(sum(values)/len(values), 2) if values else "-"

            monthly_df["Average"] = monthly_df.apply(calc_avg, axis=1)
            monthly_df.to_csv(csv_path, index=False, encoding="utf-8-sig")
            logger.info(f"Successfully updated monthly CSV: {csv_path}")
            return csv_path

        except Exception as e:
            logger.error(f"Failed to update monthly CSV: {e}")
            raise

    def run_daily_scrape(self):
        try:
            logger.info("Starting daily egg price scraping...")
            soup = self.scrape_website()
            df = self.parse_table(soup)
            cities = self.get_clean_cities(df)
            csv_path = self.update_monthly_csv(df, cities)

            today = datetime.now()
            if "Average" in df.columns:
                result = df[["Name Of Zone / Day", "Average"]].copy()
                result.columns = ["City", "Rate"]
                backup_path = self.data_dir / f"daily_prices_{today.strftime('%Y%m%d')}.csv"
                result.to_csv(backup_path, index=False, encoding="utf-8-sig")
                logger.info(f"Saved daily backup: {backup_path}")

            logger.info("Daily scraping completed successfully!")
            return csv_path
        except Exception as e:
            logger.error(f"Daily scraping failed: {e}")
            raise

def main():
    scraper = EggPriceScraper()
    try:
        path = scraper.run_daily_scrape()
        print(f"✅ Successfully updated: {path}")
    except Exception as e:
        print(f"❌ Scraping failed: {e}")
        return 1
    return 0

if __name__ == "__main__":
    exit(main())
'''

# Save to file
output_path = Path("egg_price_automation.py")
output_path.write_text(updated_script)
output_path.name
