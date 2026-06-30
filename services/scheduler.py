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

def start_scheduler():
    trigger_briefing = CronTrigger(hour=22, minute=0, timezone="Asia/Seoul")
    scheduler.add_job(daily_briefing_job, trigger=trigger_briefing, id="daily_briefing", replace_existing=True)
    
    trigger_sync = CronTrigger(hour=8, minute=0, timezone="Asia/Seoul")
    scheduler.add_job(morning_sync_job, trigger=trigger_sync, id="morning_sync", replace_existing=True)
    
    scheduler.start()
    print("[Scheduler] 스케줄러가 시작되었습니다. (매일 22:00 브리핑, 08:00 체결 동기화)")
