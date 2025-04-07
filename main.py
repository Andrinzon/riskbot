import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, CallbackContext

# Lista de usuarios que han interactuado con el bot
usuarios = set()
admin_mode = False

# Diccionario de niveles de riesgo por moneda
niveles_riesgo = {}

# Alias de monedas
alias_monedas = {
    "btc": "bitcoin", "eth": "ethereum", "bnb": "binancecoin",
    "xrp": "ripple", "sol": "solana", "ada": "cardano"
}
monedas_validas = list(alias_monedas.values())

# Colores para cada nivel de riesgo
colores_riesgo = {
    1: "🔸 (Muy bajo)", 2: "🔵 (Bajo)", 3: "🔹 (Moderado bajo)",
    4: "🟢 (Moderado)", 5: "💚 (Medio)", 6: "💛 (Medio-alto)",
    7: "🟡 (Alto)", 8: "🔶 (Muy alto)", 9: "🔴 (Riesgoso)", 10: "🔥 (Extremo)"
}

# Obtener precio de una criptomoneda
def obtener_precio(moneda):
    try:
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={moneda}&vs_currencies=usd"
        response = requests.get(url)
        data = response.json()
        return data[moneda]["usd"] if moneda in data else None
    except Exception:
        return None

# Comando /precio
async def precio(update: Update, context: CallbackContext):
    usuarios.add(update.message.chat_id)
    if len(context.args) == 0:
        mensaje = "💰 *Precios de criptomonedas:*\n"
        for clave, nombre in alias_monedas.items():
            price = obtener_precio(nombre)
            mensaje += f"💰 *{clave.upper()}*: ${price:,.2f}\n" if price else f"❌ {clave.upper()}: Error\n"
        await update.message.reply_text(mensaje, parse_mode="Markdown")
        return

    moneda = alias_monedas.get(context.args[0].lower(), context.args[0].lower())
    if moneda not in monedas_validas:
        await update.message.reply_text("❌ Moneda no soportada.")
        return

    price = obtener_precio(moneda)
    await update.message.reply_text(f"💰 *{moneda.upper()}*: ${price:,.2f}", parse_mode="Markdown") if price else await update.message.reply_text("❌ Error al obtener el precio.")

# Comando /riesgo (solo admin)
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
    await update.message.reply_text(f"✅ Riesgo de *{moneda.upper()}* asignado a {nivel} {color_riesgo}.", parse_mode="Markdown")

    for user_id in usuarios:
        await context.bot.send_message(user_id, f"⚠️ El riesgo de {moneda.upper()} ha cambiado. ¡Échale un vistazo!")

# Comando /verriesgo
async def mostrar_riesgo(update: Update, context: CallbackContext):
    if len(context.args) == 0:
        mensaje = "📊 *Niveles de riesgo:*\n"
        for moneda, nivel in niveles_riesgo.items():
            color_riesgo = colores_riesgo.get(nivel, "❔")
            mensaje += f"⚠️ *{moneda.upper()}*: Nivel {nivel}/10 {color_riesgo}\n"
        await update.message.reply_text(mensaje, parse_mode="Markdown")
        return

    moneda = alias_monedas.get(context.args[0].lower(), context.args[0].lower())
    if moneda not in monedas_validas:
        await update.message.reply_text("❌ Moneda no soportada.")
        return

    nivel = niveles_riesgo.get(moneda, "No asignado")
    color_riesgo = colores_riesgo.get(nivel, "❔") if isinstance(nivel, int) else ""
    await update.message.reply_text(f"⚠️ *Riesgo de {moneda.upper()}*: {nivel}/10 {color_riesgo}", parse_mode="Markdown")

# Comando secreto para activar el modo admin
async def activar_admin(update: Update, context: CallbackContext):
    global admin_mode
    admin_mode = True
    await update.message.reply_text("🔑 Modo administrador activado. Ahora puedes modificar riesgos.")

# Comando /start con botones
async def start(update: Update, context: CallbackContext):
    usuarios.add(update.message.chat_id)
    mensaje = (
        "🤖 ¡Bienvenido!\n\n"
        "📌 *Comandos disponibles:*\n"
        "🔹 /precio [moneda] - Ver precio\n"
        "🔹 /verriesgo [moneda] - Ver riesgo\n\n"
        "👇 Aquí tienes accesos rápidos:"
    )

    botones = [
        [InlineKeyboardButton("📊 Riesgo BTC", callback_data="verriesgo btc")],
        [InlineKeyboardButton("💰 Precio BTC", callback_data="precio btc")]
    ]

    reply_markup = InlineKeyboardMarkup(botones)
    await update.message.reply_text(mensaje, parse_mode="Markdown", reply_markup=reply_markup)

# Manejar botones
async def manejar_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    data = query.data.split(" ")
    comando = data[0]
    moneda = data[1] if len(data) > 1 else ""

    if comando == "verriesgo":
        context.args = [moneda]
        await mostrar_riesgo(update, context)
    elif comando == "precio":
        context.args = [moneda]
        await precio(update, context)

# Inicializar el bot
def main():
    TOKEN = "7883868261:AAFy-KbQk8BT1JnmLhXwAVK8udJef84T2_Q"
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("precio", precio))
    app.add_handler(CommandHandler("riesgo", establecer_riesgo))
    app.add_handler(CommandHandler("verriesgo", mostrar_riesgo))
    app.add_handler(CommandHandler("bierakgestorderiesgo", activar_admin))
    app.add_handler(CallbackQueryHandler(manejar_callback))

    print("🤖 Bot en ejecución...")
    app.run_polling()

if __name__ == "__main__":
    main()
