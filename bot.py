import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

TOKEN = "7363306203:AAHWOgT18WdrHuH-EM6aYB6K5ahA3Ip0MgA"

# Зберігаємо скарги тимчасово в пам'яті (пізніше можна підключити базу)
complaints = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Поскаржитись на шахрая", callback_data='complaint')],
        [InlineKeyboardButton("Залишити позитивний відгук", callback_data='positive')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text('Виберіть дію:', reply_markup=reply_markup)

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if query.data == 'complaint':
        complaints[user_id] = {'type': 'complaint'}
        await query.message.reply_text('Введіть нік або посилання на продавця:')
        return
    elif query.data == 'positive':
        complaints[user_id] = {'type': 'positive'}
        await query.message.reply_text('Введіть нік або посилання на продавця:')
        return

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text

    if user_id not in complaints or 'nick' not in complaints[user_id]:
        complaints.setdefault(user_id, {})['nick'] = text
        await update.message.reply_text('Опишіть суть ситуації:')
    elif 'description' not in complaints[user_id]:
        complaints[user_id]['description'] = text
        await update.message.reply_text('Вкажіть суму (якщо є):')
    elif 'amount' not in complaints[user_id]:
        complaints[user_id]['amount'] = text
        await update.message.reply_text('Надішліть фото або скріншоти (або напишіть "Пропустити"):')
    elif 'photo' not in complaints[user_id]:
        if update.message.photo:
            file_id = update.message.photo[-1].file_id
            complaints[user_id]['photo'] = file_id
            await update.message.reply_text('Дякую! Ваша скарга/відгук прийнята на перевірку.')
            await notify_admin(update, context, complaints[user_id])
            complaints.pop(user_id)  # очистити дані користувача
        elif update.message.text and update.message.text.lower() == 'пропустити':
            complaints[user_id]['photo'] = None
            await update.message.reply_text('Дякую! Ваша скарга/відгук прийнята на перевірку.')
            await notify_admin(update, context, complaints[user_id])
            complaints.pop(user_id)
        else:
            await update.message.reply_text('Будь ласка, надішліть фото або напишіть "Пропустити".')

async def notify_admin(update: Update, context: ContextTypes.DEFAULT_TYPE, data):
    admin_id = 840077699  # твій ID
    msg = f"Нова заявка ({data['type']}):\n\n"
    msg += f"Продавець: {data.get('nick')}\n"
    msg += f"Опис: {data.get('description')}\n"
    msg += f"Сума: {data.get('amount')}\n"

    keyboard = [
        [
            InlineKeyboardButton("✅ Прийняти", callback_data='approve'),
            InlineKeyboardButton("❌ Відхилити", callback_data='reject')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if data.get('photo'):
        await context.bot.send_photo(chat_id=admin_id, photo=data['photo'], caption=msg, reply_markup=reply_markup)
    else:
        await context.bot.send_message(chat_id=admin_id, text=msg, reply_markup=reply_markup)

async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == 'approve':
        # Публікуємо у канал
        text = query.message.caption or query.message.text
        channel_id = '@olx_checker'  # ваш канал
        if query.message.photo:
            await context.bot.send_photo(chat_id=channel_id, photo=query.message.photo[-1].file_id, caption=text)
        else:
            await context.bot.send_message(chat_id=channel_id, text=text)
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text('Опубліковано у канал.')
    elif query.data == 'reject':
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text('Відхилено.')

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button, pattern='^(complaint|positive)$'))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), text_handler))
    app.add_handler(CallbackQueryHandler(admin_callback, pattern='^(approve|reject)$'))

    app.run_polling()

if __name__ == '__main__':
    main()
