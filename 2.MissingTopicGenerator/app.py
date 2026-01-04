import streamlit as st
import uuid
import hashlib
import json
import pandas as pd
from supabase import create_client, Client
from google import genai
from google.genai import types

# =========================================================
# 0) إعداد صفحة التطبيق
# =========================================================
st.set_page_config(
    page_title="9/100: مُنشئ المحتوى المفقود",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# =========================================================
# 1) تحميل المفاتيح من Secrets (Streamlit Cloud)
# =========================================================
try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
    GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
except Exception:
    st.error("⚠️ فشل في تحميل المفاتيح السرّية (Secrets). تأكدي من ضبط SUPABASE_URL, SUPABASE_KEY, GOOGLE_API_KEY في Streamlit Cloud.")
    st.stop()

# تهيئة عملاء Supabase & Gemini
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
genai_client = genai.Client(api_key=GOOGLE_API_KEY)

# معرّف هذا التطبيق داخل قاعدة البيانات
APP_ID = "missing-topic-generator"

# =========================================================
# 2) CSS: RTL + Responsive + هوامش + فوتر
# =========================================================
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700&display=swap');

    html, body, [data-testid="stAppViewContainer"], .main {
        font-family: 'Cairo', sans-serif;
        direction: rtl;
        text-align: right;
    }

    /* حاوية عامة لضبط الهوامش من اليمين */
    .app-container {
        direction: rtl;
        text-align: right;
        padding-right: 0.5rem;
        padding-left: 0.5rem;
    }

    /* مربعات النص */
    .stTextArea textarea {
        direction: rtl !important;
        text-align: right !important;
        border-radius: 12px !important;
        font-size: 15px !important;
    }

    .stTextInput input {
        direction: rtl !important;
        text-align: right !important;
    }

    /* الأزرار */
    .stButton > button {
        width: 100%;
        border-radius: 999px;
        height: 3.2em;
        background-color: #2563eb !important;
        color: #ffffff !important;
        font-weight: 700;
        border: none;
        font-size: 16px;
        box-shadow: 0 4px 12px rgba(37, 99, 235, 0.35);
        transition: all 0.2s ease-in-out;
    }

    .stButton > button:hover {
        background-color: #1d4ed8 !important;
        transform: translateY(-1px);
        box-shadow: 0 6px 18px rgba(37, 99, 235, 0.45);
    }

    /* عنوان التطبيق في المنتصف RTL */
    .main-title {
        text-align: center !important;
        direction: rtl !important;
        font-weight: 800;
        margin-bottom: 0.25rem;
    }
    .main-subtitle {
        text-align: center !important;
        direction: rtl !important;
        color: #6b7280;
        margin-bottom: 1.5rem;
        font-size: 0.95rem;
    }

    /* صندوق النتائج/النصوص */
    .analysis-box {
        background: #f9fafb;
        border-radius: 14px;
        padding: 18px 18px;
        border: 1px solid #e5e7eb;
        margin-top: 1rem;
    }

    .analysis-box h3 {
        margin-top: 0;
        margin-bottom: 0.75rem;
        color: #111827;
        font-weight: 700;
        text-align: right;
    }

    .analysis-box p {
        margin: 0 0 0.35rem 0;
        line-height: 1.6;
        text-align: right;
    }

    /* تنسيق الـ DataFrame ليبدو مرتب */
    .stDataFrame {
        direction: rtl;
        text-align: right;
    }

    /* الفوتر: نص عربي يمين + إنجليزي يسار، لكن الكل في المنتصف */
    .footer-container {
        display: flex;
        justify-content: center;
        align-items: center;
        gap: 6px;
        margin-top: 40px;
        padding-top: 16px;
        border-top: 1px solid #e5e7eb;
        font-size: 0.8rem;
        color: #6b7280;
    }

    .footer-rtl {
        direction: rtl;
        text-align: right;
        white-space: nowrap;
    }

    .footer-ltr {
        direction: ltr;
        text-align: left;
        white-space: nowrap;
    }

    /* جعل كل شيء Responsive بشكل افتراضي (Streamlit يدعم ذلك) */
    @media (max-width: 768px) {
        .app-container {
            padding-right: 0.25rem;
            padding-left: 0.25rem;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# =========================================================
# 3) دوال التتبع (visitors + CTA) + الكاش
# =========================================================

def track_visit():
    """
    تسجيل زيارة هذا المستخدم لهذا التطبيق:
    - تستخدم دالة track_visit في Supabase.
    - تحدّث visitor_logs + analytics (views, unique_visitors, returning_visitors).
    """
    if "visitor_id" not in st.session_state:
        st.session_state.visitor_id = str(uuid.uuid4())

    visitor_id = st.session_state.visitor_id

    try:
        supabase.rpc(
            "track_visit",
            {"p_app_id": APP_ID, "p_visitor_id": visitor_id},
        ).execute()
    except Exception as e:
        # نطبع في الـ logs فقط ولا نُفشل التطبيق
        print(f"[track_visit] Error: {e}")


def track_cta_event():
    """
    تسجيل ضغطة زر (CTA) في جدول analytics باستخدام increment_cta.
    """
    try:
        supabase.rpc("increment_cta", {"p_app_id": APP_ID}).execute()
    except Exception as e:
        print(f"[track_cta_event] Error: {e}")


def get_content_hash(text1: str, text2: str) -> str:
    """
    توليد Hash ثابت بناءً على مدخلات المستخدم:
    - منشوراتك + منشورات المنافسين.
    - يساعدنا على تخزين النتيجة في كاش بحيث إذا أُعيد نفس الإدخال، نرجع نفس النتيجة فوراً.
    """
    combined = (text1.strip() + "\n---\n" + text2.strip()).encode("utf-8")
    return hashlib.sha256(combined).hexdigest()


def get_cached_analysis(content_hash: str):
    """
    قراءة نتيجة سابقة من جدول viral_scores_cache إن وجدت.
    """
    try:
        res = (
            supabase.table("viral_scores_cache")
            .select("analysis_text")
            .eq("app_id", APP_ID)
            .eq("content_hash", content_hash)
            .maybe_single()
            .execute()
        )
        data = res.data
        if data and "analysis_text" in data:
            return json.loads(data["analysis_text"])
    except Exception as e:
        print(f"[cache_read] Error: {e}")
    return None


def save_cached_analysis(content_hash: str, analysis_dict: dict):
    """
    تخزين نتيجة التحليل في جدول الكاش لزيادة السرعة وثبات النتيجة.
    """
    try:
        supabase.table("viral_scores_cache").upsert(
            {
                "app_id": APP_ID,
                "content_hash": content_hash,
                "analysis_text": json.dumps(analysis_dict, ensure_ascii=False),
            },
            on_conflict="app_id,content_hash",
        ).execute()
    except Exception as e:
        print(f"[cache_write] Error: {e}")


# تشغيل تتبع الزيارة عند تحميل الصفحة
track_visit()

# =========================================================
# 4) دالة استدعاء Gemini لتحليل الفجوات
# =========================================================

def analyze_content_gaps(my_posts: str, competitor_posts: str):
    """
    تحليل الفجوات بين محتوى المستخدم ومحتوى المنافسين
    باستخدام نموذج Gemini وإخراج منظم بصيغة JSON.
    يتم احترام الكاش عبر viral_scores_cache.
    """

    # أولاً: نتحقق من وجود نتيجة سابقة في الكاش
    content_hash = get_content_hash(my_posts, competitor_posts)
    cached = get_cached_analysis(content_hash)
    if cached is not None:
        return cached

    system_prompt = (
        "أنت خبير استراتيجي في المحتوى التسويقي متخصص في تحليل الفجوات (Content Gap Analysis). "
        "مهمتك هي مقارنة قائمة منشورات (العميل) مع قائمة منشورات (المنافسين)، "
        "ثم استخراج 5–7 مواضيع مهمة لم يتم تغطيتها بما يكفي، أو يتم تجاهلها، "
        "مع توضيح سبب كون كل موضوع فرصة قوية للنمو."
    )

    user_prompt = f"""
    🔹 قائمة منشورات العميل (عناوين أو ملخصات مختصرة):
    {my_posts}

    🔹 قائمة منشورات المنافسين (عناوين أو ملخصات مختصرة):
    {competitor_posts}

    المطلوب:
    1) تحليل نمط محتوى العميل مقابل المنافسين.
    2) اكتشاف الفجوات (مواضيع غير مغطاة عند العميل أو لم تُغطَّ بعمق).
    3) اقتراح 5–7 مواضيع (Missing Topics) يمكن أن تصبح محتوى قويّ الأداء.
    """

    response = genai_client.models.generate_content(
        model="gemini-2.5-flash",
        contents=user_prompt,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            response_mime_type="application/json",
            response_schema={
                "type": "OBJECT",
                "properties": {
                    "missing_topics": {
                        "type": "ARRAY",
                        "description": "قائمة بالمواضيع الاستراتيجية التي يُنصح بتغطيتها.",
                        "items": {
                            "type": "OBJECT",
                            "properties": {
                                "topic_title": {
                                    "type": "STRING",
                                    "description": "عنوان مختصر للموضوع المقترح.",
                                },
                                "gap_reason": {
                                    "type": "STRING",
                                    "description": "لماذا يُعد هذا الموضوع فجوة أو فرصة؟",
                                },
                                "format_suggestion": {
                                    "type": "STRING",
                                    "description": "أفضل صيغة محتوى لهذا الموضوع (ريل، كاروسيل، مقال، لايف...).",
                                },
                            },
                        },
                    },
                    "summary_analysis": {
                        "type": "STRING",
                        "description": "ملخص للنمط العام لمحتوى العميل مقابل المنافسين، مع توصيات عامة.",
                    },
                },
            },
        ),
    )

    try:
        result = json.loads(response.text)
    except json.JSONDecodeError:
        st.error("⚠️ لم يتمكن النموذج من إرجاع JSON منظم. يظهر النص الخام أدناه لمراجعتك:")
        st.code(response.text)
        return None

    # تخزين في الكاش لمرات الاستخدام القادمة
    save_cached_analysis(content_hash, result)
    return result


# =========================================================
# 5) واجهة المستخدم (UI)
# =========================================================

st.markdown('<div class="app-container">', unsafe_allow_html=True)

st.markdown('<h1 class="main-title">🧩 مُنشئ المحتوى المفقود</h1>', unsafe_allow_html=True)
st.markdown(
    '<div class="main-subtitle">حلّل منشوراتك ومنشورات منافسيك لاكتشاف المواضيع التي ينتظرها جمهورك ولم يتحدث عنها أحد بعمق.</div>',
    unsafe_allow_html=True,
)

with st.expander("ℹ️ ما الذي تفعله هذه الأداة؟"):
    st.markdown(
        """
        هذه الأداة تساعدك على **تحليل فجوات المحتوى (Content Gaps)** بين:
        
        - ما تنشره أنت حاليًا (بوستات، ريلز، فيديوهات، مقالات...)
        - وما ينشره منافسوك في نفس السوق أو النيتش
        
        ثم تقترح لك:
        
        - 🧠 مواضيع *مهمّة* لم تتناولها بما يكفي  
        - 🎯 أسباب كون كل موضوع فرصة قوية للنمو  
        - 🎥 واقتراح صيغة محتوى لكل موضوع (ريل، كاروسيل، لايف، سلسلة بوستات...)
        
        الهدف أن تخرجي من الأداة بقائمة جاهزة من **أفكار محتوى استراتيجية** بدلاً من النشر العشوائي.
        """
    )

st.markdown("---")

col1, col2 = st.columns(2)

with col1:
    my_posts_input = st.text_area(
        "منشوراتك العشرة الأخيرة (عناوين أو ملخصات سريعة):",
        height=260,
        placeholder=(
            "مثال:\n"
            "1. ليه المحتوى التعليمي ما بجيب مبيعات؟\n"
            "2. رحلتي من أول عميل حر إلى أول 1000$ شهريًا\n"
            "3. 3 أخطاء بتقتل تفاعل الريلز عندك\n"
            "4. كيف تستخدم لينكدإن لبناء براند مهني...\n"
        ),
        key="my_posts",
    )

with col2:
    competitor_posts_input = st.text_area(
        "أهم منشورات منافسيك (أو الحسابات الملهمة لك):",
        height=260,
        placeholder=(
            "مثال:\n"
            "1. خطة محتوى أسبوعية جاهزة لخبراء السوشال ميديا\n"
            "2. كيف تعمل لانش لمنتحك في 7 أيام\n"
            "3. أكثر أنواع الريلز انتشارًا في 2025\n"
            "4. تحليل حساب وصل من 0 إلى 100K متابع...\n"
        ),
        key="competitor_posts",
    )

analyze_button = st.button("🔍 تحليل الفجوات واقتراح المواضيع", use_container_width=True)

if analyze_button:
    if not my_posts_input.strip() or not competitor_posts_input.strip():
        st.warning("يرجى تعبئة القائمتين قبل بدء التحليل.")
    elif len(my_posts_input.strip()) < 40 or len(competitor_posts_input.strip()) < 40:
        st.warning("للحصول على تحليل أدق، يُفضّل أن تحتوي كل قائمة على عدة عناوين أو ملخصات (وليس جملة واحدة فقط).")
    else:
        # تسجيل CTA في analytics
        track_cta_event()

        with st.spinner("جاري تحليل المحتوى المُقارَن واكتشاف الفرص المخفية..."):
            result = analyze_content_gaps(my_posts_input, competitor_posts_input)

        if result:
            st.markdown("### 📌 ملخص النمط العام للمحتوى")
            st.markdown(
                f"""<div class="analysis-box"><p>{result.get('summary_analysis', 'لا يوجد ملخص متوفر.')}</p></div>""",
                unsafe_allow_html=True,
            )

            st.markdown("---")
            st.markdown("### 🎯 المواضيع المفقودة المقترحة (Missing Topics)")

            topics = result.get("missing_topics", [])
            if topics:
                # تحويل إلى DataFrame للعرض المنظم
                df = pd.DataFrame(topics)
                # تسمية الأعمدة بالعربية
                rename_map = {
                    "topic_title": "عنوان الموضوع المقترح",
                    "gap_reason": "سبب كونه فجوة/فرصة",
                    "format_suggestion": "اقتراح صيغة المحتوى",
                }
                df = df.rename(columns=rename_map)
                st.dataframe(df, use_container_width=True)
            else:
                st.info("لم يتمكن النموذج من تحديد مواضيع مفقودة بوضوح. جرّبي إدخال قوائم أكثر تنوّعاً أو تفصيلاً.")

st.markdown(
    """
    <div class="footer-container">
      <span class="footer-rtl">جميع الحقوق محفوظة @ 2026 |</span>
      <span class="footer-ltr">AI Product Builder - Layan Khalil</span>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown("</div>", unsafe_allow_html=True)
