import os
from dotenv import load_dotenv
from brokers.kis_adapter import KISBrokerAdapter

def main():
    # .env 파일 로드
    load_dotenv()
    
    paper_trading = os.getenv("KIS_PAPER_TRADING", "True").lower() == "true"
    
    try:
        adapter = KISBrokerAdapter(paper_trading=paper_trading)
        print(f"=== 한국투자증권 API 연동 테스트 ===")
        print(f"모의투자 모드: {paper_trading}")
        
        # 토큰 발급 테스트
        token = adapter._get_access_token()
        print(f"접근 토큰 발급 성공! (길이: {len(token)})")
        
    except Exception as e:
        print(f"연동 실패: {e}")

if __name__ == "__main__":
    main()
