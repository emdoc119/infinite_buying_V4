import os
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from services.notifier import notifier

scheduler = AsyncIOScheduler()

async def daily_briefing_job():
    from app import cycles, strategy
    import httpx
    
    print("[Scheduler] 일일 브리핑 작업을 실행합니다.")
    
    for cycle_id, state in cycles.items():
        if state.status not in ["RUNNING", "REVERSE_MODE"]:
            continue
            
        try:
            # 실시간 가격(또는 종가)을 로컬 서버에서 가져오기
            async with httpx.AsyncClient() as client:
                res = await client.get(f"http://127.0.0.1:8081/api/orders/today?cycle_id={cycle_id}")
                if res.status_code != 200:
                    continue
                
                data = res.json()
                orders = data.get("orders", [])
                name_to_show = f"[{state.params.name}] {state.params.symbol.value}" if state.params.name else state.params.symbol.value
                
                if not orders:
                    orders_summary = "오늘 생성될 주문이 없습니다."
                else:
                    lines = []
                    for o in orders:
                        lines.append(f"- [{o['kind']}] {o['quantity']}주 {o['tag']} @ ${o['price']:.2f}")
                    orders_summary = "\n".join(lines)
                
                await notifier.send_briefing_async(
                    symbol=name_to_show,
                    cycle_id=cycle_id,
                    orders_summary=orders_summary,
                    cash=f"{state.cash_remaining:.2f}",
                    current_t=state.T
                )
        except Exception as e:
            print(f"[Scheduler] 브리핑 에러 ({cycle_id}): {e}")

async def morning_sync_job():
    from app import cycles
    import httpx
    
    print("[Scheduler] 아침 체결 동기화 작업을 실행합니다.")
    for cycle_id, state in cycles.items():
        if state.status not in ["RUNNING", "REVERSE_MODE"]:
            continue
            
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                res = await client.post(f"http://127.0.0.1:8081/api/action/auto_sync?cycle_id={cycle_id}")
                
                if res.status_code == 200:
                    data = res.json()
                    message = data.get("message", "동기화 완료 (내용 없음)")
                else:
                    message = f"에러: {res.text}"
                    
                name_to_show = f"[{state.params.name}] {state.params.symbol.value}" if state.params.name else state.params.symbol.value
                await notifier.send_sync_report_async(
                    symbol=name_to_show,
                    sync_message=message,
                    cash=f"{state.cash_remaining:.2f}",
                    current_t=state.T
                )
        except Exception as e:
            print(f"[Scheduler] 아침 동기화 에러 ({cycle_id}): {e}")

async def auto_trade_job():
    from app import cycles, strategy
    import os
    from brokers.kis_adapter import KISBrokerAdapter
    import yfinance as yf
    from decimal import Decimal
    
    print("[Scheduler] 자동 매매(Auto Trade) 작업을 실행합니다.")
    paper_trading = os.getenv("KIS_PAPER_TRADING", "True").lower() == "true"
    adapter = KISBrokerAdapter(paper_trading=paper_trading)
    
    for cycle_id, state in cycles.items():
        if state.status not in ["RUNNING", "REVERSE_MODE"]:
            continue
        if not getattr(state.params, "is_auto_mode", False):
            continue
            
        try:
            symbol = state.params.symbol.value
            name_to_show = f"[{state.params.name}] {symbol}" if state.params.name else symbol
            
            # 1. 오늘 주문이 이미 존재하는지 확인
            if adapter.check_today_orders_exist(symbol):
                print(f"[Scheduler] {name_to_show} 오늘 주문이 이미 존재합니다. 자동 매매를 건너뜁니다.")
                continue
                
            # 2. 가격 데이터 및 주문 생성
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="5d")
            hist = hist.dropna(subset=['Close'])
            if hist.empty:
                continue
                
            ref_price = Decimal(str(hist.iloc[-1]['Close']))
            buy_orders = strategy.build_buy_orders(state, ref_price)
            sell_orders = strategy.build_sell_orders(state)
            all_orders = buy_orders + sell_orders
            
            if not all_orders:
                continue
                
            # 3. KIS API 전송
            success_count = 0
            fail_count = 0
            for order in all_orders:
                try:
                    adapter.submit_order(order)
                    success_count += 1
                except Exception as e:
                    fail_count += 1
                    print(f"자동 주문 실패: {e}")
                    
            msg = f"🤖 [자동 매매 전송 완료]\n- 전송 성공: {success_count}건\n- 실패: {fail_count}건"
            await notifier.send_briefing_async(
                symbol=name_to_show,
                cycle_id=cycle_id,
                orders_summary=msg,
                cash=f"{state.cash_remaining:.2f}",
                current_t=state.T
            )
        except Exception as e:
            print(f"[Scheduler] 자동 매매 에러 ({cycle_id}): {e}")

def start_scheduler():
    trigger_briefing = CronTrigger(hour=22, minute=0, timezone="Asia/Seoul")
    scheduler.add_job(daily_briefing_job, trigger=trigger_briefing, id="daily_briefing", replace_existing=True)
    
    trigger_sync = CronTrigger(hour=9, minute=30, timezone="Asia/Seoul")
    scheduler.add_job(morning_sync_job, trigger=trigger_sync, id="morning_sync", replace_existing=True)
    
    trigger_auto = CronTrigger(hour=22, minute=30, timezone="Asia/Seoul")
    scheduler.add_job(auto_trade_job, trigger=trigger_auto, id="auto_trade", replace_existing=True)
    
    scheduler.start()
    print("[Scheduler] 스케줄러가 시작되었습니다. (매일 22:00 브리핑, 22:30 자동주문, 09:30 체결 동기화)")
