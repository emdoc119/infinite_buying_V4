import sys, os
sys.path.append('/root/infinite_bot')
from dotenv import load_dotenv
load_dotenv('/root/infinite_bot/.env')

from brokers.kis_adapter import KISBrokerAdapter
from datetime import date

try:
    adapter = KISBrokerAdapter(paper_trading=False)
    fills = adapter.get_fills("SOXL", date.today())
    print("Fills retrieved successfully:")
    print(fills)
except Exception as e:
    print("Error retrieving fills:")
    print(str(e))
