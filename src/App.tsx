import { CheckCircle2, Film, FolderOpen, KeyRound, Languages, Mic, Music, Package, ShieldCheck, Terminal } from 'lucide-react';

const MODULES = [
  { name: 'documaker_dz/main.py', desc: 'نقطة تشغيل واجهة PySide6 بدون نافذة طرفية مع معالجة أخطاء محلية' },
  { name: 'documaker_dz/ui/main_window.py', desc: 'الشاشات السبع الكاملة (إنشاء فيديو، المكتبة، محرر السكربت، الصوت، الموسيقى، المرئيات، الإعدادات)' },
  { name: 'documaker_dz/core/job_queue.py', desc: 'محرك خط الإنتاج ذو 9 خطوات مع الإلغاء والاستئناف من الخطوة المتوقفة' },
  { name: 'documaker_dz/core/security.py', desc: 'تشفير مفاتيح API محلياً عبر Windows DPAPI أو Fernet/HMAC' },
  { name: 'documaker_dz/ai/*', desc: 'المدير الإبداعي، وكيل البحث والمصادر، كاتب السكربت، مخطط المشاهد، ومراجع الجودة' },
  { name: 'documaker_dz/media/*', desc: 'Edge-TTS المجاني مع التوقيت الدقيق، Pexels للصور والفيديو، Pixabay و Wikimedia' },
  { name: 'documaker_dz/production/*', desc: 'معالجة FFmpeg الصامتة، Ken Burns، خفض صوت الموسيقى، الترجمة .srt/.ass، وإخراج MP4 720p' },
  { name: 'documaker_dz/documaker.spec & build_exe.bat', desc: 'ملف تغليف PyInstaller (--noconsole) مع أيقونة ويندوز مخصصة assets/icon.ico' },
];

const PIPELINE_STEPS = [
  '1. البحث وجمع المعلومات الموثقة والمصادر',
  '2. كتابة السكربت الوثائقي بالعربية الفصحى',
  '3. تخطيط المشاهد واستخراج الكلمات المفتاحية',
  '4. توليد التعليق الصوتي عبر Edge-TTS لكل مشهد',
  '5. جلب الصور ومقاطع الفيديو المرخصة من Pexels',
  '6. اختيار ومزج الموسيقى التصويرية',
  '7. إنشاء ملفات الترجمة المتزامنة (.srt و .ass)',
  '8. مزامنة وتجميع المشاهد بحركة Ken Burns',
  '9. تصدير الفيديو النهائي MP4 بدقة 720p',
];

export default function App() {
  return (
    <div dir="rtl" className="min-h-screen bg-slate-950 text-slate-100">
      <div className="mx-auto max-w-6xl px-6 py-10">
        {/* Header */}
        <header className="mb-10 flex flex-col gap-4 border-b border-slate-800 pb-8 md:flex-row md:items-center md:justify-between">
          <div className="flex items-center gap-4">
            <div className="flex h-14 w-14 items-center justify-center rounded-2xl border border-emerald-500/40 bg-slate-900 text-amber-400 shadow-lg">
              <Film className="h-7 w-7" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-emerald-400">صانع الوثائقيات — DocuMaker DZ</h1>
              <p className="text-sm text-slate-400">
                تطبيق سطح مكتب لويندوز (Python + PySide6 + FFmpeg + Edge-TTS + Pexels + PyInstaller)
              </p>
            </div>
          </div>
          <div className="flex flex-wrap gap-2 text-xs">
            <span className="rounded-lg border border-emerald-500/30 bg-emerald-950/60 px-3 py-1.5 text-emerald-300">
              واجهة عربية RTL افتراضياً
            </span>
            <span className="rounded-lg border border-amber-500/30 bg-amber-950/50 px-3 py-1.5 text-amber-300">
              مناسب لأجهزة 4 GB RAM
            </span>
          </div>
        </header>

        {/* Architecture & Pipeline */}
        <div className="grid gap-6 lg:grid-cols-2">
          <section className="rounded-2xl border border-slate-800 bg-slate-900/70 p-6">
            <h2 className="mb-4 flex items-center gap-2 text-lg font-bold text-slate-100">
              <FolderOpen className="h-5 w-5 text-emerald-400" />
              هيكل الحزمة البرمجية في مساحة العمل
            </h2>
            <div className="space-y-3">
              {MODULES.map((m) => (
                <div key={m.name} className="rounded-xl border border-slate-800 bg-slate-950/70 p-3">
                  <div className="font-mono text-xs font-semibold text-emerald-300" dir="ltr">
                    {m.name}
                  </div>
                  <div className="mt-1 text-sm text-slate-300">{m.desc}</div>
                </div>
              ))}
            </div>
          </section>

          <section className="space-y-6">
            <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-6">
              <h2 className="mb-4 flex items-center gap-2 text-lg font-bold text-slate-100">
                <CheckCircle2 className="h-5 w-5 text-emerald-400" />
                خط الإنتاج الآلي (9 مراحل قابلة للاستئناف)
              </h2>
              <ul className="space-y-2 text-sm text-slate-300">
                {PIPELINE_STEPS.map((step) => (
                  <li key={step} className="rounded-lg border border-slate-800/80 bg-slate-950/60 px-3 py-2">
                    {step}
                  </li>
                ))}
              </ul>
            </div>

            <div className="rounded-2xl border border-amber-500/30 bg-amber-950/20 p-6">
              <h2 className="mb-3 flex items-center gap-2 text-lg font-bold text-amber-300">
                <Package className="h-5 w-5" />
                بناء ملف Windows .exe على جهاز ويندوز
              </h2>
              <p className="mb-3 text-sm leading-relaxed text-slate-300">
                تم تجهيز ملفات PyInstaller (<code className="text-amber-300">documaker.spec</code> و{' '}
                <code className="text-amber-300">build_exe.bat</code>) والأيقونة{' '}
                <code className="text-amber-300">assets/icon.ico</code> مع تعطيل نافذة الطرفية.
                لأن بيئة البناء الحالية تعمل على Linux، يتم توليد الملف التنفيذي النهائي{' '}
                <code className="text-emerald-300">DocuMakerDZ.exe</code> عند تشغيل{' '}
                <code className="text-amber-300">documaker_dz\build_exe.bat</code> على نظام Windows.
              </p>
              <div className="grid grid-cols-2 gap-3 text-xs text-slate-300 sm:grid-cols-3">
                <div className="flex items-center gap-2 rounded-lg bg-slate-900/80 p-2">
                  <Languages className="h-4 w-4 text-emerald-400" />
                  <span>عربي / فرنسي / إنجليزي</span>
                </div>
                <div className="flex items-center gap-2 rounded-lg bg-slate-900/80 p-2">
                  <Mic className="h-4 w-4 text-emerald-400" />
                  <span>Edge-TTS + توقيت دقيق</span>
                </div>
                <div className="flex items-center gap-2 rounded-lg bg-slate-900/80 p-2">
                  <Music className="h-4 w-4 text-emerald-400" />
                  <span>Audio Ducking آلي</span>
                </div>
                <div className="flex items-center gap-2 rounded-lg bg-slate-900/80 p-2">
                  <KeyRound className="h-4 w-4 text-emerald-400" />
                  <span>تشفير DPAPI للمفاتيح</span>
                </div>
                <div className="flex items-center gap-2 rounded-lg bg-slate-900/80 p-2">
                  <ShieldCheck className="h-4 w-4 text-emerald-400" />
                  <span>تحقق من التراخيص والمصادر</span>
                </div>
                <div className="flex items-center gap-2 rounded-lg bg-slate-900/80 p-2">
                  <Terminal className="h-4 w-4 text-emerald-400" />
                  <span>بدون نافذة طرفية</span>
                </div>
              </div>
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}
