# Supervision (Django + MySQL)

نظام لإدارة إشرافات الرسائل/الأبحاث: (باحث/رسالة) + (مشرف/مشرفين) + حالة + تواريخ.

## التشغيل السريع

### 1) جهّز قاعدة بيانات MySQL
```sql
CREATE DATABASE supervision_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 2) أنشئ ملف .env
انسخ `.env.example` إلى `.env` وعدّل بيانات MySQL:
```env
DJANGO_SECRET_KEY=change-me
DJANGO_DEBUG=1

DB_NAME=supervision_db
DB_USER=root
DB_PASSWORD=YOUR_PASSWORD
DB_HOST=127.0.0.1
DB_PORT=3306
```

### 3) ثبّت المتطلبات
```bash
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

pip install -r requirements.txt
```

### 4) Migrations + Admin user
```bash
python manage.py migrate
python manage.py createsuperuser
```

### 5) تشغيل
```bash
python manage.py runserver
```
افتح:
http://127.0.0.1:8000/admin

## استيراد الإكسيل
هذا المشروع يدعم حالتك: عمود المشرف فيه اسم واحد، لكن الباحث يتكرر في صفوف متعددة عند وجود أكثر من مشرف.

شغّل:
```bash
python manage.py import_supervisions path/to/your.xlsx
```

لو أسماء الأعمدة عندك مختلفة استخدم flags:
```bash
python manage.py import_supervisions data.xlsx \
  --col_degree "المرحلة" \
  --col_name "اسم الباحث" \
  --col_dept "القسم" \
  --col_title "عنوان الرسالة" \
  --col_supervisor "المشرف"
```

## التواريخ الجديدة
موجودة في Research وتُترك فارغة في الاستيراد:
- registration_date (تاريخ التسجيل)
- frame_date (تاريخ الإطار)
- university_approval_date (تاريخ موافقة الجامعة)
