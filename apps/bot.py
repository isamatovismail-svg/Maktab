import logging
import datetime
from asgiref.sync import sync_to_async
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters, CallbackQueryHandler
)

from apps.models import Student, Grade, Timetable, Attendance, Homework, Quiz, Question, QuizResult

logging.basicConfig(level=logging.INFO)

@sync_to_async
def get_student_by_telegram_id(telegram_id):
    return Student.objects.filter(telegram_id=str(telegram_id)).select_related('grade_class').first()

@sync_to_async
def link_student_telegram(phone_or_name, telegram_id):
    clean_text = phone_or_name.strip()
    qs = Student.objects.select_related('grade_class')
    st = qs.filter(phone__icontains=clean_text).first()
    if not st:
        st = qs.filter(parent_phone__icontains=clean_text).first()
    if not st:
        parts = clean_text.split()
        if len(parts) >= 2:
            st = qs.filter(first_name__icontains=parts[0], last_name__icontains=parts[1]).first()
            if not st:
                st = qs.filter(first_name__icontains=parts[1], last_name__icontains=parts[0]).first()
        if not st:
            st = qs.filter(first_name__icontains=clean_text).first()
        if not st:
            st = qs.filter(last_name__icontains=clean_text).first()
    if st:
        st.telegram_id = str(telegram_id)
        st.save()
        return st
    return None

@sync_to_async
def get_student_grades(student):
    return list(Grade.objects.filter(student=student).select_related('subject')[:6])

@sync_to_async
def get_student_timetable(student):
    if not student.grade_class:
        return []
    today_num = datetime.date.today().isoweekday()
    return list(Timetable.objects.filter(grade_class=student.grade_class, day_of_week=today_num).select_related('subject', 'teacher'))

@sync_to_async
def get_student_attendance(student):
    return list(Attendance.objects.filter(student=student).select_related('subject')[:5])

@sync_to_async
def get_student_homework(student):
    if not student.grade_class:
        return []
    return list(Homework.objects.filter(grade_class=student.grade_class, due_date__gte=datetime.date.today()).select_related('subject')[:5])

@sync_to_async
def get_active_quizzes():
    return list(Quiz.objects.select_related('subject').all()[:5])


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tg_id = update.effective_user.id
    student = await get_student_by_telegram_id(tg_id)

    if student:
        text = (
            f"🌟 **Xush kelibsiz, {student.first_name} {student.last_name}!**\n"
            f"Sinfingiz: **{student.grade_class.name if student.grade_class else 'Biriktirilmagan'}**\n\n"
            "Bot orqali quyidagi ma'lumotlarni olishingiz mumkin:\n"
            "📊 /baholar — So'nggi baholaringiz\n"
            "📅 /jadval — Bugungi dars jadvalingiz\n"
            "📋 /yoqlama — Davomat ko'rsatgichingiz\n"
            "📚 /vazifa — Uyga vazifalaringiz\n"
            "🧠 /test — Test topshirish (Bilim)"
        )
    else:
        text = (
            "👋 **Smart Maktab Telegram Botiga Xush Kelibsiz!**\n\n"
            "Tizimdan foydalanish uchun akkauntingizni bog'lash kerak.\n"
            "Telefon raqamingizni yoki ismingizni yuboring (masalan: `Ismail` yoki `+998901234567`):"
        )

    await update.message.reply_text(text, parse_mode='Markdown')


async def baholar_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    student = await get_student_by_telegram_id(update.effective_user.id)
    if not student:
        await update.message.reply_text("⚠️ Avval botga registratsiya qilishingiz kerak! /start bo'limiga o'ting.")
        return

    grades = await get_student_grades(student)
    if not grades:
        await update.message.reply_text("📋 Sizda hali baholar yo'q.")
        return

    res = f"📊 **{student.first_name}ning So'nggi Baholari:**\n\n"
    for g in grades:
        res += f"• {g.subject.icon} **{g.subject.name}:** {g.score} ball ({g.date.strftime('%d.%m.%Y')})\n"

    await update.message.reply_text(res, parse_mode='Markdown')


async def jadval_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    student = await get_student_by_telegram_id(update.effective_user.id)
    if not student:
        await update.message.reply_text("⚠️ Avval botga registratsiya qilishingiz kerak!")
        return

    timetable = await get_student_timetable(student)
    if not timetable:
        await update.message.reply_text("📅 Bugun uchun dars jadvali kiritilmagan.")
        return

    res = f"📅 **{student.grade_class.name} Sinfining Bugungi Dars Jadvali:**\n\n"
    for t in timetable:
        res += f"⏰ `{t.time_slot}` — {t.subject.icon} **{t.subject.name}** ({t.room or 'Xonasiz'})\n"

    await update.message.reply_text(res, parse_mode='Markdown')


async def yoqlama_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    student = await get_student_by_telegram_id(update.effective_user.id)
    if not student:
        await update.message.reply_text("⚠️ Avval botga registratsiya qilishingiz kerak!")
        return

    attendances = await get_student_attendance(student)
    if not attendances:
        await update.message.reply_text("📋 Davomat ma'lumotlari topilmadi.")
        return

    res = f"📋 **{student.first_name}ning Davomat Yozuvlari:**\n\n"
    status_map = {'B': '✅ Bor', 'K': '⏰ Kech qoldi', 'Y': '❌ Yo\'q (Sababsiz)', 'S': 'ℹ️ Sababli'}
    for a in attendances:
        res += f"• {a.date.strftime('%d.%m.%Y')} — {a.subject.name}: **{status_map.get(a.status, a.status)}**\n"

    await update.message.reply_text(res, parse_mode='Markdown')


async def vazifa_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    student = await get_student_by_telegram_id(update.effective_user.id)
    if not student:
        await update.message.reply_text("⚠️ Avval botga registratsiya qilishingiz kerak!")
        return

    hws = await get_student_homework(student)
    if not hws:
        await update.message.reply_text("📚 Hozirda faol uyga vazifalar yo'q.")
        return

    res = f"📚 **{student.grade_class.name} Sinfining Uyga Vazifalari:**\n\n"
    for h in hws:
        res += f"📌 **{h.subject.icon} {h.subject.name}:** {h.title}\n"
        res += f"📝 _{h.description}_\n"
        res += f"⏰ Muddat: {h.due_date.strftime('%d.%m.%Y')}\n\n"

    await update.message.reply_text(res, parse_mode='Markdown')


async def test_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    student = await get_student_by_telegram_id(update.effective_user.id)
    if not student:
        await update.message.reply_text("⚠️ Avval botga registratsiya qilishingiz kerak!")
        return

    quizzes = await get_active_quizzes()
    if not quizzes:
        await update.message.reply_text("🧠 Hozirda faol testlar yo'q.")
        return

    res = "🧠 **Mavjud Testlar Ro'yxati:**\n\n"
    for q in quizzes:
        sub_name = q.subject.name if q.subject else 'Umumiy'
        icon = q.subject.icon if q.subject else '📝'
        res += f"• {icon} **{q.title}** ({sub_name})\n"
        res += f"  ⏱ Vaqt: {q.time_limit_minutes} daqiqa\n\n"

    res += "💡 Testlarni onlayn yechish uchun saytga kiring:\nhttp://127.0.0.1:8080/quizzes/"

    await update.message.reply_text(res, parse_mode='Markdown')



async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tg_id = update.effective_user.id
    st = await get_student_by_telegram_id(tg_id)
    if st:
        await update.message.reply_text("💡 Buyruqlar ro'yxatini ko'rish uchun menyudan foydalaning: /baholar, /jadval, /yoqlama, /vazifa, /test")
        return

    text = update.message.text.strip()
    linked_st = await link_student_telegram(text, tg_id)
    if linked_st:
        await update.message.reply_text(
            f"✅ **Muvaffaqiyatli bog'landi!**\n"
            f"Xush kelibsiz, **{linked_st.first_name} {linked_st.last_name}** ({linked_st.grade_class.name if linked_st.grade_class else 'Sinfsiz'}).\n\n"
            "Endi siz /baholar, /jadval, /yoqlama, /vazifa, /test buyruqlaridan foydalanishingiz mumkin!",
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text("❌ O'quvchi topilmadi. Iltimos, ismingizni yoki bazaga kiritilgan telefon raqamingizni to'g'ri yozing.")


def create_bot_app(token: str):
    app = ApplicationBuilder().token(token).build()
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("baholar", baholar_command))
    app.add_handler(CommandHandler("jadval", jadval_command))
    app.add_handler(CommandHandler("yoqlama", yoqlama_command))
    app.add_handler(CommandHandler("vazifa", vazifa_command))
    app.add_handler(CommandHandler("test", test_command))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), text_handler))
    return app

