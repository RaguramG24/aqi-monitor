# coimbatore_aqi_compare.py
# Fetches AQI & pollutant data (IQAir + AQI.in) for Coimbatore,
# computes an average AQI, appends one clean row per run to aqi_compare.csv,
# and prints the absolute path where the CSV is saved (useful for GitHub Actions).

import re
import csv
import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime

CSV_PATH = "aqi_compare.csv"  # MUST be repository-root relative
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.google.com/"
}

# --- simple pollutant patterns (captures numeric values) ---
PATTERNS = {
    "pm25": [r'PM\s*2\.?5\s*[:\u00A0]?\s*([0-9]+(?:\.[0-9]+)?)', r'PM25\s*[:\u00A0]?\s*([0-9]+(?:\.[0-9]+)?)'],
    "pm10": [r'PM\s*10\s*[:\u00A0]?\s*([0-9]+(?:\.[0-9]+)?)', r'PM10\s*[:\u00A0]?\s*([0-9]+(?:\.[0-9]+)?)'],
    "co":   [r'CO\s*[:\u00A0]?\s*([0-9]+(?:\.[0-9]+)?)'],
    "so2":  [r'SO2\s*[:\u00A0]?\s*([0-9]+(?:\.[0-9]+)?)', r'SO\s*2\s*[:\u00A0]?\s*([0-9]+(?:\.[0-9]+)?)'],
    "no2":  [r'NO2\s*[:\u00A0]?\s*([0-9]+(?:\.[0-9]+)?)', r'NO\s*2\s*[:\u00A0]?\s*([0-9]+(?:\.[0-9]+)?)'],
    "o3":   [r'O3\s*[:\u00A0]?\s*([0-9]+(?:\.[0-9]+)?)', r'Ozone\s*[:\u00A0]?\s*([0-9]+(?:\.[0-9]+)?)']
}

def fetch_html(url, timeout=15):
    resp = requests.get(url, headers=HEADERS, timeout=timeout)
    resp.raise_for_status()
    return resp.text

def extract_first_number(txt, regex_list):
    for pat in regex_list:
        m = re.search(pat, txt, re.IGNORECASE)
        if m:
            try:
                return float(m.group(1))
            except Exception:
                # fallback: pull any number from the matched text
                mm = re.search(r'([0-9]+(?:\.[0-9]+)?)', m.group(0))
                if mm:
                    return float(mm.group(1))
    return None

# --- parsers for each site ---
def parse_iqair(html):
    soup = BeautifulSoup(html, "html.parser")
    txt = soup.get_text(separator=" ", strip=True)

    aqi = None
    m = re.search(r'(\d{1,3})\s*(?:US\s*AQI|Air quality index|AQI)', txt, re.IGNORECASE)
    if m:
        try:
            aqi = int(m.group(1))
        except:
            aqi = None

    return {
        "aqi": aqi,
        "pm25": extract_first_number(txt, PATTERNS["pm25"]),
        "pm10": extract_first_number(txt, PATTERNS["pm10"]),
        "co": extract_first_number(txt, PATTERNS["co"]),
        "so2": extract_first_number(txt, PATTERNS["so2"]),
        "no2": extract_first_number(txt, PATTERNS["no2"]),
        "o3": extract_first_number(txt, PATTERNS["o3"])
    }

def parse_aqi_in(html):
    soup = BeautifulSoup(html, "html.parser")
    txt = soup.get_text(separator=" ", strip=True)

    aqi = None
    m = re.search(r'Live\s*AQI[\s:]*([0-9]{1,3})', txt, re.IGNORECASE) or \
        re.search(r'([0-9]{1,3})\s*\(AQI[- ]?US\)', txt, re.IGNORECASE) or \
        re.search(r'(\d{1,3})\s*(?:AQI|AQI-US|AQI \(US\))', txt, re.IGNORECASE)
    if m:
        try:
            aqi = int(m.group(1))
        except:
            aqi = None

    return {
        "aqi": aqi,
        "pm25": extract_first_number(txt, PATTERNS["pm25"]),
        "pm10": extract_first_number(txt, PATTERNS["pm10"]),
        "co": extract_first_number(txt, PATTERNS["co"]),
        "so2": extract_first_number(txt, PATTERNS["so2"]),
        "no2": extract_first_number(txt, PATTERNS["no2"]),
        "o3": extract_first_number(txt, PATTERNS["o3"])
    }

def summarize_and_append(iqair, aqi_in, csv_path=CSV_PATH):
    now_iso = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # compute average from available AQIs
    aqi_vals = [v for v in (iqair.get("aqi"), aqi_in.get("aqi")) if isinstance(v, (int, float))]
    avg = round(sum(aqi_vals)/len(aqi_vals), 1) if aqi_vals else ""

    # prepare one clean row for this run
    row = {
        "Timestamp": now_iso,
        "IQAir_AQI": iqair.get("aqi") or "",
        "IQAir_PM2.5": iqair.get("pm25") or "",
        "IQAir_PM10": iqair.get("pm10") or "",
        "AQIin_AQI": aqi_in.get("aqi") or "",
        "AQIin_PM2.5": aqi_in.get("pm25") or "",
        "AQIin_PM10": aqi_in.get("pm10") or "",
        "Average_AQI": avg
    }

    # Print summary to console (visible in Action logs)
    print("\nAQI summary for Coimbatore (fetched {})\n".format(now_iso))
    print(f"- IQAir:  AQI={row['IQAir_AQI']}  PM2.5={row['IQAir_PM2.5']}  PM10={row['IQAir_PM10']}")
    print(f"- AQI.in: AQI={row['AQIin_AQI']}  PM2.5={row['AQIin_PM2.5']}  PM10={row['AQIin_PM10']}")
    print(f"\nAverage AQI: {row['Average_AQI']}\n")

    # Make sure CSV is written to the repository working directory
    # Print absolute path for troubleshooting / GitHub Actions
    abs_path = os.path.abspath(csv_path)
    print("Saving CSV to:", abs_path)

    # Append single-row-per-run, create file with header if missing
    file_exists = os.path.exists(csv_path)
    with open(csv_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(row.keys()))
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)

    print("Appended clean record to", csv_path)

def main():
    urls = {
        "IQAir": "https://www.iqair.com/in-en/india/tamil-nadu/coimbatore",
        "AQI.in": "https://www.aqi.in/dashboard/india/tamil-nadu/coimbatore"
    }

    # IQAir
    try:
        h = fetch_html(urls["IQAir"])
        iqair = parse_iqair(h)
    except Exception as e:
        print("IQAir fetch/parse error:", e)
        iqair = {"aqi": None, "pm25": None, "pm10": None, "co": None, "so2": None, "no2": None, "o3": None}

    # AQI.in
    try:
        h = fetch_html(urls["AQI.in"])
        aqi_in = parse_aqi_in(h)
    except Exception as e:
        print("AQI.in fetch/parse error:", e)
        aqi_in = {"aqi": None, "pm25": None, "pm10": None, "co": None, "so2": None, "no2": None, "o3": None}

    summarize_and_append(iqair, aqi_in, csv_path=CSV_PATH)

if __name__ == "__main__":
    main()
