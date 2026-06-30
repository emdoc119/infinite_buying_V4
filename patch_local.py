import re

with open('brokers/kis_adapter.py', 'r') as f:
    content = f.read()

# Replace TR_ID logic
content = re.sub(
    r'tr_id = "VTTS3008U" if intent.side == Side.BUY else "VTTS3009U"\n        else:\n.*?\n            url = f"\{self.base_url\}/uapi/overseas-stock/v1/trading/order"',
    r'tr_id = "VTTS3008U" if intent.side == Side.BUY else "VTTS3009U"\n        else:\n            tr_id = "TTTT1002U" if intent.side == Side.BUY else "TTTT1006U"\n            \n        url = f"{self.base_url}/uapi/overseas-stock/v1/trading/order"',
    content, flags=re.DOTALL
)

# Replace Body logic
body_regex = r'        # 주문 구분 \(LOC: 34, LIMIT: 00\)\n        ord_dvsn = "34" if intent.kind == OrderKind.LOC else "00"\n\n        body = \{\n            "CANO": self.cano,\n            "ACNT_PRDT_CD": self.prdt_cd,\n            "OVRS_EXCG_CD": "NAS", # 나스닥 가정 \(TQQQ, SOXL\)\n            "PDNO": intent.symbol,\n            "ORD_QTY": str\(int\(intent.quantity\)\),\n            "OVRS_ORD_UNPR": str\(round\(intent.price, 2\)\),\n            "ORD_SVR_DVSN_CD": "0",\n            "ORD_DVSN": ord_dvsn\n        \}'

new_body = """        # 주문 구분 (LOC: 34, LIMIT: 00)
        ord_dvsn = "34" if intent.kind == OrderKind.LOC else "00"
        
        if intent.symbol == "SOXL":
            excg_cd = "AMEX"
        elif intent.symbol == "TQQQ":
            excg_cd = "NASD"
        else:
            excg_cd = "NASD"
            
        sll_type = "00" if intent.side == Side.SELL else ""

        body = {
            "CANO": self.cano,
            "ACNT_PRDT_CD": self.prdt_cd,
            "OVRS_EXCG_CD": excg_cd,
            "PDNO": intent.symbol,
            "ORD_QTY": str(int(intent.quantity)),
            "OVRS_ORD_UNPR": f"{intent.price:.2f}",
            "CTAC_TLNO": "",
            "MGCO_APTM_ODNO": "",
            "SLL_TYPE": sll_type,
            "ORD_SVR_DVSN_CD": "0",
            "ORD_DVSN": ord_dvsn
        }"""

content = re.sub(body_regex, new_body, content)

with open('brokers/kis_adapter.py', 'w') as f:
    f.write(content)
