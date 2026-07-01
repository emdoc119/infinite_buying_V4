from decimal import Decimal
from enum import Enum
from pydantic import BaseModel, Field
from datetime import date
from typing import Optional, List

class CycleStatus(Enum):
    RUNNING = "RUNNING"
    WAITING_RESET = "WAITING_RESET"
    REVERSE_MODE = "REVERSE_MODE"
    COMPLETED = "COMPLETED"

class Side(Enum):
    BUY = "BUY"
    SELL = "SELL"

class OrderKind(Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    LOC = "LOC"
    MOC = "MOC"

class TickerType(str, Enum):
    TQQQ = "TQQQ"
    SOXL = "SOXL"

import uuid

class StrategyParams(BaseModel):
    cycle_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    symbol: TickerType
    total_budget: Decimal
    split_count: int = 40 # 20 or 40
    commission_rate: Decimal = Field(default=Decimal('0.0'))
    initial_loc_pct: Decimal = Field(default=Decimal('0.15'))
    star_alpha: Decimal = Field(default=Decimal('0.10'))
    star_beta: Decimal = Field(default=Decimal('2.0'))
    sudden_drop_pct: Decimal = Field(default=Decimal('-0.20'))
    crash_prep_enabled: bool = True
    crash_prep_ratios: List[float] = Field(default_factory=lambda: [-0.20, -0.30, -0.40, -0.50])
    is_auto_mode: bool = False

class Position(BaseModel):
    quantity: Decimal = Decimal('0')
    avg_price: Decimal = Decimal('0')
    
    @property
    def value(self) -> Decimal:
        return self.quantity * self.avg_price

class FillEvent(BaseModel):
    symbol: str
    side: Side
    price: Decimal
    quantity: Decimal
    trade_date: date
    order_id: str = ""
    action: Optional[str] = None

class OrderIntent(BaseModel):
    symbol: str
    side: Side
    kind: OrderKind
    price: Decimal
    quantity: Decimal
    tag: str = ""

class CycleState(BaseModel):
    params: StrategyParams
    status: CycleStatus = CycleStatus.RUNNING
    T: float = 0.0
    processed_order_ids: List[str] = Field(default_factory=list)
    cash_remaining: Decimal = Field(default_factory=Decimal)
    position: Position = Field(default_factory=Position)
    fills: List[FillEvent] = Field(default_factory=list)
    
    # UI 표시용 필드 (매일 계산됨)
    current_star_pct: float = 0.15
    current_star_price: Decimal = Decimal('0')
    current_one_lot_budget: Decimal = Decimal('0')
    
    # 리버스 모드용 상태
    reverse_mode: bool = False
    reverse_sell_qty_unit: Decimal = Decimal('0')
    current_5d_avg: Decimal = Decimal('0')
    
    def __init__(self, **data):
        super().__init__(**data)
        if self.cash_remaining == Decimal('0') and self.status == CycleStatus.RUNNING and self.T == 0.0 and len(self.fills) == 0:
            self.cash_remaining = self.params.total_budget
