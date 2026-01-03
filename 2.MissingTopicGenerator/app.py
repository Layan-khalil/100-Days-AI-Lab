import streamlit as st
import uuid
import hashlib
import json
import pandas as pd
from supabase import create_client, Client
from google import genai
from google.genai import types

# =================================================================
# 1. إعدادات الصفحة + CSS (RTL / Responsive)
# =================================================================

st.set_page_config(
    page_title="🔍 مُنشئ المحتوى المفقود",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700&display=swap');

    html, body, [data-testid="stAppViewContainer"], .main {
        direction: rtl;
        text-align: right;
        font-family: 'Cairo', sans-serif;
        background-color: #020617;
        color: #e5e7eb;
    }

    .app-container {
        max-width: 900px;
        margin: 0 auto;
        padding: 1.5rem 1rem 4rem 1rem;
    }

    h1, h2, h3 {
        text-align: center;
    }

    .stTextArea textarea {
        direction: rtl !important;
        text-align: right !important;
        border-radius: 12px !important;
        font-size: 0.95rem;
    }

    .stButton>button {
        width: 100%;
        border-radius: 999px;
        padding: 0.9rem 1.5rem;
        background-color: #e63946 !important;
        color: #ffffff !important;
        font-weight: 700;
        border: none;
        font-size: 1rem;
        box-shadow: 0 4px 12px rgba(230, 57, 70, 0.35);
    }

    .stButton>button:hover {
        background-color: #c92c3a !important;
        box-shadow: 0 6px 16px rgba(230, 57, 70, 0.45);
        transform: translateY(-1px);
    }

    .result-block {
        background: #020617;
        border-radius: 16px;
        padding: 1.2rem 1.4rem;
        border: 1px solid #374151;
        margin-top: 1.2rem;
    }

    .result-block p,
    .result-block li,
    .result-block span,
    .result-block div {
        direction: rtl;
        text-align: right;
    }

    .result-block ul,
    .result-block ol {
        padding-inline-start: 1.4rem;
        list-style-position: inside;
    }

    [data-testid="stDataFrame"] {
        direction: rtl;
        text-align: right;
    }

    .footer-container {
        direction: ltr;
        text-align: center;
        color: #9ca3af;
        margin-top: 3rem;
        padding-top: 1rem;
        border-top: 1px solid #374151;
        font-size: 0.8rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# =================================================================
# 2. الاتصال بـ Supabase + Gemini
# =================================================================

APP_ID = "missing-topic-generator"

# Supabase
try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
except KeyError:
    st.error("⚠️ لم يتم العثور على SUPABASE_URL أو SUPABASE_KEY في secrets.")
    st.stop()

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Gemini API Key (يدعم اسمين: GEMINI_API_KEY أو GOOGLE_API_KEY)
try:
    try:
        API_KEY = st.secrets["GEMINI_API_KEY"]
    except KeyError:
        API_KEY = st.secrets["GOOGLE_API_KEY"]
except KeyError:
    st.error("⚠️ لم يتم العثور على مفتاح Gemini (GEMINI_API_KEY أو GOOGLE_API_KEY) في secrets.")
    st.stop()

genai_client = genai.Client(api_key=API_KEY)

# =================================================================
# 3. دوال التتبع (Views / Unique / Returning / CTA)
# =================================================================

def track_visit():
    """
    يرسل visitor_id + app_id إلى دالة track_visit في Supabase
    لحساب:
    - views
    - unique_visitors
    - returning_visitors
    """
    if "visitor_id" not in st.session_state:
        st.session_state["visitor_id"] = str(uuid.uuid4())

    visitor_id = st.session_state["visitor_id"]

    try:
        supabase.rpc(
            "track_visit",
            {"p_app_id": APP_ID, "p_visitor_id": visitor_id},
        ).execute()
    except Exception as e:
        # نطبع الخطأ في اللوغ فقط كي لا نُفسد تجربة المستخدم
        print("track_visit error:", e)


def track_cta():
    """زيادة عدّاد الضغطات على زر التحليل (cta_count)."""
    try:
        supabase.rpc("increment_cta", {"p_app_id": APP_ID}).execute()
    except Exception as e:
        print("increment_cta error:", e)


# استدعاء التتبع عند تحميل الصفحة
track_visit()

# =================================================================
# 4. دالة استدعاء Gemini + الكاش في viral_scores_cache
# =================================================================

def call_gemini_gap_analysis(my_posts: str, competitor_posts: str) -> dict | None:
    """
    يستدعي نموذج Gemini لتحليل فجوات المحتوى ويعيد JSON منظم.
    """
    system_prompt = (
        "أنت خبير استراتيجي في المحتوى التسويقي متخصص في تحليل الفجوات (Content Gap Analysis). "
        "قارن بين قائمة منشورات العميل وقائمة منشورات المنافسين، واستخرج 5–7 مواضيع مفقودة "
        "أو غير مغطّاة بالشكل الكافي، لكنّها مهمة وذات طلب محتمل من الجمهور. "
        "التزم تمامًا بمخطّط JSON المطلوب دون أي نص خارج JSON."
    )

    user_prompt = (
        "هذه هي بيانات التحليل:\n\n"
        f"منشورات العميل (مختصرة أو عناوين فقط):\n{my_posts}\n\n"
        f"منشورات المنافسين (مختصرة أو عناوين فقط):\n{competitor_posts}\n\n"
        "أعد النتيجة في JSON مطابق للمخطط."
    )

    config = types.GenerateContentConfig(
        system_instruction=system_prompt,
        response_mime_type="application/json",
        response_schema={
            "type": "OBJECT",
            "properties": {
                "missing_topics": {
                    "type": "ARRAY",
                    "description": "قائمة بالمواضيع الاستراتيجية المفقودة أو غير المغطاة جيدًا.",
                    "items": {
                        "type": "OBJECT",
                        "properties": {
                            "topic_title": {
                                "type": "STRING",
                                "description": "عنوان واضح للموضوع المقترح."
                            },
                            "gap_reason": {
                                "type": "STRING",
                                "description": "لماذا يُعد هذا الموضوع فجوة؟ ما الذي يجعله فرصة قوية؟"
                            },
                            "format_suggestion": {
                                "type": "STRING",
                                "description": "اقتراح شكل المحتوى: فيديو قصير، سلسلة بوستات، بث مباشر، كتيّب، إلخ."
                            },
                        },
                    },
                },
                "summary_analysis": {
                    "type": "STRING",
                    "description": "تلخيص لنمط محتوى العميل مقابل المنافسين وما يميّز الفرص المقترحة."
                },
            },
        },
        temperature=0.2,
        top_p=0.8,
        top_k=32,
        max_output_tokens=1200,
    )

    response = genai_client.models.generate_content(
        model="gemini-2.5-flash",
        contents=user_prompt,
        config=config,
    )

    raw = response.text.strip()

    # في حال رجّع ```json ... ``` نحاول تنظيفها
    if raw.startswith("```"):
        raw = raw.strip("`")
        # أحياناً يكون أول سطر json أو JSON
        lines = raw.splitlines()
        if lines and lines[0].lower().startswith("json"):
            raw = "\n".join(lines[1:]).strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        print("JSON decode error. Raw response:", raw[:300])
        return None


def get_or_create_cached_analysis(my_posts: str, competitor_posts: str) -> dict | None:
    """
    1) يحسب hash للنصين معاً.
    2) يحاول جلب النتيجة من جدول viral_scores_cache.
    3) إذا لم يجدها، يستدعي Gemini ويحفظ النتيجة في الكاش.
    """
    combined = (my_posts or "").strip() + "\n---\n" + (competitor_posts or "").strip()
    content_hash = hashlib.sha256(combined.encode("utf-8")).hexdigest()

    # محاولة قراءة من الكاش
    try:
        res = (
            supabase.table("viral_scores_cache")
            .select("analysis_text")
            .eq("app_id", APP_ID)
            .eq("content_hash", content_hash)
            .execute()
        )
        if res.data:
            cached_text = res.data[0]["analysis_text"]
            return json.loads(cached_text)
    except Exception as e:
        print("cache read error:", e)

    # لا يوجد كاش → استدعاء Gemini
    analysis = call_gemini_gap_analysis(my_posts, competitor_posts)
    if analysis is None:
        return None

    # حفظ في الكاش
    try:
        supabase.table("viral_scores_cache").insert(
            {
                "app_id": APP_ID,
                "content_hash": content_hash,
                "analysis_text": json.dumps(analysis, ensure_ascii=False),
            }
        ).execute()
    except Exception as e:
        print("cache write error:", e)

    return analysis


# =================================================================
# 5. واجهة المستخدم
# =================================================================

st.markdown('<div class="app-container">', unsafe_allow_html=True)

st.title("🔍 مُنشئ المحتوى المفقود (Content Gap Finder)")
st.caption(
    "أداة تساعدك على اكتشاف المواضيع التي لا تغطيها أنت ولا منافسوك بالشكل الكافي، "
    "لكن جمهورك ينتظرها."
)

with st.expander("💡 كيف يعمل هذا المحلل؟", expanded=False):
    st.markdown(
        """
        يقوم هذا المحلل بمقارنة آخر ما تنشره أنت مع ما ينشره منافسوك، ثم يبحث عن:

        - مواضيع مهمّة لا تظهر في محتواك إطلاقًا.  
        - مواضيع يكررها المنافسون بينما تذكرها أنت بشكل ضعيف أو سطحي.  
        - أسئلة أو زوايا ناقصة يمكن أن تتحوّل إلى **سلاسل محتوى قوية** (بوستات، فيديوهات، نشرات بريدية…).  

        المخرجات النهائية تعطيك:

        1. عنوان واضح لكل فكرة قابلة للتنفيذ.  
        2. سبب اعتبارها «فجوة» وفرصة للمنافسة.  
        3. اقتراح لشكل المحتوى الأنسب (Reel، Thread، بث مباشر، سلسلة مقالات…).  
        """
    )

st.markdown("### ✍️ أدخل البيانات")

col1, col2 = st.columns(2)

with col1:
    my_posts_input = st.text_area(
        "منشوراتك العشرة الأخيرة (عناوين أو ملخصات مختصرة):",
        height=260,
        placeholder=(
            "مثال:\n"
            "1. 5 أخطاء شائعة في التسويق بالمحتوى\n"
            "2. كيف تنمو على TikTok في 30 يوماً\n"
            "3. تجربتي مع أول حملة إعلانات مدفوعة\n"
            "4. مراجعة أدوات الذكاء الاصطناعي لصناع المحتوى..."
        ),
    )

with col2:
    competitor_posts_input = st.text_area(
        "منشورات المنافسين (من 5 إلى 15 منشوراً / عنواناً):",
        height=260,
        placeholder=(
            "مثال:\n"
            "1. خطة محتوى جاهزة لـ Reels في 2025\n"
            "2. كيف تختار نيتش مربح في إنستغرام\n"
            "3. دورة مجانية في تحرير الفيديو\n"
            "4. نتائج حملة إعلانية لمتجر إلكتروني..."
        ),
    )

analyze_button = st.button("🚀 تحليل الفجوات واقتراح المواضيع")

# =================================================================
# 6. تنفيذ التحليل وعرض النتائج
# =================================================================

if analyze_button:
    if not my_posts_input or not competitor_posts_input:
        st.warning("يرجى إدخال بيانات منشوراتك ومنشورات المنافسين أولاً.")
    elif len(my_posts_input.strip()) < 50 or len(competitor_posts_input.strip()) < 50:
        st.warning("للحصول على تحليل مفيد، يُفضَّل أن تحتوي كل قائمة على ما لا يقل عن 50 حرفاً.")
    else:
        # تسجيل ضغطة الزر في التحليلات
        track_cta()

        with st.spinner("جاري تحليل المحتوى المُقارَن واكتشاف الفجوات الاستراتيجية..."):
            analysis_result = get_or_create_cached_analysis(
                my_posts_input, competitor_posts_input
            )

        if analysis_result is None:
            st.error("لم يتمكّن النموذج من إنتاج استجابة صالحة هذه المرة. حاول تعديل القوائم أو إعادة المحاولة.")
        else:
            st.markdown("## 🎯 الفرص المفقودة في محتواك")

            summary = analysis_result.get("summary_analysis", "")
            missing_topics = analysis_result.get("missing_topics", [])

            if summary:
                st.markdown("### ملخص عام")
                st.markdown(
                    f'<div class="result-block"><p>{summary}</p></div>',
                    unsafe_allow_html=True,
                )

            st.markdown("### المواضيع المقترحة للتنفيذ:")

            if missing_topics:
                df = pd.DataFrame(missing_topics)
                df.columns = ["الموضوع المقترح", "سبب اعتباره فجوة", "اقتراح شكل المحتوى"]
                st.dataframe(df, use_container_width=True)
            else:
                st.info("لم يحدّد النموذج فجوات واضحة. ربما القوائم متشابهة جداً أو قصيرة.")

st.markdown(
    '<div class="footer-container">جميع الحقوق محفوظة © 2026 | AI Product Builder - Layan Khalil</div>',
    unsafe_allow_html=True,
)

st.markdown('</div>', unsafe_allow_html=True)
