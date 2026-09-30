import os
import asyncio
import logging
from typing import Dict
from aiohttp import ClientSession
from aiogram import Bot, Dispatcher, html
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.filters import CommandStart
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = int(os.getenv("CHAT_ID", "0"))

logging.basicConfig(level=logging.INFO)

# Подключаем встроенный прокси PythonAnywhere для Telegram API
PROXY_URL = "http://proxy.server:3128"
bot_session = AiohttpSession(proxy=PROXY_URL)
bot = Bot(token=BOT_TOKEN, session=bot_session)
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
            # Отправляем запрос к MEXC через прокси PythonAnywhere
            async with session.get(url, proxy=PROXY_URL) as resp:
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
        f"🤖 Радар-бот запущен и отслеживает аномалии B2.",
        reply_markup=keyboard
    )

async def main():
    cex = CEXAnomalyMonitor(bot, CHAT_ID)
    asyncio.create_task(cex.run_loop())
    logging.info("Бот успешно запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
