import requests
import xml.etree.ElementTree as ET
from telegram import ReplyKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

TOKEN = "8408097470:AAFuCqdrNMoPKHODl2Z0eGmkp1xeOZvMWt4"

# ===== НАСТРОЙКИ =====
USD_VND = 25144        # базовый курс
MARGIN = 0.04          # 4% скрытая маржа
MAP_LINK = "https://maps.app.goo.gl/krV5k2CNnfMdeR5u7"
CONTACT = "@banance_club"

rates = {
    "usd_rub": None,
    "kzt_rub": None
}

# ===== ЗАГРУЗКА КУРСОВ ЦБ РФ =====
def update_rates():
    global rates
    try:
        url = "https://www.cbr.ru/scripts/XML_daily.asp"
        response = requests.get(url, timeout=10)
        root = ET.fromstring(response.content)

        for valute in root.findall("Valute"):
            code = valute.find("CharCode").text
            value = float(valute.find("Value").text.replace(",", "."))
            nominal = int(valute.find("Nominal").text)

            if code == "USD":
                rates["usd_rub"] = value

            if code == "KZT":
                # сколько рублей за 1 KZT
                rates["kzt_rub"] = value / nominal

        print("Курсы обновлены")

    except Exception as e:
        print("Ошибка загрузки:", e)


# ===== РАСЧЁТ =====
def calculate_vnd(amount, currency):

    if not rates["usd_rub"]:
        return "Курс временно недоступен."

    # курс 1 RUB в VND
    vnd_per_rub = USD_VND / rates["usd_rub"]

    if currency == "RUB":
        base_rate = vnd_per_rub

    elif currency == "KZT":
        if not rates["kzt_rub"]:
            return "Курс KZT временно недоступен."

        # 1 KZT → RUB → VND
        base_rate = rates["kzt_rub"] * vnd_per_rub

    else:
        return "Ошибка валюты."

    # скрыто отнимаем 4%
    final_rate = base_rate * (1 - MARGIN)

    vnd = amount * final_rate

    message = (
        f"💱 Обмен {currency} → VND\n\n"
        f"Сумма: {amount:,.0f} {currency}\n"
        f"Курс: {final_rate:,.2f} VND\n"
        f"К выдаче: {vnd:,.0f} VND\n\n"
        f"📍 Локация:\n{MAP_LINK}\n\n"
        f"📩 Связаться: {CONTACT}"
    )

    if vnd > 10_000_000:
        message += (
            "\n\n⚠️ Пожалуйста свяжитесь заранее для заказа наличных. "
            "Пока вы будете ехать к нам, мы подготовим нужную сумму, "
            "чтобы вы получили деньги без ожидания."
        )

    return message


# ===== START =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        ["RUB → VND"],
        ["KZT → VND"],
        ["🔄 Обновить курс"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    await update.message.reply_text(
        "Выберите направление обмена:",
        reply_markup=reply_markup
    )


# ===== ОБРАБОТКА =====
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    # Обновление курса
    if text == "🔄 Обновить курс":
        update_rates()
        await update.message.reply_text("Курс обновлён.")
        return

    # Выбор направления
    if text == "RUB → VND":
        context.user_data["currency"] = "RUB"
        await update.message.reply_text("Введите сумму в RUB:")
        return

    if text == "KZT → VND":
        context.user_data["currency"] = "KZT"
        await update.message.reply_text("Введите сумму в KZT:")
        return

    # Ввод суммы
    if "currency" in context.user_data:
        try:
            amount = float(text.replace(" ", "").replace(",", "."))
            currency = context.user_data["currency"]

            result = calculate_vnd(amount, currency)
            await update.message.reply_text(result)

            context.user_data.clear()

        except:
            await update.message.reply_text("Введите корректную сумму.")
        return


# ===== ЗАПУСК =====
if __name__ == "__main__":
    print("Загружаем курсы при старте...")
    update_rates()

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Бот запущен")
    app.run_polling()