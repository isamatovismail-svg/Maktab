import datetime
import logging
import re
from asgiref.sync import sync_to_async
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters
)

from apps.models import Student, Grade, Timetable, Attendance, Homework, StudentFee

logger = logging.getLogger('apps')


def normalize_phone(phone_str: str) -> str:
    """Extract digits only for robust phone comparison."""
    if not phone_str:
        return ""
    digits = re.sub(r'\D', '', phone_str)
    # If starting with 998 and 12 digits, return 998...
    if len(digits) >= 9:
        return digits[-9:]  # match last 9 digits (e.g. 901234567)
    return digits


@sync_to_async
def get_student_by_telegram_id(telegram_id):
    return Student.objects.filter(telegram_id=str(telegram_id)).select_related('grade_class').first()


@sync_to_async
def link_student_telegram(identifier, telegram_id):
    """
    Securely link student by unique student_id (e.g. STU-12345) or registered phone number.
    Rejects ambiguous or loose text to prevent account takeover.
    """
    clean_text = identifier.strip()
    if not clean_text:
        return None, "Bo'sh ma'lumot yuborildi."

    qs = Student.objects.select_related('grade_class')

    # 1. Match by unique student_id (e.g. STU-12345)
    st = qs.filter(student_id__iexact=clean_text).first()

    # 2. Match by exact normalized phone
    if not st:
        digits = normalize_phone(clean_text)
        if len(digits) >= 9:
            for candidate in qs.exclude(phone='').exclude(phone__isnull=True):
                if normalize_phone(candidate.phone) == digits:
                    st = candidate
                    break
            if not st:
                for candidate in qs.exclude(parent_phone='').exclude(parent_phone__isnull=True):
                    if normalize_phone(candidate.parent_phone) == digits:
                        st = candidate
                        break

    if not st:
        return None, (
            "O'quvchi topilmadi. Iltimos, profilingizdagi O'quvchi ID raqamini (masalan: `STU-12345`) "
            "yoki ro'yxatdan o'tgan telefon raqamingizni kiriting."
        )

    # Prevent hijacking an already linked account with a different telegram ID
    if st.telegram_id and st.telegram_id != str(telegram_id):
        return None, (
            "Ushbu o'quvchi akkaunti allaqachon boshqa Telegram profiliga biriktirilgan. "
            "Iltimos, maktab ma'muriyatiga murojaat qiling."
        )

    st.telegram_id = str(telegram_id)
    st.save(update_fields=['telegram_id'])
    return st, None


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
def get_student_fees_data(student):
    """Safely calculates fee summaries inside sync context to avoid async DB queries."""
    fees = list(StudentFee.objects.filter(student=student).select_related('fee_type')[:10])
    data = []
    total_debt = 0.0
    for f in fees:
        balance = f.balance_due
        total_debt += balance
        data.append({
            'fee_type_name': f.fee_type.name,
            'balance': balance,
            'status': f.status,
            'due_date': f.due_date,
        })
    return data, total_debt


@sync_to_async
def get_next_lesson(student):
    if not student or not student.grade_class:
        return None, None
    today = datetime.date.today()
    today_num = today.isoweekday()
    for day_offset in range(7):
        check_day = (today_num + day_offset - 1) % 7 + 1
        lessons = list(Timetable.objects.filter(
            grade_class=student.grade_class, day_of_week=check_day
        ).select_related('subject', 'teacher').order_by('time_slot'))
        if lessons:
            return lessons[0], check_day
    return None, None


# ── Bot Commands ──────────────────────────────────────────────

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tg_id = update.effective_user.id
    student = await get_student_by_telegram_id(tg_id)

    if student:
        class_name = student.grade_class.name if student.grade_class else 'Biriktirilmagan'
        text = (
            f"🌟 **Xush kelibsiz, {student.first_name} {student.last_name}!**\n"
            f"Sinfingiz: **{class_name}**\n\n"
            "Bot orqali quyidagi ma'lumotlarni olishingiz mumkin:\n"
            "📊 /baholar — So'nggi baholaringiz\n"
            "📅 /jadval — Bugungi dars jadvalingiz\n"
            "📋 /yoqlama — Davomat ko'rsatgichingiz\n"
            "📚 /vazifa — Uyga vazifalaringiz\n"
            "💳 /tolov — To'lovlar holati\n"
            "👤 /profil — Profil ma'lumotlaringiz\n"
            "⏭ /keyingidars — Keyingi darsingiz"
        )
    else:
        text = (
            "👋 **Smart Maktab Telegram Botiga Xush Kelibsiz!**\n\n"
            "Tizimdan foydalanish uchun o'quvchi akkauntingizni bog'lash kerak.\n"
            "O'quvchi ID raqamingizni (masalan: `STU-12345`) yoki maktabga berilgan telefon raqamingizni yuboring:"
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
        icon = g.subject.icon if g.subject else '📚'
        sub_name = g.subject.name if g.subject else 'Fan'
        res += f"• {icon} **{sub_name}:** {g.score} ball ({g.date.strftime('%d.%m.%Y')})\n"

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

    class_name = student.grade_class.name if student.grade_class else "Sinf"
    res = f"📅 **{class_name} Sinfining Bugungi Dars Jadvali:**\n\n"
    for t in timetable:
        icon = t.subject.icon if t.subject else '📚'
        sub_name = t.subject.name if t.subject else 'Fan'
        res += f"⏰ `{t.time_slot}` — {icon} **{sub_name}** ({t.room or 'Xonasiz'})\n"

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
        sub_name = a.subject.name if a.subject else 'Fan'
        res += f"• {a.date.strftime('%d.%m.%Y')} — {sub_name}: **{status_map.get(a.status, a.status)}**\n"

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

    class_name = student.grade_class.name if student.grade_class else "Sinf"
    res = f"📚 **{class_name} Sinfining Uyga Vazifalari:**\n\n"
    for h in hws:
        icon = h.subject.icon if h.subject else '📌'
        sub_name = h.subject.name if h.subject else 'Fan'
        res += f"📌 **{icon} {sub_name}:** {h.title}\n"
        if h.description:
            res += f"📝 _{h.description}_\n"
        res += f"⏰ Muddat: {h.due_date.strftime('%d.%m.%Y')}\n\n"

    await update.message.reply_text(res, parse_mode='Markdown')


async def tolov_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    student = await get_student_by_telegram_id(update.effective_user.id)
    if not student:
        await update.message.reply_text("⚠️ Avval /start orqali akkauntingizni bog'lang.")
        return

    fees_data, total_debt = await get_student_fees_data(student)
    if not fees_data:
        await update.message.reply_text("✅ Sizda hozircha to'lovlar belgilanmagan.")
        return

    status_map = {'PENDING': '⏳ Kutilmoqda', 'PAID': '✅ To\'langan', 'PARTIAL': '🔶 Qisman', 'OVERDUE': '❌ Muddati o\'tgan'}
    res = f"💳 **{student.first_name}ning To'lovlari:**\n\n"
    for f in fees_data:
        status = status_map.get(f['status'], f['status'])
        balance = f['balance']
        res += f"• **{f['fee_type_name']}**: {balance:,.0f} UZS\n"
        res += f"  {status} | Muddat: {f['due_date'].strftime('%d.%m.%Y')}\n\n"

    res += f"━━━━━━━━━━━━━\n💰 **Jami qarzdorlik: {total_debt:,.0f} UZS**"
    await update.message.reply_text(res, parse_mode='Markdown')


async def profil_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    student = await get_student_by_telegram_id(update.effective_user.id)
    if not student:
        await update.message.reply_text("⚠️ Avval /start orqali akkauntingizni bog'lang.")
        return

    gender_map = {'M': '👨 Erkak', 'F': '👩 Ayol'}
    res = (
        f"👤 **Profil Ma'lumotlaringiz:**\n\n"
        f"📛 Ism-Familiya: **{student.first_name} {student.last_name}**\n"
        f"🆔 O'quvchi ID: `{student.student_id or 'Belgilanmagan'}`\n"
        f"🏫 Sinf: **{student.grade_class.name if student.grade_class else 'Biriktirilmagan'}**\n"
        f"📞 Telefon: {student.phone or 'Kiritilmagan'}\n"
        f"🧬 Jins: {gender_map.get(student.gender, student.gender)}\n"
        f"📅 Qabul sanasi: {student.admission_date.strftime('%d.%m.%Y') if student.admission_date else '—'}\n"
    )
    await update.message.reply_text(res, parse_mode='Markdown')


async def keyingidars_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    student = await get_student_by_telegram_id(update.effective_user.id)
    if not student:
        await update.message.reply_text("⚠️ Avval /start orqali akkauntingizni bog'lang.")
        return

    lesson, day_num = await get_next_lesson(student)

    if not lesson:
        await update.message.reply_text("📅 Keyingi dars topilmadi.")
        return

    days_uz = {1: 'Dushanba', 2: 'Seshanba', 3: 'Chorshanba', 4: 'Payshanba', 5: 'Juma', 6: 'Shanba'}
    teacher_name = f"{lesson.teacher.first_name} {lesson.teacher.last_name}" if lesson.teacher else "Belgilanmagan"
    icon = lesson.subject.icon if lesson.subject else '📚'
    sub_name = lesson.subject.name if lesson.subject else 'Fan'
    res = (
        f"⏭ **Keyingi Darsingiz:**\n\n"
        f"📚 Fan: **{icon} {sub_name}**\n"
        f"📅 Kun: **{days_uz.get(day_num, '?')}**\n"
        f"⏰ Vaqt: **{lesson.time_slot}**\n"
        f"🚪 Xona: **{lesson.room or 'Belgilanmagan'}**\n"
        f"👨‍🏫 O'qituvchi: **{teacher_name}**"
    )
    await update.message.reply_text(res, parse_mode='Markdown')


async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tg_id = update.effective_user.id
    st = await get_student_by_telegram_id(tg_id)
    if st:
        await update.message.reply_text(
            "💡 Buyruqlar ro'yxatini ko'rish uchun quyidagilardan foydalaning: "
            "/baholar, /jadval, /yoqlama, /vazifa, /tolov, /profil, /keyingidars"
        )
        return

    text = update.message.text.strip()
    linked_st, error = await link_student_telegram(text, tg_id)
    if linked_st:
        class_name = linked_st.grade_class.name if linked_st.grade_class else 'Sinfsiz'
        await update.message.reply_text(
            f"✅ **Muvaffaqiyatli bog'landi!**\n"
            f"Xush kelibsiz, **{linked_st.first_name} {linked_st.last_name}** ({class_name}).\n\n"
            "Endi siz /baholar, /jadval, /yoqlama, /vazifa, /tolov, /profil buyruqlaridan foydalanishingiz mumkin!",
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(f"❌ {error}", parse_mode='Markdown')


def create_bot_app(token: str):
    app = ApplicationBuilder().token(token).build()
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("baholar", baholar_command))
    app.add_handler(CommandHandler("jadval", jadval_command))
    app.add_handler(CommandHandler("yoqlama", yoqlama_command))
    app.add_handler(CommandHandler("vazifa", vazifa_command))
    app.add_handler(CommandHandler("tolov", tolov_command))
    app.add_handler(CommandHandler("profil", profil_command))
    app.add_handler(CommandHandler("keyingidars", keyingidars_command))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), text_handler))
    return app
