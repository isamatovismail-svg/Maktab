# 🏫 Smart Maktab — Maktab Boshqaruv Tizimi & Telegram Bot

**Smart Maktab** — bu umumta'lim maktablari va o'quv markazlari uchun mo'ljallangan, Django frameworkida yaratilgan zamonaviy boshqaruv platformasi hamda Telegram bot integratsiyasidir.

Ushbu loyiha o'quvchilar, o'qituvchilar, sinflar, baholar, davomat, imtihon natijalari va to'lovlarni tizimli nazorat qilish imkonini beradi.

---

## 🌟 Asosiy Imkoniyatlar (Features)

- **O'quvchilar va O'qituvchilar bazasi**: To'liq ma'lumotlar, profillar va rollar boshqaruvi.
- **Sinflar va Fanlar**: Sinflarni taqsimlash, fanlar va dars jadvallari.
- **Baholash tizimi**: Kundalik baholar va imtihon (test) natijalarini kiritish, tahlil qilish.
- **Davomat nazorati**: O'quvchilarning darslarga qatnashishini belgilash va hisobotlar.
- **To'lovlar (Finance)**: O'quvchilar to'lovlari monitoringi va turlari.
- **Telegram Bot integratsiyasi**:
  - Baholar va davomat haqida o'quvchi va ota-onalarga bildirishnomalar yuborish.
  - Kundalik jadvallar va yangiliklarni bot orqali ko'rish.
- **Demo ma'lumotlar**: Tizimni tez sinab ko'rish uchun maxsus boshqaruv buyrug'i.
- **To'liq test qamrovi**: `pytest` orqali tekshirilgan barqaror kod bazasi.

---

## 🛠 Texnologiyalar Stoki (Tech Stack)

- **Backend**: Python 3.10+, Django 5.x
- **Ma'lumotlar bazasi**: SQLite (boshlang'ich/dev), PostgreSQL ga moslashgan
- **Bot**: `python-telegram-bot` (v20+)
- **Frontend**: Django Templates, Bootstrap / Tailwind CSS
- **Testlar**: Pytest, Pytest-Django

---

## 🚀 O'rnatish va Ishga Tushirish (Quick Start)

Loyihani o'z kompyuteringizda ishga tushirish uchun quyidagi qadamlarni ketma-ket bajaring:

### 1. Loyihani klonlash (Clone repository)

```bash
git clone https://github.com/isamatovismail-svg/Maktab.git
cd Maktab
```

### 2. Virtual muhit (Virtual Environment) yaratish va faollashtirish

```bash
# Linux / macOS:
python3 -m venv .venv
source .venv/bin/activate

# Windows (PowerShell):
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### 3. Kerakli kutubxonalarni o'rnatish

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Muhit o'zgaruvchilarini (`.env`) sozlash

`.env.example` faylidan nusxa olib, yangi `.env` faylini hosil qiling:

```bash
cp .env.example .env
```

`.env` faylini oching va quyidagi qiymatlarni kiriting:
```ini
DEBUG=True
SECRET_KEY=django-insecure-your-secret-key-here
ALLOWED_HOSTS=127.0.0.1,localhost,testserver
TELEGRAM_BOT_TOKEN=sizning_telegram_bot_tokeningiz
```

### 5. Ma'lumotlar bazasini sozlash (Migrations)

```bash
python manage.py makemigrations
python manage.py migrate
```

### 6. Sinov foydalanuvchilarini yaratish (Demo Data)

Loyiha bilan tezda tanishish uchun quyidagi tayyor demo ma'lumotlarni yaratish buyrug'ini ishga tushiring:

```bash
python manage.py create_demo_users
```

> **Demo hisoblar:**
> - **O'qituvchi**: login `demo_ustoz`, parol `Ustoz@1234`
> - **O'quvchi**: login `demo_oquvchi`, parol `Oquvchi@1234`

Admin panelga kirish uchun superuser yaratishingiz ham mumkin:
```bash
python manage.py createsuperuser
```

### 7. Veb-serverni ishga tushirish

```bash
python manage.py runserver
```

Brauzerda quyidagi manzilni oching: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)  
Admin panel: [http://127.0.0.1:8000/admin/](http://127.0.0.1:8000/admin/)

### 8. Telegram Botni ishga tushirish (Alohida terminalda)

```bash
python manage.py run_bot
```

---

## 🧪 Testlarni Ishga Tushirish

Loyihada testlar to'g'ri ishlashiga ishonch hosil qilish uchun:

```bash
pytest
```

---

## 🤝 Loyihani O'zgartirish va Hissa Qo'shish (Contributing)

Ushbu loyiha ochiq manbali bo'lib, har kim kodni ko'rishi, o'zgartirishi va rivojlantirishi mumkin!

Agar yangi xususiyat qo'shmoqchi bo'lsangiz yoki xatolikni to'g'rilamoqchi bo'lsangiz:

1. Loyihani o'z profilingizga **Fork** qiling.
2. Yangi tarmoq (branch) oching:
   ```bash
   git checkout -b feature/yangi-imkoniyat
   ```
3. O'zgarishlarni kiriting va commit qiling:
   ```bash
   git commit -m "feat: Yangi imkoniyat qo'shildi"
   ```
4. O'z fork-omboringizga yuboring (push):
   ```bash
   git push origin feature/yangi-imkoniyat
   ```
5. GitHub'da **Pull Request (PR)** oching!

---

## 📄 Litsenziya

Ushbu loyiha [MIT Litsenziyasi](LICENSE) asosida tarqatiladi. Siz undan erkin foydalanishingiz, nusxa olishingiz va o'zgartirishingiz mumkin.