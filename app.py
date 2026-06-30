import os
from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from decimal import Decimal
from datetime import date, timedelta
from typing import Optional, Dict
import yfinance as yf

from domain.models import StrategyParams, CycleState, CycleStatus, OrderKind, Side
from strategy.infinite_buying_v4 import InfiniteBuyingV4Strategy
from strategy.state_machine import CycleStateMachine
from brokers.kis_adapter import KISBrokerAdapter
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Infinite Buying V4 Dashboard")

from services.scheduler import start_scheduler
from services.notifier import notifier
from services.persistence import load_cycles, save_cycles
import asyncio

@app.on_event("startup")
async def startup_event():
    start_scheduler()
    await notifier.start_bot()

@app.on_event("shutdown")
async def shutdown_event():
    await notifier.stop_bot()

cycles: Dict[str, CycleState] = load_cycles()
strategy = InfiniteBuyingV4Strategy()
machine = CycleStateMachine()

class StartCycleRequest(BaseModel):
    name: str = ""
    symbol: str
    total_budget: float
    split_count: int = 40
    commission_rate: float = 0.0
    initial_loc_pct: float = 0.15
    sudden_drop_pct: float = -0.10
    is_auto_mode: bool = False

class ActionRequest(BaseModel):
    action: str
    price: float
    quantity: float

@app.get("/api/cycles")
def get_all_cycles():
    # 반환 형식 유지하되 cycle_id와 name, symbol을 함께 반환하면 클라이언트가 편함
    return {"cycles": [{"cycle_id": cid, "name": state.params.name, "symbol": state.params.symbol.value} for cid, state in cycles.items()]}

@app.post("/api/cycle")
def start_cycle(req: StartCycleRequest):
    global cycles
    
    ticker = yf.Ticker(req.symbol)
    hist = ticker.history(period="5d")
    hist = hist.dropna(subset=['Close'])
    if hist.empty:
        raise HTTPException(status_code=400, detail="가격 데이터를 가져올 수 없습니다. 종목 코드(심볼)를 확인해주세요.")
        
    current_price = Decimal(str(hist.iloc[-1]['Close']))
    loc_multiplier = Decimal('1.10') # 고정 10% 버퍼 적용
    min_budget_per_day = (current_price * loc_multiplier) * Decimal('2')
    min_total_budget = min_budget_per_day * Decimal(str(req.split_count))
    
    if Decimal(str(req.total_budget)) < min_total_budget:
        formatted_min = f"${min_total_budget:,.2f}"
        raise HTTPException(status_code=400, detail=f"최소 예산 부족! 현재 주가(${current_price:,.2f}) 기준 하루에 최소 2주를 사기 위해 약 {formatted_min} 이상이 필요합니다.")
        
    params = StrategyParams(
        name=req.name,
        symbol=req.symbol,
        total_budget=Decimal(str(req.total_budget)),
        split_count=req.split_count,
        commission_rate=Decimal(str(req.commission_rate)),
        initial_loc_pct=Decimal(str(req.initial_loc_pct)),
        sudden_drop_pct=Decimal(str(req.sudden_drop_pct)),
        is_auto_mode=req.is_auto_mode
    )
    cycle_id = params.cycle_id
    cycles[cycle_id] = CycleState(params=params)
    strategy.calculate_daily_indicators(cycles[cycle_id])
    save_cycles(cycles)
    return get_cycle_state(cycle_id)


class UpdateLocPctRequest(BaseModel):
    initial_loc_pct: float

@app.patch("/api/cycle/loc_pct")
def update_loc_pct(req: UpdateLocPctRequest, cycle_id: str = Query(...)):
    if cycle_id not in cycles:
        raise HTTPException(status_code=400, detail="No active cycle for cycle_id")
    cycles[cycle_id].params.initial_loc_pct = Decimal(str(req.initial_loc_pct))
    save_cycles(cycles)
    return {"status": "success"}

class UpdateSuddenDropPctRequest(BaseModel):
    sudden_drop_pct: float

@app.patch("/api/cycle/sudden_drop_pct")
def update_sudden_drop_pct(req: UpdateSuddenDropPctRequest, cycle_id: str = Query(...)):
    if cycle_id not in cycles:
        raise HTTPException(status_code=400, detail="No active cycle for cycle_id")
    cycles[cycle_id].params.sudden_drop_pct = Decimal(str(req.sudden_drop_pct))
    save_cycles(cycles)
    return {"status": "success"}

@app.delete("/api/cycle/reset")
def reset_cycle(cycle_id: str = Query(...)):
    if cycle_id in cycles:
        del cycles[cycle_id]
        save_cycles(cycles)
    return {"status": "success"}

@app.get("/api/cycle")
def get_cycle_state(cycle_id: str = Query(...)):
    current_cycle = cycles.get(cycle_id)
    if not current_cycle:
        return {"active": False}
    try:
        ticker = yf.Ticker(current_cycle.params.symbol)
        hist = ticker.history(period="5d")
        hist = hist.dropna(subset=['Close'])
        if not hist.empty:
            avg_price = Decimal(str(hist['Close'].mean()))
            current_cycle.current_5d_avg = avg_price
    except Exception:
        pass
        
    strategy.calculate_daily_indicators(current_cycle)
    
    return {
        "active": True,
        "cycle_id": current_cycle.params.cycle_id,
        "name": current_cycle.params.name,
        "symbol": current_cycle.params.symbol,
        "total_budget": float(current_cycle.params.total_budget),
        "split_count": current_cycle.params.split_count,
        "cash_remaining": float(current_cycle.cash_remaining),
        "quantity": float(current_cycle.position.quantity),
        "avg_price": float(current_cycle.position.avg_price),
        "T": current_cycle.T,
        "status": current_cycle.status.name,
        "reverse_mode": current_cycle.reverse_mode,
        "current_star_pct": float(current_cycle.current_star_pct),
        "current_star_price": float(current_cycle.current_star_price),
        "current_one_lot_budget": float(current_cycle.current_one_lot_budget),
        "initial_loc_pct": float(current_cycle.params.initial_loc_pct),
        "sudden_drop_pct": float(current_cycle.params.sudden_drop_pct),
        "is_auto_mode": current_cycle.params.is_auto_mode
    }

@app.get("/api/price/{ticker}")
def get_current_price(ticker: str):
    try:
        t = yf.Ticker(ticker)
        todays_data = t.history(period='1d')
        if not todays_data.empty:
            return {"price": float(todays_data['Close'].iloc[0])}
        return {"price": 0.0}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/status/pnl")
def get_status_pnl(cycle_id: str = Query(...)):
    current_cycle = cycles.get(cycle_id)
    if not current_cycle:
        raise HTTPException(status_code=400, detail="No active cycle")
    
    qty = float(current_cycle.position.quantity)
    avg_price = float(current_cycle.position.avg_price)
    
    try:
        t = yf.Ticker(current_cycle.params.symbol)
        todays_data = t.history(period='1d')
        current_price = float(todays_data['Close'].iloc[0]) if not todays_data.empty else 0.0
    except Exception:
        current_price = 0.0
        
    unrealized_pnl = 0.0
    unrealized_pnl_pct = 0.0
    if qty > 0 and avg_price > 0 and current_price > 0:
        unrealized_pnl = (current_price - avg_price) * qty
        unrealized_pnl_pct = (current_price - avg_price) / avg_price * 100
        
    return {
        "cycle_id": cycle_id,
        "name": current_cycle.params.name,
        "symbol": current_cycle.params.symbol.value,
        "quantity": qty,
        "avg_price": avg_price,
        "current_price": current_price,
        "unrealized_pnl": unrealized_pnl,
        "unrealized_pnl_pct": unrealized_pnl_pct,
        "T": current_cycle.T,
        "cash_remaining": float(current_cycle.cash_remaining)
    }

@app.get("/api/orders/today")
def get_orders_today(cycle_id: str = Query(...)):
    current_cycle = cycles.get(cycle_id)
    if not current_cycle:
        raise HTTPException(status_code=400, detail="No active cycle")
        
    try:
        ticker = yf.Ticker(current_cycle.params.symbol)
        hist = ticker.history(period="5d")
        hist = hist.dropna(subset=['Close'])
        if hist.empty:
            ref_price = Decimal('0')
            current_cycle.current_5d_avg = Decimal('0')
        else:
            ref_price = Decimal(str(hist.iloc[-1]['Close']))
            avg_price = Decimal(str(hist['Close'].mean()))
            current_cycle.current_5d_avg = avg_price
            
        buy_orders = strategy.build_buy_orders(current_cycle, ref_price)
        sell_orders = strategy.build_sell_orders(current_cycle)
        all_orders = buy_orders + sell_orders
        
        orders_data = [{"kind": o.kind.value, "price": float(o.price), "quantity": float(o.quantity), "tag": o.tag} for o in all_orders]
        
        return {
            "ref_price": float(ref_price),
            "orders": orders_data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/action")
def apply_action(req: ActionRequest, cycle_id: str = Query(...)):
    current_cycle = cycles.get(cycle_id)
    if not current_cycle:
        raise HTTPException(status_code=400, detail="No active cycle")
        
    updated_cycle = machine.process_action(
        current_cycle, 
        req.action, 
        Decimal(str(req.price)), 
        Decimal(str(req.quantity))
    )
    
    if updated_cycle.status == CycleStatus.WAITING_RESET:
        params = updated_cycle.params
        updated_cycle = CycleState(params=params)
        
    cycles[cycle_id] = updated_cycle
    save_cycles(cycles)
    return get_cycle_state(cycle_id)

class SyncPositionRequest(BaseModel):
    quantity: float
    avg_price: float

@app.post("/api/cycle/sync")
def sync_position(req: SyncPositionRequest, cycle_id: str = Query(...)):
    current_cycle = cycles.get(cycle_id)
    if not current_cycle:
        raise HTTPException(status_code=400, detail="No active cycle")

    quantity = Decimal(str(req.quantity))
    avg_price = Decimal(str(req.avg_price))
    
    # Update position
    current_cycle.position.quantity = quantity
    current_cycle.position.avg_price = avg_price
    
    # Calculate new T and cash remaining
    total_invested = quantity * avg_price
    budget_per_day = current_cycle.params.total_budget / Decimal(str(current_cycle.params.split_count))
    if budget_per_day > 0:
        raw_t = float(total_invested / budget_per_day)
        current_cycle.T = round(raw_t * 2) / 2
    else:
        current_cycle.T = 0.0
        
    current_cycle.cash_remaining = current_cycle.params.total_budget - total_invested
    
    # Ensure cash doesn't exceed total budget (if they input 0 qty)
    if current_cycle.cash_remaining > current_cycle.params.total_budget:
        current_cycle.cash_remaining = current_cycle.params.total_budget
        
    # Update status based on new T
    if current_cycle.T > current_cycle.params.split_count - 1:
        current_cycle.reverse_mode = True
        current_cycle.status = CycleStatus.REVERSE_MODE
        divisor = Decimal('10') if current_cycle.params.split_count == 20 else Decimal('20')
        if current_cycle.reverse_sell_qty_unit == 0:
            current_cycle.reverse_sell_qty_unit = current_cycle.position.quantity / divisor
    else:
        current_cycle.reverse_mode = False
        current_cycle.status = CycleStatus.RUNNING

    strategy.calculate_daily_indicators(current_cycle)
    save_cycles(cycles)
    return get_cycle_state(cycle_id)

@app.post("/api/action/submit_to_broker")
def submit_to_broker(cycle_id: str = Query(...)):
    current_cycle = cycles.get(cycle_id)
    if not current_cycle:
        raise HTTPException(status_code=400, detail="No active cycle")

    try:
        ticker = yf.Ticker(current_cycle.params.symbol)
        hist = ticker.history(period="5d")
        hist = hist.dropna(subset=['Close'])
        if hist.empty:
            raise HTTPException(status_code=500, detail="가격 데이터를 불러오지 못했습니다.")
            
        ref_price = Decimal(str(hist.iloc[-1]['Close']))
        buy_orders = strategy.build_buy_orders(current_cycle, ref_price)
        sell_orders = strategy.build_sell_orders(current_cycle)
        all_orders = buy_orders + sell_orders

        paper_trading = os.getenv("KIS_PAPER_TRADING", "True").lower() == "true"
        adapter = KISBrokerAdapter(paper_trading=paper_trading)
        
        results = []
        for order in all_orders:
            try:
                odno = adapter.submit_order(order)
                results.append({"tag": order.tag, "status": "SUCCESS", "odno": odno})
            except Exception as e:
                results.append({"tag": order.tag, "status": "FAIL", "detail": str(e)})
                
        success_count = sum(1 for r in results if r["status"] == "SUCCESS")
        fail_count = len(results) - success_count
        
        return {
            "message": f"총 {len(results)}건 주문 전송 완료 (성공: {success_count}, 실패: {fail_count})",
            "results": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

from datetime import date

@app.post("/api/action/auto_sync")
def auto_sync_kis(cycle_id: str = Query(...)):
    current_cycle = cycles.get(cycle_id)
    if not current_cycle:
        raise HTTPException(status_code=400, detail="No active cycle")

    try:
        paper_trading = os.getenv("KIS_PAPER_TRADING", "True").lower() == "true"
        adapter = KISBrokerAdapter(paper_trading=paper_trading)
        
        # 최근 4일간의 체결 내역 조회 (주말 미국장 및 휴일 체결 누락 방지)
        today = date.today()
        start_date = today - timedelta(days=4)
        fills = adapter.get_fills(current_cycle.params.symbol.value, start_date, today)
        
        messages = []
        
        # 1. T (회차) 이벤트 기반 누적 계산
        daily_buy_values = {}
        if fills:
            for fill in fills:
                # 중복 처리 방지 (고유 주문번호 사용)
                if fill.side == Side.BUY and fill.order_id and fill.order_id not in current_cycle.processed_order_ids:
                    current_cycle.processed_order_ids.append(fill.order_id)
                    date_str = fill.trade_date.strftime("%Y-%m-%d")
                    daily_buy_values[date_str] = daily_buy_values.get(date_str, Decimal('0')) + (fill.price * fill.quantity)
                    
        # 날짜별로 매수 금액을 분석하여 T값 증가
        if daily_buy_values:
            budget_per_day = current_cycle.params.total_budget / Decimal(str(current_cycle.params.split_count))
            for date_str, buy_val in daily_buy_values.items():
                if buy_val >= budget_per_day * Decimal('0.7'):
                    current_cycle.T += 1.0
                    messages.append(f"[{date_str}] 1회 매수 판정 (T+1.0)")
                elif buy_val > 0:
                    current_cycle.T += 0.5
                    messages.append(f"[{date_str}] 절반 매수 판정 (T+0.5)")

        # 2. 잔고 동기화 (Truth of State) - 수량/평단가 강제 덮어쓰기
        balance = adapter.get_balance(current_cycle.params.symbol.value)
        if balance and balance["quantity"] > 0:
            current_cycle.position.quantity = balance["quantity"]
            current_cycle.position.avg_price = balance["avg_price"]
            
            # 잔여 현금 역산
            total_invested = balance["quantity"] * balance["avg_price"]
            current_cycle.cash_remaining = current_cycle.params.total_budget - total_invested
            
            # 상태 재평가 (T가 절반 이상 넘어가면 리버스 모드)
            if current_cycle.T >= float(current_cycle.params.split_count) / 2:
                current_cycle.reverse_mode = True
                current_cycle.status = CycleStatus.REVERSE_MODE
            else:
                current_cycle.reverse_mode = False
                current_cycle.status = CycleStatus.RUNNING
                
            strategy.calculate_daily_indicators(current_cycle)
            messages.append(f"잔고 동기화: {balance['quantity']}주 (평단 ${balance['avg_price']}, 진행률 T={current_cycle.T})")
        elif balance and balance["quantity"] == 0:
            messages.append("잔고 0주 확인됨 (사이클 초기화 필요 시 수동 진행)")
        else:
            messages.append("잔고 조회 내역 없음")
            
        save_cycles(cycles)
        
        final_msg = " | ".join(messages)
        if not final_msg:
            final_msg = "새로운 체결 내역 및 잔고 변동 없음"
        return {"message": final_msg}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/action/auto_fill")
def auto_fill_action(symbol: str = Query("TQQQ")):
    current_cycle = cycles.get(symbol)
    if not current_cycle:
        raise HTTPException(status_code=400, detail="No active cycle")

    try:
        ticker = yf.Ticker(current_cycle.params.symbol)
        hist = ticker.history(period="5d")
        if hist.empty or len(hist) < 2:
            raise HTTPException(status_code=500, detail="데이터를 불러오지 못했습니다.")
        
        last_day = hist.iloc[-1]
        prev_day = hist.iloc[-2]
        
        high = Decimal(str(last_day['High']))
        low = Decimal(str(last_day['Low']))
        close = Decimal(str(last_day['Close']))
        ref_price = Decimal(str(prev_day['Close']))

        buy_orders = strategy.build_buy_orders(current_cycle, ref_price)
        sell_orders = strategy.build_sell_orders(current_cycle)
        all_orders = buy_orders + sell_orders

        filled_actions = []

        for order in all_orders:
            filled = False
            fill_price = close
            
            if order.kind == OrderKind.LIMIT:
                if order.side == Side.BUY and low <= order.price:
                    filled = True
                    fill_price = order.price
                elif order.side == Side.SELL and high >= order.price:
                    filled = True
                    fill_price = order.price
            elif order.kind == OrderKind.LOC:
                if order.side == Side.BUY and close <= order.price:
                    filled = True
                elif order.side == Side.SELL and close >= order.price:
                    filled = True
            elif order.kind == OrderKind.MOC:
                filled = True

            if filled:
                action_str = None
                if "1회 매수" in order.tag: action_str = "full_buy"
                elif "절반 매수" in order.tag: action_str = "half_buy"
                elif "쿼터 매수" in order.tag: action_str = "reverse_buy"
                elif "무한 매도" in order.tag: action_str = "reverse_sell"
                elif "쿼터 매도" in order.tag: action_str = "quarter_sell"
                elif "전량 익절" in order.tag: action_str = "take_profit"

                if action_str:
                    current_cycle = machine.process_action(current_cycle, action_str, fill_price, order.quantity)
                    filled_actions.append(order.tag)

        if current_cycle.status == CycleStatus.WAITING_RESET:
            params = current_cycle.params
            current_cycle = CycleState(params=params)

        cycles[symbol] = current_cycle

        if not filled_actions:
            return {"status": "success", "message": "체결된 주문이 없습니다."}
        
        return {"status": "success", "message": ", ".join(filled_actions)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def read_index():
    return FileResponse("static/index.html")
