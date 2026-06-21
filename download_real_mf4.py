import urllib.request
import ssl

# Bypass SSL certificate checks (sometimes causes issues on corporate networks)
ssl._create_default_https_context = ssl._create_unverified_context

print("Fetching real-world OBD2 data from CSS Electronics GitHub...")

# 1. URL for a real 1MB .mf4 CAN log
mf4_url = "https://raw.githubusercontent.com/CSS-Electronics/canedge-influxdb-writer/master/sample_data/log/958D2219/00002501/00002077.MF4"
# 2. URL for the exact matched standard OBD2 DBC file
dbc_url = "https://raw.githubusercontent.com/CSS-Electronics/canedge-influxdb-writer/master/dbc_files/css-electronics-obd2-v1.4.dbc"

try:
    print("Downloading obd2_log.mf4...")
    urllib.request.urlretrieve(mf4_url, "obd2_log.mf4")
    
    print("Downloading obd2_database.dbc...")
    urllib.request.urlretrieve(dbc_url, "obd2_database.dbc")
    
    print("\nSuccess! Files have been saved to your workspace.")
    print("You are ready to test your plotter.")
except Exception as e:
    print(f"\nDownload failed. Error: {e}")