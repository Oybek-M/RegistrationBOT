from telegram import (
    Update, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove,
    InlineKeyboardButton, InlineKeyboardMarkup
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ConversationHandler, CallbackQueryHandler, ContextTypes, filters
)
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta

# — States for conversation —
ASK_PHONE, ASK_ISM, ASK_YOSHI, ASK_INGLIZ, ASK_QAYER, ASK_KIDS, ASK_MABLAG = range(7)

# — BOT va Sheet sozlamalari —
BOT_TOKEN    = "7699805832:AAHONDohmkHNsMuXRb2v2g_VFKoe7ypjhJ8"
BOT_USERNAME = "KidsAcademy_Ibrat_bot"
SHEET_ID     = "1thEJ61H9z1Qt70ye53xGOLHm5SDgLoaPQYkSsHdGqGo"
SERVICE_FILE = "credentials.json"

# — Google Sheets bilan avtorizatsiya —
scope = ["https://spreadsheets.google.com/feeds","https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name(SERVICE_FILE, scope)
gc    = gspread.authorize(creds)
sheet = gc.open_by_key(SHEET_ID).worksheet("Sheet1")

def uzb_now_iso():
    """UTC+5 ga o‘tkazib, ISO formatga keltiradi."""
    return (datetime.utcnow() + timedelta(hours=5)) \
           .isoformat(sep=' ', timespec='seconds')


async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    # 1) Tekshir: foydalanuvchi allaqachon ro'yxatda bormi?
    existing = sheet.findall(str(user_id))
    if existing:
        # Ha bo'lsa → faqat referral tugmasi, balansni oshirmaymiz
        sheet.update_cell(existing[0].row, 10, uzb_now_iso())  # last_edited_datetime yangilash

        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton(
                "🔗 Mening Referral Linkim",
                callback_data="get_referral"
            )
        ]])
        await update.message.reply_text(
            "👋 Siz allaqachon ro‘yxatdan o‘tgansiz.\n"
            "Quyidagi tugma orqali referral link’ingizni oling:",
            reply_markup=keyboard
        )
        return ConversationHandler.END

    # 2) Yangi foydalanuvchi: referral bal oshirish (agar ?start=referrer_id bo'lsa)
    args   = context.args
    ref_id = args[0] if args else None
    if ref_id:
        ref_cells = sheet.findall(str(ref_id))
        if ref_cells:
            ref_row = ref_cells[0].row
            current_bal = int(sheet.cell(ref_row, 7).value or 0)
            sheet.update_cell(ref_row, 7, current_bal + 1)

    # 3) Yangi user_data tayyorlash
    user = update.effective_user
    context.user_data.clear()
    context.user_data.update({
        "user_id":     user_id,
        "referrer_id": ref_id,
        "username":    user.username or "",
        "firstname":   user.first_name or "",
        "lastname":    user.last_name or "",
        "balance":     0
    })

    # 4) Telefon raqam so'rash
    button = KeyboardButton("📱 Telefon raqamni yuborish", request_contact=True)
    kb     = ReplyKeyboardMarkup([[button]], one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text(
        "📱 Iltimos, telefon raqamingizni yuboring:", reply_markup=kb
    )
    return ASK_PHONE


async def handle_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    contact = update.message.contact
    context.user_data["phonenumber"] = (
        contact.phone_number if contact else update.message.text
    )
    await update.message.reply_text("1. Ismingiz")
    return ASK_ISM


async def handle_ism(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Bu “ismingiz” ustuni uchun userning javobi
    context.user_data["ismingiz"] = update.message.text
    await update.message.reply_text("2. Farzandingiz yoshi")
    return ASK_YOSHI


async def handle_yoshi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["farzandingiz_yoshi"] = update.message.text
    await update.message.reply_text("3. Farzandingiznining ingliz tili darajasi ")
    return ASK_INGLIZ


async def handle_ingliz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["ingliz_tili_darajasi"] = update.message.text
    await update.message.reply_text("4. Qayerda yashaysiz?")
    return ASK_QAYER


async def handle_qayer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["qayerda_yashaysiz"] = update.message.text
    await update.message.reply_text("5. KIDS ACADEMY haqida qayerdan eshitdingiz?")
    return ASK_KIDS


async def handle_kids(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["kids_academy_haqida_qayerdan_eshitdingiz"] = update.message.text
    await update.message.reply_text("6. Farzandingiz ta'limi uchun qancha mablag' ajrata olasiz?")
    return ASK_MABLAG


async def handle_mablag(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["farzandingiz_uchun_qancha_mablag_ajrata_olasiz"] = update.message.text

    data = context.user_data
    # Jadvalga yoziladigan qator: profildan olgan firstname, lastname va “ismingiz” javob
    row = [
        data["user_id"], data["referrer_id"], data["username"],
        data["phonenumber"], data["firstname"], data["lastname"],
        data["balance"],
        f"https://t.me/{BOT_USERNAME}?start={data['user_id']}",
        uzb_now_iso(),  # created_datetime
        uzb_now_iso(),  # last_edited_datetime
        data["ismingiz"],                # foydalanuvchi yozgan ism
        data["farzandingiz_yoshi"],
        data["ingliz_tili_darajasi"], 
        data["qayerda_yashaysiz"],
        data["kids_academy_haqida_qayerdan_eshitdingiz"],
        data["farzandingiz_uchun_qancha_mablag_ajrata_olasiz"]
    ]
    sheet.append_row(row)               # append_row orqali saqlaymiz :contentReference[oaicite:6]{index=6}
    await update.message.reply_text(
        "✅ Ro‘yxatdan o‘tdingiz va ma’lumotlaringiz saqlandi!"
    )

    # Ro‘yxatdan o‘tganidan keyin ham referral tugmasini ko‘rsatamiz
    link = f"https://t.me/{BOT_USERNAME}?start={data['user_id']}"
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("🔗 Mening Referral Linkim", callback_data="get_referral")
    ]])
    await update.message.reply_text(
        "Referral link’ingizni olish uchun quyidagi tugmani bosing:",
        reply_markup=keyboard
    )
    return ConversationHandler.END


async def referral_button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    cells = sheet.findall(str(user_id))
    if not cells:
        await query.edit_message_text(
            "❗ Siz avval ro‘yxatdan o‘tmagansiz. /start orqali boshlang."
        )
        return

    row  = cells[0].row
    link = sheet.cell(row, 8).value   # referral_link ustunidan o‘qiymiz
    await query.edit_message_text(f"🔗 Sizning referral link’ingiz:\n{link}")


# ConversationHandler sozlash
conv_handler = ConversationHandler(
    entry_points=[CommandHandler("start", handle_start)],
    states={
        ASK_PHONE:  [MessageHandler(filters.CONTACT | filters.TEXT, handle_phone)],
        ASK_ISM:    [MessageHandler(filters.TEXT  & ~filters.COMMAND, handle_ism)],
        ASK_YOSHI:  [MessageHandler(filters.TEXT  & ~filters.COMMAND, handle_yoshi)],
        ASK_INGLIZ: [MessageHandler(filters.TEXT  & ~filters.COMMAND, handle_ingliz)],
        ASK_QAYER:  [MessageHandler(filters.TEXT  & ~filters.COMMAND, handle_qayer)],
        ASK_KIDS:   [MessageHandler(filters.TEXT  & ~filters.COMMAND, handle_kids)],
        ASK_MABLAG: [MessageHandler(filters.TEXT  & ~filters.COMMAND, handle_mablag)],
    },
    fallbacks=[]
)

if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(conv_handler)
    app.add_handler(CallbackQueryHandler(referral_button_callback, pattern="^get_referral$"))
    app.run_polling()
