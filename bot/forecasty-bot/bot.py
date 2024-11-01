import os
import json
import httpx
import asyncio
import logging

from datetime import datetime
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.filters.command import Command
from aiogram import Bot, Dispatcher, F, types
from aiogram.fsm.state import State, StatesGroup


API_URL = "http://forecasty-backend:5000"

logging.basicConfig(level=logging.INFO)

bot = Bot(os.getenv("BOT_TOKEN"))

dp = Dispatcher()


class WeatherState(StatesGroup):
    choosing_first_point = State()
    choosing_second_point = State()
    choosing_period = State()


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "Привет!\n\n"
        "Это бот для получения прогноза погоды по заданному маршруту.\n\n"
        "Используй команду /weather, чтобы получить прогноз погоды или /help для получения списка доступных команд."
    )


def choose_forecast_keyboard():
    buttons = [
        [
            types.InlineKeyboardButton(
                text="5 дней", callback_data="forecast_5days_5 дней"
            ),
            types.InlineKeyboardButton(
                text="12 часов", callback_data="forecast_12hours_12 часов"
            ),
        ]
    ]
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard


@dp.message(Command("weather"))
async def cmd_weather(message: types.Message, state: FSMContext):
    await message.answer("Введите первую точку маршрута")
    await state.set_state(WeatherState.choosing_first_point)


@dp.message(WeatherState.choosing_first_point)
async def choose_second_point(message: types.Message, state: FSMContext):
    await state.update_data(first_point=message.text)
    await message.answer("Введите вторую точку маршрута")
    await state.set_state(WeatherState.choosing_second_point)


@dp.message(WeatherState.choosing_second_point)
async def choose_weather_period(message: types.Message, state: FSMContext):
    await state.update_data(second_point=message.text)
    await message.answer(
        "На какой период времени мне стоит предоставить прогноз погоды?",
        reply_markup=choose_forecast_keyboard(),
    )
    await state.set_state(WeatherState.choosing_period)


async def request_forecast(point: str, period: str) -> dict | None:
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{API_URL}/accu/forecast/{period}", params={"location": point}
        )
        try:
            if response.status_code == 200 and response.text.find("error") == -1:
                return json.loads(response.text)
        except httpx.RequestError:
            pass


async def generate_forecast_message(
    point: str, forecast: dict, period_human_readable: str
) -> str:
    text = f"<b>{point}</b>\n<b>Прогноз на {period_human_readable}</b>"

    for fc in forecast["units"]:
        conditions = fc["conditions"]
        description = fc["description"]
        timestamp = datetime.fromisoformat(fc["date"]).strftime("%a %d %b %Y, %H:%M")

        text += (
            f"\n\n<b>{timestamp}</b>\n"
            f"<i>{description}</i>\n"
            f"Температура: {conditions['temperature_c']:.2f} °C\n"
            f"Влажность: {conditions['humidity_percent']:.2f}%\n"
            f"Осадки: {conditions['precipitation_probability_percent']:.2f}%\n"
            f"Скорость ветра: {conditions['wind_speed_ms']:.2f} м/с\n"
        )

    return text


@dp.callback_query(F.data.startswith("forecast_"))
async def callback_route(callback: types.CallbackQuery, state: FSMContext):
    period = callback.data.split("_")[1]
    period_human_readable = callback.data.split("_")[2]
    data = await state.get_data()

    first_point, second_point = data["first_point"], data["second_point"]

    forecasts = {
        first_point: await request_forecast(first_point, period),
        second_point: await request_forecast(second_point, period),
    }

    if not all(forecasts.values()):
        await callback.bot.send_message(
            callback.message.chat.id,
            f"Произошла ошибка при попытке получить данные для следующих городов: "
            + ", ".join(
                [point for point, forecast in forecasts.items() if forecast is None]
            ),
        )

    for point, forecast in forecasts.items():
        if forecast is None:
            continue
        await callback.bot.send_message(
            callback.message.chat.id,
            await generate_forecast_message(point, forecast, period_human_readable),
            parse_mode=ParseMode.HTML,
        )


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
