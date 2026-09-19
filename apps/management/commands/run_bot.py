import os
from django.core.management.base import BaseCommand
from apps.bot import create_bot_app


class Command(BaseCommand):
    help = "Smart Maktab Telegram botini ishga tushirish buyrug'i"

    def add_arguments(self, parser):
        parser.add_argument('--token', type=str, help='Telegram Bot Token (.env dan olish mumkin)')

    def handle(self, *args, **options):
        token = options.get('token') or os.environ.get('TELEGRAM_BOT_TOKEN', '')
        if not token:
            self.stdout.write(self.style.ERROR(
                "Xato: TELEGRAM_BOT_TOKEN topilmadi. "
                ".env faylida yoki --token argumentida bering."
            ))
            return

        self.stdout.write(self.style.SUCCESS(f"🚀 Telegram Bot ishga tushirilmoqda..."))
        try:
            app = create_bot_app(token)
            self.stdout.write(self.style.SUCCESS("✅ Bot tayyor! Xabarlarni kutmoqda... (To'xtatish: Ctrl+C)"))
            app.run_polling(stop_signals=None)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Bot xatosi: {e}"))
