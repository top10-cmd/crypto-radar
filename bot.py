import os
import asyncio
import logging
from typing import Dict
from aiohttp import ClientSession, web
from aiogram import Bot, Dispatcher, html
from aiogram.filters import CommandStart
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

# Получаем секретные ключи из настроек облака
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = int(os.getenv("CHAT_ID", "0"))

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

class CEXAnomalyMonitor:
    def __init__(self, bot: Bot, chat_id: int):
        self.bot = bot
        self.chat_id = chat_id
        self.last_prices: Dict[str, float] = {}

    async def check_mexc_anomalies(self, session: ClientSession):
        """Отслеживание резких скачков цены B2 на MEXC"""
        url = "https://api.mexc.com/api/v3/ticker/24hr?symbol=B2USDT"
        try:
            async with session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    current_price = float(data.get("lastPrice", 0))
                    volume_24h = float(data.get("quoteVolume", 0))
                    symbol = "B2USDT"

                    if symbol in self.last_prices:
                        prev_price = self.last_prices[symbol]
                        if prev_price > 0:
                            price_change_pct = ((current_price - prev_price) / prev_price) * 100

                            # Порог: изменение цены от 1.5% за 10 секунд
                            if abs(price_change_pct) >= 1.5:
                                direction = "🚀 ПАМП" if price_change_pct > 0 else "📉 ДАМП"
                                
                                # Ссылка на русскую версию MEXC
                                ru_link = "https://www.mexc.com/ru-RU/exchange/B2_USDT"
                                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                                    [InlineKeyboardButton(text="📊 Открыть на MEXC (RU)", url=ru_link)]
                                ])

                                msg = (
                                    f"⚡ <b>CEX ANOMALY: {direction}</b>\n\n"
                                    f"🔹 <b>Пара:</b> {symbol} (MEXC)\n"
                                    f"📈 <b>Импульс цены:</b> {price_change_pct:+.2f}%\n"
                                    f"💵 <b>Текущая цена:</b> ${current_price:.4f}\n"
                                    f"📊 <b>Объем 24ч:</b> ${volume_24h:,.0f}"
                                )
                                await self.bot.send_message(self.chat_id, msg, parse_mode="HTML", reply_markup=keyboard)

                    self.last_prices[symbol] = current_price
        except Exception as e:
            logging.error(f"Ошибка CEX монитора: {e}")

    async def run_loop(self):
        async with ClientSession() as session:
            while True:
                await self.check_mexc_anomalies(session)
                await asyncio.sleep(10)

@dp.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    ru_link = "https://www.mexc.com/ru-RU/exchange/B2_USDT"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 График B2 на MEXC", url=ru_link)]
    ])
    await message.answer(
        f"Привет, {html.bold(message.from_user.full_name)}!\n"
        f"🤖 Радар-бот запущен. Я отслеживаю аномалии. Биржа по кнопке ниже откроется на русском.",
        reply_markup=keyboard
    )

# --- Заглушка для облака Render ---
async def handle_ping(request):
    return web.Response(text="Bot is running!")

async def main():
    cex = CEXAnomalyMonitor(bot, CHAT_ID)
    asyncio.create_task(cex.run_loop())
    asyncio.create_task(dp.start_polling(bot))

    app = web.Application()
    app.router.add_get('/', handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    logging.info("Бот и сервер успешно запущены!")
    
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(main())
