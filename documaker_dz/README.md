# DocuMaker DZ — صانع الوثائقيات

تطبيق سطح مكتب لويندوز (Python + PySide6 + FFmpeg + Edge-TTS + Pexels + PyInstaller) لإنتاج فيديوهات وثائقية كاملة بصيغة MP4 انطلاقاً من عنوان واحد، بواجهة عربية افتراضية (RTL) ومن دون نافذة طرفية.

## التشغيل من المصدر
```bash
cd documaker_dz
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

## التغليف كملف تنفيذي لويندوز (`DocuMakerDZ.exe`)
1. ضع ملفّي `ffmpeg.exe` و `ffprobe.exe` داخل المجلد `documaker_dz/bin/` (اختياري لتضمينهما داخل الـ `.exe`).
2. شغّل `build_exe.bat` على نظام ويندوز.
3. ستجد الملف النهائي بدون نافذة طرفية مع الأيقونة المخصصة في:
   `documaker_dz/dist/DocuMakerDZ.exe`

## الاختبارات الآلية
```bash
python -m unittest discover -s documaker_dz/tests -v
```
