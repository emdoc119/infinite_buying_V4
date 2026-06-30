import sys, os
sys.path.append('/root/infinite_bot')
from dotenv import load_dotenv
load_dotenv('/root/infinite_bot/.env')
from brokers.kis_adapter import KISBrokerAdapter
from domain.models import OrderIntent, Side, OrderKind

try:
    paper = os.getenv("KIS_PAPER_TRADING", "true").lower() == "true"
    adapter = KISBrokerAdapter(paper_trading=paper)
    order = OrderIntent(symbol="SOXL", side=Side.BUY, kind=OrderKind.LOC, price=10.0, quantity=1, tag="Test")
    res = adapter.submit_order(order)
    print("Success! ODNO:", res)
except Exception as e:
    print("Error:", str(e))
