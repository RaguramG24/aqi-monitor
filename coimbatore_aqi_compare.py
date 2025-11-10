# coimbatore_aqi_compare.py
# Fetches AQI and pollutant data from IQAir & AQI.in for Coimbatore.
# Produces one clean row per run, including Average AQI.

import re
import csv
import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime

CSV_PATH = "aqi_compare.csv"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.google.com/"
}

# --- pollutant regex patterns ---
PATTERNS = {
    "pm25": [r'PM\s*2\.?5\s*[:\u00A0]?\s*([0-9]+(?:\.[0-9]+)?)', r'PM25\s*[:\u00A0]?\s*([0-9]+(?:\.[0-9]+)?)'],
    "pm10": [r'PM\s*10\s*[:\u00A0]?\s*([0-9]+(?:\.[0-9]+)?)', r'PM10\s*[:\u00A0]?\s*([0-9]+(?:\.[0-9]+)?)'],
    "co":   [r'CO\s*[:\u00A0]?\s*([0-9]+(?:\.[0-9]+)?)'],
    "so2":  [r'SO2\s*[:\u00A0]?\s*([0-9]+(?:\.[0-9]+)?)', r'SO\s*2\s*[:\u00A0]?\s*([0-9]+(?:\.[0-9]+)?)'],
    "no2":  [r'NO2\s*[:\u00A0]?\s*([0-9]+(?:\.[0-9]+)?)', r'NO\s*2\s*[:\u00A0]?\s*([0-9]+(?:\.[0-9]+)?)'],
    "o3":   [r'O3\s*[:\u00A0]?\s*([0-9]+(?:\.[0-9]+)?)', r'Ozone\s*[:\u00A0]?\s*([0-9]+(?:\.[0-9]+)?)']
}

def fetch_html(url, timeout=15):
    r = requests.get(url, headers=HEADERS, timeout=timeout)
    r.raise_for_status()
    return r.text

def extract_first_number(txt, regex_list):
    for pat in regex_list:
        m = re.search(pat, txt, re.IGNORECASE)
        if m:
            try:
                return float(m.group(1))
            except Exception:
                mm = re.search(r'([0-9]+(?:\.[0-9]+)?)', m.group(0))
                if mm:
                    return float(mm.group(1))
    return None

# --- IQAir parser ---
def parse_iqair(html):
    soup = BeautifulSoup(html, "html.parser")
    txt = soup.get_text(separator=" ", strip=True)

    m = re.search(r'(\d{1,3})\s*(?:US\s*AQI|Air quality index|AQI)', txt, re.IGNORECASE)
    aqi = int(m.group(1)) if m else None

    return {
        "aqi": aqi,
        "pm25": extract_first_number(txt, PATTERNS["pm25"]),
        "pm10": extract_first_number(txt, PATTERNS["pm10"]),
        "co": extract_first_number(txt, PATTERNS["co"]),
        "so2": extract_first_number(txt, PATTERNS["so2"]),
        "no2": extract_first_number(txt, PATTERNS["no2"]),
        "o3": extract_first_number(txt, PATTERNS["o3"])
    }

# --- AQI.in parser ---
def parse_aqi_in(html):
    soup = BeautifulSoup(html, "html.parser")
    txt = soup.get_text(separator=" ", strip=True)

    m = re.search(r'Live\s*AQI[\s:]*([0-9]{1,3})', txt, re.IGNORECASE) or \
        re.search(r'([0-9]{1,3})\s*\(AQI[- ]?US\)', txt, re.IGNORECASE)
    aqi = int(m.group(1)) if m else None

    return {
        "aqi": aqi,
        "pm25": extract_first_number(txt, PATTERNS["pm25"]),
        "pm10": extract_first_number(txt, PATTERNS["pm10"]),
        "co": extract_first_number(txt, PATTERNS["co"]),
        "so2": extract_first_number(txt, PATTERNS["so2"]),
        "no2": extract_first_number(txt, PATTERNS["no2"]),
        "o3": extract_first_number(txt, PATTERNS["o3"])
    }

# --- Save one clean row per run ---
def summarize_and_append(iqair, aqi_in, csv_path=CSV_PATH):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Compute average AQI
    aqi_values = [v for v in [iqair["aqi"], aqi_in["aqi"]] if isinstance(v, (int, float))]
    avg_aqi = sum(aqi_values)/len(aqi_values) if aqi_values else None

    print(f"\nAQI summary for Coimbatore (fetched {now})\n")
    print(f"- IQAir:  AQI={iqair['aqi']}  PM2.5={iqair['pm25']}  PM10={iqair['pm10']}")
    print(f"- AQI.in: AQI={aqi_in['aqi']}  PM2.5={aqi_in['pm25']}  PM10={aqi_in['pm10']}")
    print(f"\nAverage AQI: {round(avg_aqi,1) if avg_aqi else 'N/A'}\n")

    # Create clean, single-row dataset
    data = {
        "Timestamp": now,
        "IQAir_AQI": iqair["aqi"],
        "IQAir_PM2.5": iqair["pm25"],
        "IQAir_PM10": iqair["pm10"],
        "AQI.in_AQI": aqi_in["aqi"],
        "AQI.in_PM2.5": aqi_in["pm25"],
        "AQI.in_PM10": aqi_in["pm10"],
        "Average_AQI": round(avg_aqi,1) if avg_aqi else ""
    }

    # Append to CSV
    file_exists = os.path.exists(csv_path)
    with open(csv_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(data.keys()))
        if not file_exists:
            writer.writeheader()
        writer.writerow(data)

    print(f"Appended clean record to {csv_path}")

def main():
    urls = {
        "IQAir": "https://www.iqair.com/in-en/india/tamil-nadu/coimbatore",
        "AQI.in": "https://www.aqi.in/dashboard/india/tamil-nadu/coimbatore"
    }

    # Fetch and parse both sites
    try:
        iqair_html = fetch_html(urls["IQAir"])
        iqair_data = parse_iqair(iqair_html)
    except Exception as e:
        print("IQAir fetch/parse error:", e)
        iqair_data = {"aqi": None, "pm25": None, "pm10": None, "co": None, "so2": None, "no2": None, "o3": None}

    try:
        aqi_in_html = fetch_html(urls["AQI.in"])
        aqi_in_data = parse_aqi_in(aqi_in_html)
    except Exception as e:
        print("AQI.in fetch/parse error:", e)
        aqi_in_data = {"aqi": None, "pm25": None, "pm10": None, "co": None, "so2": None, "no2": None, "o3": None}

    summarize_and_append(iqair_data, aqi_in_data)

if __name__ == "__main__":
    main()