# ChainShield — درع الحماية من هجمات DDoS

> حماية خدماتك من هجمات الإغراق باستخدام خوارزميات مستوحاة من البلوكتشين

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://python.org)

---

## ما هو ChainShield؟

هجمات الـ DDoS تعمل ببساطة: مهاجم يرسل كميات ضخمة من الطلبات لخادمك حتى ينهار. الحل التقليدي هو الاعتماد على شركات خارجية مثل Cloudflare أو جدران الحماية المركزية — لكن هذا يعني أنك تثق بطرف ثالث وعندك نقطة فشل واحدة.

أبحاث البلوكتشين أثبتت فكرة ذكية: إذا وضعت قواعد الحماية داخل **Smart Contract** على شبكة Ethereum، تكون القواعد شفافة ولا أحد يقدر يتلاعب بها. المشكلة؟ تكلفة الـ Gas وبطء البلوكتشين تجعلها غير عملية للاستخدام الحقيقي.

**ChainShield يأخذ نفس الخوارزميات ويشغّلها في Python** — بدون Gas، بدون تأخير، جاهزة للإنتاج.

---

## كيف يعمل؟

يحمي ChainShield خدمتك بثلاث طبقات تعمل بالتسلسل:

```
┌──────────────────────────────────────────────┐
│                   Guardian                   │
│                                              │
│  طلب ──▶ [في القائمة السوداء؟] ──▶ [تجاوز الحد؟] ──▶ [حد عالمي؟] ──▶ قبول
│                    │                   │                 │
│                  رفض             رفض + حظر           رفض
└──────────────────────────────────────────────┘
```

### الطبقة الأولى: Sliding Window Rate Limiter

المشكلة مع العداد التراكمي (الطريقة البدائية): مستخدم يرسل 5 طلبات خلال 3 أشهر ← يُحجب إلى الأبد. هذا خطأ.

الـ Sliding Window يحل المشكلة: يعد الطلبات **خلال نافذة زمنية محددة فقط**. بعد انتهاء النافذة، العداد يُصفّر.

```
t=0s   طلب 1 ✓ (العد: 1/5)
t=10s  طلب 2 ✓ (العد: 2/5)
t=30s  طلب 3 ✓ (العد: 3/5)
t=45s  طلب 4 ✓ (العد: 4/5)
t=55s  طلب 5 ✓ (العد: 5/5)
t=61s  طلب 6 ✓ (نافذة انتهت! العد: 1/5) ← يُسمح له
```

### الطبقة الثانية: Temporary Blacklist (قائمة سوداء مؤقتة)

لما مستخدم يتجاوز الحد، يُوضع في القائمة السوداء لفترة محددة ثم يُحذف تلقائياً. مقارنة بالحل الأصلي في Solidity الذي أراد حجباً دائماً لكن باكتشف أن `revert` يلغي حالة البلوكتشين — هذا الخطأ لا يوجد في Python.

```
t=0s   طلب 1-5 ✓
t=0s   طلب 6   ✗ ← محجوب حتى t=30s (مثلاً)
t=15s  طلب 7   ✗ ← لا يزال محجوباً
t=31s  طلب 8   ✓ ← انتهى الحظر، مسموح له
```

### الطبقة الثالثة: Global Limit (الحد العالمي)

المشكلة مع الحد الفردي فقط: مهاجم يستخدم 1000 عنوان IP مختلف، كل عنوان يرسل 4 طلبات (أقل من الحد) = 4000 طلب بدون أي حجب.

الحل: حد عالمي يُحسب **مجموع كل الطلبات** من **جميع المستخدمين**. لما يُكتمل الحد، **الكل يُوقف** حتى تنتهي النافذة.

```
user-1 طلب ✓  (عالمي: 1/20)
user-2 طلب ✓  (عالمي: 2/20)
...
user-20 طلب ✓  (عالمي: 20/20)
user-21 طلب ✗  ← تجاوز الحد العالمي
```

---

## التثبيت

```bash
pip install chainshield
```

مع Flask:
```bash
pip install "chainshield[flask]"
```

مع FastAPI:
```bash
pip install "chainshield[fastapi]"
```

---

## الاستخدام الأساسي

```python
from chainshield import Guardian, GuardianConfig

# إعداد الحارس بالمعاملات المطلوبة
guardian = Guardian(
    GuardianConfig(
        max_requests=5,         # 5 طلبات لكل مستخدم
        window_size=60,         # داخل نافذة 60 ثانية
        blacklist_duration=30,  # الحجب لمدة 30 ثانية
        global_max_requests=100, # حد عالمي
    )
)

# فحص كل طلب قادم
decision = guardian.check("192.168.1.1")

if decision.allowed:
    # مسموح بالطلب
    serve_response()
else:
    # طلب محجوب
    print(f"محجوب — السبب: {decision.block_reason}")
```

---

## التكامل مع Flask

```python
from flask import Flask
from chainshield import Guardian, GuardianConfig
from chainshield.middleware import FlaskChainShield

app = Flask(__name__)

guardian = Guardian(GuardianConfig(max_requests=10, window_size=60))
FlaskChainShield(app, guardian)

@app.route("/api/بيانات")
def get_data():
    return {"رسالة": "مرحباً من نقطة نهاية محمية"}
```

الطلبات المحجوبة تستقبل تلقائياً:
```json
HTTP 429 Too Many Requests
Retry-After: 28

{
  "error": "Too Many Requests",
  "reason": "rate_limit_exceeded",
  "retry_after": "28"
}
```

---

## التكامل مع FastAPI

```python
from fastapi import FastAPI
from chainshield import Guardian
from chainshield.middleware import FastAPIChainShield

app = FastAPI()
app.add_middleware(FastAPIChainShield, guardian=Guardian())

@app.get("/api/بيانات")
async def get_data():
    return {"رسالة": "مرحباً"}
```

---

## مثال عملي كامل

هذا يشرح بالضبط ما يحدث:

```python
from chainshield import Guardian, GuardianConfig, BlockReason

g = Guardian(GuardianConfig(max_requests=3, window_size=60, blacklist_duration=10))

# مستخدمين مختلفين
users = ["أحمد", "سارة", "خالد"]

# أحمد يرسل 4 طلبات (الحد 3)
print("=== أحمد ===")
for i in range(1, 5):
    d = g.check("أحمد")
    status = "✓ مقبول" if d.allowed else f"✗ محجوب ({d.block_reason.value})"
    print(f"  طلب {i}: {status}")

# سارة غير متأثرة بحجب أحمد
print("\n=== سارة ===")
d = g.check("سارة")
print(f"  طلب 1: {'✓ مقبول' if d.allowed else '✗ محجوب'}")

# إحصائيات
stats = g.stats()
print(f"\n=== إحصائيات ===")
print(f"  مقبول: {stats.total_accepted}")
print(f"  محجوب: {stats.total_blocked}")
print(f"  محجوبون الآن: {stats.active_blacklisted_count}")
```

المخرج:
```
=== أحمد ===
  طلب 1: ✓ مقبول
  طلب 2: ✓ مقبول
  طلب 3: ✓ مقبول
  طلب 4: ✗ محجوب (rate_limit_exceeded)

=== سارة ===
  طلب 1: ✓ مقبول

=== إحصائيات ===
  مقبول: 4
  محجوب: 1
  محجوبون الآن: 1
```

---

## المعاملات وإعدادات الضبط

| المعامل | القيمة الافتراضية | الشرح |
|---|---|---|
| `max_requests` | `5` | الحد الأقصى للطلبات لكل هوية |
| `window_size` | `60` | مدة النافذة الزمنية (ثانية) |
| `blacklist_duration` | `30` | مدة الحجب بعد تجاوز الحد (ثانية) |
| `global_max_requests` | `20` | الحد الإجمالي لجميع المستخدمين |

---

## تشغيل الاختبارات

```bash
pip install -e ".[dev]"
pytest tests/ -v --cov=chainshield
```

---

## هيكل المشروع

```
chainshield/
├── chainshield/
│   ├── core/
│   │   ├── guardian.py        ← نقطة الدخول الرئيسية
│   │   ├── rate_limiter.py    ← Sliding Window
│   │   ├── blacklist.py       ← القائمة السوداء المؤقتة
│   │   └── global_limit.py    ← الحد العالمي
│   ├── storage/
│   │   ├── base.py            ← الواجهة المجردة
│   │   └── memory.py          ← التخزين في الذاكرة
│   ├── middleware/
│   │   ├── flask_middleware.py
│   │   └── fastapi_middleware.py
│   └── models.py              ← نماذج البيانات
├── tests/                     ← اختبارات شاملة
├── examples/                  ← أمثلة عملية
├── docs/                      ← توثيق تفصيلي
└── benchmarks/                ← قياس الأداء
```

---

## لماذا Python وليس Solidity؟

الـ Smart Contracts على Ethereum لديها مشاكل عملية حقيقية:

1. **تكلفة الـ Gas**: كل تغيير في الحالة يكلف مال حقيقي
2. **بطء التأكيد**: كل 12 ثانية بلوك جديد — الفلترة الفورية مستحيلة
3. **خطأ الـ revert**: في المشروع الأصلي، الـ `revert` كان يلغي حالة القائمة السوداء، فالحجب لم يكن يُحفظ أبداً
4. **الاعتماد على الشبكة**: تحتاج node كامل متصل

Python يحل كل هذه المشاكل مع الحفاظ على نفس المنطق الخوارزمي.

---

## الأمان

راجع [docs/Security-Analysis.md](docs/Security-Analysis.md) للتحليل الكامل.

النقاط الأساسية:
- ضع ChainShield خلف Reverse Proxy موثوق لمنع تزوير `X-Forwarded-For`
- للنشر على أكثر من process، استخدم Redis بدلاً من الذاكرة
- اضبط `global_max_requests` بناءً على حجم حركتك الطبيعية

---

## المساهمة

راجع [CONTRIBUTING.md](CONTRIBUTING.md). كل المساهمات مرحب بها.

---

## الرخصة

MIT — راجع [LICENSE](LICENSE).
