import os
import asyncio
import logging
import httpx
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

logging.getLogger("httpx").setLevel(logging.WARNING)

class TelegramNotifier:
    def __init__(self):
        self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID")
        self.app = None
        if self.bot_token:
            self.app = Application.builder().token(self.bot_token).build()
            
            # 핸들러 등록
            self.app.add_handler(CommandHandler("start", self.start_command))
            self.app.add_handler(CallbackQueryHandler(self.button_callback))
            self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "안녕하세요! 무한매수법 V4.0 알리미 봇입니다. 🚀\n\n"
            "💬 **[대화형 명령어]**\n"
            "채팅창에 아래 단어를 포함해서 말해보세요!\n"
            "- 📈 **상태 / 수익 / 이익 / 손실**: 현재 보유수량, 평단가, 수익금/수익률을 알려줍니다.\n"
            "- 📝 **주문 / 오늘 / 계획 / 예약**: 오늘의 매수/매도 주문 계획을 알려줍니다.\n"
            "- 🚀 **전송 / 승인**: 계획된 주문을 KIS(한국투자증권)로 즉시 전송합니다.\n"
            "- ❓ **명령어 / 도움말**: 이 도움말을 다시 보여줍니다."
        )

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = update.message.text.strip()
        user_chat_id = str(update.effective_chat.id)
        
        if self.chat_id and user_chat_id != self.chat_id:
            return # 인가되지 않은 사용자 무시
            
        # 1. 상태 / 수익 조회
        if any(keyword in text for keyword in ["상태", "수익", "손실", "이익"]):
            await self._handle_status_request(update)
            
        # 2. 주문 / 계획 조회
        elif any(keyword in text for keyword in ["주문", "오늘", "계획", "예약"]):
            await self._handle_order_plan_request(update)
            
        # 3. 수동 전송 / 승인
        elif any(keyword in text for keyword in ["전송", "승인", "실행"]):
            await self._handle_manual_submit(update)
            
        # 4. 도움말
        elif any(keyword in text for keyword in ["명령어", "도움말", "?"]):
            await self.start_command(update, context)
            
        else:
            await update.message.reply_text("이해하지 못했어요. 😅\n'상태', '오늘 주문', '명령어' 등을 입력해 보세요!")

    async def _handle_status_request(self, update: Update):
        await update.message.reply_text("⏳ 현재 상태와 수익률을 조회 중입니다...")
        try:
            async with httpx.AsyncClient() as client:
                res = await client.get("http://127.0.0.1:8081/api/cycles")
                if res.status_code != 200:
                    await update.message.reply_text("❌ 활성화된 사이클 정보를 가져올 수 없습니다.")
                    return
                    
                symbols = res.json().get("cycles", [])
                if not symbols:
                    await update.message.reply_text("현재 진행 중인 무한매수 사이클이 없습니다.")
                    return
                
                for cycle_info in symbols:
                    cycle_id = cycle_info["cycle_id"]
                    name = cycle_info["name"]
                    symbol = cycle_info["symbol"]
                    name_to_show = f"[{name}] {symbol}" if name else symbol
                    
                    status_res = await client.get(f"http://127.0.0.1:8081/api/status/pnl?cycle_id={cycle_id}")
                    if status_res.status_code == 200:
                        data = status_res.json()
                        qty = data["quantity"]
                        avg_price = data["avg_price"]
                        cur_price = data["current_price"]
                        pnl = data["unrealized_pnl"]
                        pnl_pct = data["unrealized_pnl_pct"]
                        t = data["T"]
                        
                        sign = "+" if pnl > 0 else ""
                        msg = (
                            f"📊 <b>{name_to_show} 상태 (T: {t}회차)</b>\n"
                            f"보유 수량: {qty}주\n"
                            f"평균 단가: ${avg_price:.2f}\n"
                            f"현재 주가: ${cur_price:.2f}\n"
                            f"-------------------\n"
                            f"평가 손익: {sign}${pnl:.2f} ({sign}{pnl_pct:.2f}%)"
                        )
                        await update.message.reply_text(msg, parse_mode="HTML")
        except Exception as e:
            await update.message.reply_text(f"❌ 조회 중 오류가 발생했습니다: {e}")

    async def _handle_order_plan_request(self, update: Update):
        await update.message.reply_text("⏳ 오늘의 주문 계획을 계산 중입니다...")
        try:
            async with httpx.AsyncClient() as client:
                res = await client.get("http://127.0.0.1:8081/api/cycles")
                if res.status_code != 200:
                    return
                    
                symbols = res.json().get("cycles", [])
                if not symbols:
                    await update.message.reply_text("현재 진행 중인 무한매수 사이클이 없습니다.")
                    return
                
                for cycle_info in symbols:
                    cycle_id = cycle_info["cycle_id"]
                    name = cycle_info["name"]
                    symbol = cycle_info["symbol"]
                    name_to_show = f"[{name}] {symbol}" if name else symbol
                    
                    order_res = await client.get(f"http://127.0.0.1:8081/api/orders/today?cycle_id={cycle_id}")
                    if order_res.status_code == 200:
                        data = order_res.json()
                        orders = data.get("orders", [])
                        
                        if not orders:
                            msg = f"<b>{name_to_show}</b> 오늘 생성될 주문이 없습니다."
                        else:
                            lines = [f"<b>{name_to_show} 오늘의 주문 계획</b>"]
                            for o in orders:
                                lines.append(f"- [{o['kind']}] {o['quantity']}주 {o['tag']} @ ${o['price']:.2f}")
                            msg = "\n".join(lines)
                            
                        keyboard = [[InlineKeyboardButton(f"🚀 주문 전송", callback_data=f"send_kis_{cycle_id}")]]
                        reply_markup = InlineKeyboardMarkup(keyboard)
                        
                        await update.message.reply_text(msg, parse_mode="HTML", reply_markup=reply_markup)
        except Exception as e:
            await update.message.reply_text(f"❌ 조회 중 오류가 발생했습니다: {e}")

    async def _handle_manual_submit(self, update: Update):
        await update.message.reply_text("💡 주문을 전송하려면 '오늘 주문'이라고 입력한 뒤, 나타나는 [🚀 주문 전송] 버튼을 눌러주세요!")

    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer() # 텔레그램 로딩 버튼 해제
        
        data = query.data
        if data.startswith("send_kis_"):
            cycle_id = data.replace("send_kis_", "")
            # HTTP 요청으로 로컬 FastAPI의 주문 전송 엔드포인트 호출
            await query.edit_message_text(text=f"{query.message.text}\n\n⏳ 주문을 KIS로 전송 중입니다...")
            
            try:
                # 같은 서버 내 FastAPI 찌르기
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(f"http://127.0.0.1:8081/api/action/submit_to_broker?cycle_id={cycle_id}")
                    
                    if response.status_code == 200:
                        res_data = response.json()
                        success_cnt = len([r for r in res_data.get('results', []) if r.get('status') == 'SUCCESS'])
                        msg = res_data.get('message', '')
                        await query.edit_message_text(text=f"{query.message.text}\n\n✅ KIS 전송 완료: {msg} ({success_cnt}건)")
                    else:
                        await query.edit_message_text(text=f"{query.message.text}\n\n❌ KIS 전송 실패 (서버 에러)")
            except Exception as e:
                await query.edit_message_text(text=f"{query.message.text}\n\n❌ 서버 접속 오류: {e}")
                
        elif data == "cancel":
            await query.edit_message_text(text=f"{query.message.text}\n\n🔴 사용자에 의해 주문이 보류되었습니다.")

    async def start_bot(self):

        if self.app:
            await self.app.initialize()
            await self.app.start()
            await self.app.updater.start_polling(drop_pending_updates=True)
            print("[Telegram] 텔레그램 봇 리스너가 백그라운드에서 실행되었습니다.")

    async def stop_bot(self):
        if self.app:
            await self.app.updater.stop()
            await self.app.stop()
            await self.app.shutdown()

    async def send_briefing_async(self, symbol: str, cycle_id: str, orders_summary: str, cash: str, current_t: float):
        if not self.app or not self.chat_id:
            return

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        text = f"""
<b>📊 무한매수법 일일 브리핑</b>
🕒 {now_str}

<b>종목:</b> {symbol}
<b>현재 T:</b> {current_t}회차
<b>잔금:</b> ${cash}

<b>[오늘의 주문 계획]</b>
{orders_summary}
        """
        
        keyboard = [
            [
                InlineKeyboardButton("🚀 KIS로 실제 주문 전송하기", callback_data=f"send_kis_{cycle_id}")
            ],
            [
                InlineKeyboardButton("🔴 대기 (취소)", callback_data="cancel")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        try:
            await self.app.bot.send_message(
                chat_id=self.chat_id, 
                text=text.strip(), 
                parse_mode="HTML",
                reply_markup=reply_markup
            )
        except Exception as e:
            print(f"텔레그램 메시지 전송 에러: {e}")

    async def send_sync_report_async(self, symbol: str, sync_message: str, cash: str, current_t: float):
        if not self.app or not self.chat_id:
            return

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        text = f"""
<b>☀️ 간밤의 체결 동기화 완료</b>
🕒 {now_str}

<b>종목:</b> {symbol}
<b>현재 회차(T):</b> {current_t}회차
<b>남은 예산:</b> ${cash}

<b>[업데이트 내역]</b>
{sync_message}
        """
        try:
            await self.app.bot.send_message(
                chat_id=self.chat_id, 
                text=text.strip(), 
                parse_mode="HTML"
            )
        except Exception as e:
            print(f"텔레그램 메시지 전송 에러: {e}")

notifier = TelegramNotifier()
from datetime import datetime
