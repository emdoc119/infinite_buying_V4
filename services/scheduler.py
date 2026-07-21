import os
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from services.notifier import notifier

scheduler = AsyncIOScheduler()

async def get_active_cycles():
    import httpx
    try:
        async with httpx.AsyncClient() as client:
            res = await client.get("http://127.0.0.1:8081/api/cycles")
            if res.status_code == 200:
                data = res.json()
                return data.get("cycles", [])
    except Exception as e:
        print(f"[Scheduler] API 통신 에러: {e}")
    return []

async def daily_briefing_job():
    import httpx
    print("[Scheduler] 일일 브리핑 작업을 실행합니다.")
    
    cycles = await get_active_cycles()
    for c in cycles:
        cycle_id = c["cycle_id"]
        name_to_show = f"[{c['name']}] {c['symbol']}" if c.get("name") else c["symbol"]
        
        try:
            async with httpx.AsyncClient() as client:
                res = await client.get(f"http://127.0.0.1:8081/api/orders/today?cycle_id={cycle_id}")
                if res.status_code != 200:
                    continue
                
                data = res.json()
                orders = data.get("orders", [])
                
                if not orders:
                    orders_summary = "오늘 생성될 주문이 없습니다."
                else:
                    lines = []
                    for o in orders:
                        lines.append(f"- [{o['kind']}] {o['quantity']}주 {o['tag']} @ ${o['price']:.2f}")
                    orders_summary = "\n".join(lines)
                
                # 상태 조회
                state_res = await client.get(f"http://127.0.0.1:8081/api/cycle?cycle_id={cycle_id}")
                if state_res.status_code == 200:
                    state_data = state_res.json()
                    cash = state_data.get("cash_remaining", "0")
                    current_t = state_data.get("T", 0.0)
                    
                    await notifier.send_briefing_async(
                        symbol=name_to_show,
                        cycle_id=cycle_id,
                        orders_summary=orders_summary,
                        cash=f"{float(cash):.2f}",
                        current_t=current_t
                    )
        except Exception as e:
            print(f"[Scheduler] 브리핑 에러 ({cycle_id}): {e}")

async def morning_sync_job():
    import httpx
    print("[Scheduler] 아침 체결 동기화 작업을 실행합니다.")
    
    cycles = await get_active_cycles()
    for c in cycles:
        cycle_id = c["cycle_id"]
        name_to_show = f"[{c['name']}] {c['symbol']}" if c.get("name") else c["symbol"]
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                res = await client.post(f"http://127.0.0.1:8081/api/action/auto_sync?cycle_id={cycle_id}")
                
                if res.status_code == 200:
                    data = res.json()
                    message = data.get("message", "동기화 완료 (내용 없음)")
                else:
                    message = f"에러: {res.text}"
                    
                state_res = await client.get(f"http://127.0.0.1:8081/api/cycle?cycle_id={cycle_id}")
                cash = "0"
                current_t = 0.0
                if state_res.status_code == 200:
                    state_data = state_res.json()
                    cash = state_data.get("cash_remaining", "0")
                    current_t = state_data.get("T", 0.0)
                    
                await notifier.send_sync_report_async(
                    symbol=name_to_show,
                    sync_message=message,
                    cash=f"{float(cash):.2f}",
                    current_t=current_t
                )
        except Exception as e:
            print(f"[Scheduler] 아침 동기화 에러 ({cycle_id}): {e}")

async def auto_trade_job():
    import httpx
    print("[Scheduler] 자동 매매(Auto Trade) 작업을 실행합니다.")
    
    cycles = await get_active_cycles()
    for c in cycles:
        cycle_id = c["cycle_id"]
        name_to_show = f"[{c['name']}] {c['symbol']}" if c.get("name") else c["symbol"]
        
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                res = await client.post(f"http://127.0.0.1:8081/api/action/auto_trade?cycle_id={cycle_id}")
                if res.status_code == 200:
                    data = res.json()
                    msg = data.get("message", "")
                    
                    if "건너뜁니다" in msg or "아닙니다" in msg:
                        print(f"[Scheduler] {name_to_show} {msg}")
                        continue
                    
                    state_res = await client.get(f"http://127.0.0.1:8081/api/cycle?cycle_id={cycle_id}")
                    cash = "0"
                    current_t = 0.0
                    if state_res.status_code == 200:
                        state_data = state_res.json()
                        cash = state_data.get("cash_remaining", "0")
                        current_t = state_data.get("T", 0.0)
                    
                    await notifier.send_briefing_async(
                        symbol=name_to_show,
                        cycle_id=cycle_id,
                        orders_summary=f"🤖 [자동 매매 전송 결과]\n{msg}",
                        cash=f"{float(cash):.2f}",
                        current_t=current_t
                    )
                else:
                    print(f"[Scheduler] {name_to_show} 자동 매매 호출 실패: {res.text}")
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
