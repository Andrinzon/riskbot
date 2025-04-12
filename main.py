import requests
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackContext, MessageHandler, filters, CallbackQueryHandler

# Lista de usuarios que han interactuado con el bot
usuarios = set()
admin_mode = False

# Diccionario de niveles de riesgo por moneda
niveles_riesgo = {}
imagenes_riesgo = {}

# Alias de monedas
alias_monedas = {
    "btc": "bitcoin", "eth": "ethereum", "bnb": "binancecoin",
    "xrp": "ripple", "sol": "solana", "ada": "cardano"
}
monedas_validas = list(alias_monedas.values())

# Colores para cada nivel de riesgo
colores_riesgo = {
    1: "🟣 (Muy bajo)", 2: "🔵 (Bajo)", 3: "🔹 (Moderado bajo)",
    4: "🟢 (Moderado)", 5: "💚 (Medio)", 6: "💛 (Medio-alto)",
    7: "🟡 (Alto)", 8: "🟠 (Muy alto)", 9: "🔴 (Riesgoso)", 10: "🔥 (Extremo)"
}

# Obtener precio
def obtener_precio(moneda):
    try:
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={moneda}&vs_currencies=usd"
        response = requests.get(url)
        data = response.json()
        return data[moneda]["usd"] if moneda in data else None
    except Exception:
        return None

# Comando de riesgo para admin
async def establecer_riesgo(update: Update, context: CallbackContext):
    global admin_mode
    if not admin_mode:
        await update.message.reply_text("❌ No tienes permiso para este comando.")
        return

    if len(context.args) != 2:
        await update.message.reply_text("❌ Uso: /riesgo [moneda] [nivel 1-10]")
        return

    moneda = alias_monedas.get(context.args[0].lower(), context.args[0].lower())
    if moneda not in monedas_validas:
        await update.message.reply_text("❌ Moneda no soportada.")
        return

    try:
        nivel = int(context.args[1])
        if nivel < 1 or nivel > 10:
            await update.message.reply_text("❌ Nivel debe estar entre 1 y 10.")
            return
    except ValueError:
        await update.message.reply_text("❌ Nivel debe ser un número.")
        return

    niveles_riesgo[moneda] = nivel
    color_riesgo = colores_riesgo.get(nivel, "❔")

    await update.message.reply_text(
        f"✅ Riesgo de *{moneda.upper()}* asignado a {nivel} {color_riesgo}.\n"
        f"📷 Ahora envía una *imagen* para representar este riesgo.",
        parse_mode="Markdown"
    )

    context.user_data["esperando_imagen_para"] = moneda

# Recibir imagen
async def recibir_imagen(update: Update, context: CallbackContext):
    if "esperando_imagen_para" not in context.user_data:
        await update.message.reply_text("❌ No estoy esperando una imagen en este momento.")
        return

    moneda = context.user_data.pop("esperando_imagen_para")
    photo = update.message.photo[-1]
    file_id = photo.file_id
    imagenes_riesgo[moneda] = file_id

    await update.message.reply_text(f"✅ Imagen asociada al riesgo de *{moneda.upper()}* correctamente.", parse_mode="Markdown")

    for user_id in usuarios:
        await context.bot.send_photo(
            user_id,
            photo=file_id,
            caption=f"⚠️ El riesgo de *{moneda.upper()}* ha cambiado. ¡Échale un vistazo!",
            parse_mode="Markdown"
        )

# Activar modo admin
async def activar_admin(update: Update, context: CallbackContext):
    global admin_mode
    admin_mode = True
    await update.message.reply_text("🔑 Modo administrador activado. Ahora puedes modificar riesgos.")

# Menú principal
def get_main_menu():
    keyboard = [
        [InlineKeyboardButton("💰 Precio BTC", callback_data="precio_btc")],
        [InlineKeyboardButton("⚠️ Riesgo BTC", callback_data="riesgo_btc")],
        [InlineKeyboardButton("📄 Disclaimer", callback_data="disclaimer")],
        [InlineKeyboardButton("📬 Consulta Privada", callback_data="consulta_privada")]
    ]
    return InlineKeyboardMarkup(keyboard)

# Comando de inicio
async def start(update: Update, context: CallbackContext):
    usuarios.add(update.message.chat_id)
    mensaje = "🤖 ¡Bienvenido!\n\nSelecciona una opción:"
    await update.message.reply_text(mensaje, reply_markup=get_main_menu())

# Botones
async def boton_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id

    if query.data == "precio_btc":
        price = obtener_precio("bitcoin")
        mensaje = f"💰 *BTC*: ${price:,.2f}" if price else "❌ Error al obtener el precio."
        await context.bot.send_message(chat_id=chat_id, text=mensaje, parse_mode="Markdown")

    elif query.data == "riesgo_btc":
        await context.bot.send_message(chat_id=chat_id, text="🔎 Revisando riesgo...")
        await asyncio.sleep(2)

        nivel = niveles_riesgo.get("bitcoin", "No asignado")
        color = colores_riesgo.get(nivel, "❔") if isinstance(nivel, int) else ""

        if "bitcoin" in imagenes_riesgo:
            await context.bot.send_photo(
                chat_id=chat_id,
                photo=imagenes_riesgo["bitcoin"],
                caption=f"⚠️ *Riesgo de BTC*: {nivel}/10 {color}",
                parse_mode="Markdown"
            )
        else:
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"⚠️ *Riesgo de BTC*: {nivel}/10 {color}",
                parse_mode="Markdown"
            )

    elif query.data == "disclaimer":
        disclaimer_text = (
            "📄 *Disclaimer / Descargo de responsabilidad:*\n\n"
            "Este bot tiene fines *informativos y educativos* únicamente. "
            "No constituye asesoría financiera, legal ni de inversión. "
            "El uso de la información proporcionada es bajo *su propia responsabilidad*.\n\n"
            "⚠️ Toda inversión en criptomonedas conlleva riesgos. Por favor, investigue y consulte con un asesor profesional antes de tomar decisiones financieras."
        )
        await context.bot.send_message(chat_id=chat_id, text=disclaimer_text, parse_mode="Markdown")

    elif query.data == "consulta_privada":
        consulta_text = (
            "📬 *Consulta Privada Disponible*\n\n"
            "¿Necesitas una evaluación más personalizada o análisis más profundo?\n"
            "Puedes escribirme directamente a: 👉 [@andrinzon](https://t.me/andrinzon)\n\n"
            "💵 Costo de consulta: *5 USDT*"
        )
        await context.bot.send_message(chat_id=chat_id, text=consulta_text, parse_mode="Markdown", disable_web_page_preview=True)

# Iniciar bot
def main():
    TOKEN = "7883868261:AAFy-KbQk8BT1JnmLhXwAVK8udJef84T2_Q"
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("riesgo", establecer_riesgo))
    app.add_handler(CommandHandler("bierakgestorderiesgo", activar_admin))
    app.add_handler(MessageHandler(filters.PHOTO, recibir_imagen))
    app.add_handler(CallbackQueryHandler(boton_handler))

    print("🤖 Bot en ejecución...")
    app.run_polling()

if __name__ == "__main__":
    main()
