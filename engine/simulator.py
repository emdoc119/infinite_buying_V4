from decimal import Decimal
from typing import Dict, Any
import pandas as pd

from domain.models import CycleState, StrategyParams, FillEvent, Side, OrderKind, CycleStatus
from strategy.infinite_buying_v4 import InfiniteBuyingV4Strategy
from strategy.state_machine import CycleStateMachine

class BacktestSimulator:
    def __init__(self, params: StrategyParams, df: pd.DataFrame):
        self.params = params
        self.df = df
        self.strategy = InfiniteBuyingV4Strategy()
        self.machine = CycleStateMachine()
        
    def run(self) -> Dict[str, Any]:
        cycle = CycleState(params=self.params)
        history = []
        completed_cycles = 0
        
        peak_equity = self.params.total_budget
        max_drawdown = Decimal("0")
        
        prev_close = None
        
        for idx, row in self.df.iterrows():
            current_date = idx.date() if hasattr(idx, 'date') else idx
            
            open_p = Decimal(str(row['Open']))
            high_p = Decimal(str(row['High']))
            low_p = Decimal(str(row['Low']))
            close_p = Decimal(str(row['Close']))
            
            if prev_close is None:
                prev_close = open_p
                
            # 1. 어제 상태 기준으로 오늘 주문 생성 (버퍼 기준가는 전일 종가)
            buy_orders = self.strategy.build_buy_orders(cycle, current_date, ref_price_for_buffer=prev_close)
            sell_orders = self.strategy.build_sell_orders(cycle, current_date)
            
            fills = []
            
            # 2. 매도 주문 체결 매칭 (지정가 매도)
            # 목표가가 당일 고가 이하라면 체결된 것으로 간주
            for order in sell_orders:
                if order.kind == OrderKind.LIMIT and high_p >= order.price:
                    fills.append(FillEvent(
                        symbol=order.symbol,
                        side=Side.SELL,
                        price=order.price,
                        quantity=order.quantity,
                        trade_date=current_date
                    ))
            
            # 매도가 체결되었다면 (익절), 당일 매수 주문은 취소된 것으로 처리.
            if not fills:
                # 3. 매도 미체결 시 매수 체결 매칭 (LOC)
                for order in buy_orders:
                    if order.kind == OrderKind.LOC:
                        # LOC 매수는 당일 종가가 주문가(Limit)보다 작거나 같을 때 해당 종가로 체결
                        if close_p <= order.price:
                            fills.append(FillEvent(
                                symbol=order.symbol,
                                side=Side.BUY,
                                price=close_p,
                                quantity=order.quantity,
                                trade_date=current_date
                            ))
                            
            # 4. 체결 반영
            cycle = self.machine.apply_fills(cycle, fills)
            
            # 5. 전량 매도 완료로 인한 사이클 종료 시 재시작 처리 (복리 적용)
            if cycle.status == CycleStatus.WAITING_RESET:
                completed_cycles += 1
                cycle.status = CycleStatus.RUNNING
                cycle.params.total_budget = cycle.cash_remaining
            
            # 6. 종가 기준 계좌 상태 평가 (리버스 모드 판정)
            cycle = self.machine.evaluate_after_close(cycle, close_p)
            
            # 7. 통계 추적 (MDD 등)
            equity = cycle.cash_remaining + (cycle.position.quantity * close_p)
            if equity > peak_equity:
                peak_equity = equity
            
            dd = (equity - peak_equity) / peak_equity
            if dd < max_drawdown:
                max_drawdown = dd
                
            history.append({
                'date': current_date,
                'close': float(close_p),
                'equity': float(equity),
                'cash': float(cycle.cash_remaining),
                'qty': float(cycle.position.quantity),
                'avg_price': float(cycle.position.avg_price),
                'T': cycle.T,
                'reverse_mode': cycle.reverse_mode,
                'status': cycle.status.name
            })
            
            prev_close = close_p
            
        final_equity = cycle.cash_remaining + (cycle.position.quantity * prev_close)
        initial_budget = Decimal("10000") # 초기 원금 고정
        total_return_pct = (final_equity - initial_budget) / initial_budget * 100
        
        return {
            'history': pd.DataFrame(history),
            'final_equity': float(final_equity),
            'total_return_pct': float(total_return_pct),
            'max_drawdown_pct': float(max_drawdown * 100),
            'completed_cycles': completed_cycles
        }
