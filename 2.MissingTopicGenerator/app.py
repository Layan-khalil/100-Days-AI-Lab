import streamlit as st
from google import genai
from google.genai import types
from supabase import create_client, Client
import uuid
import hashlib
import json
import pandas as pd

# =================================================================
# 1. إعدادات الصفحة + CSS (RTL / Responsive)
# =================================================================

st.set_page_config(
    page_title="🔍 مُنشئ المحتوى المفقود",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# CSS مدمج
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700&display=swap');

    html, body, [data-testid="stAppViewContainer"], .main {
        direction: rtl !important;
        text-align: right !important;
        font-family: 'Cairo', sans-serif;
        background-color: #0f172a;
    }

    [data-testid="stAppViewContainer"] > .main {
        display: flex;
        justify-content: center;
    }

    .block-container {
        max-width: 900px;
        padding-top: 2rem;
        padding-bottom: 3rem;
    }

    h1, h2, h3 {
        text-align: center;
        font-weight: 700;
    }

    .stTextArea textarea {
        direction: rtl !important;
        text-align: right !important;
        border-radius: 12px;
        font-size: 15px;
        line-height: 1.6;
    }

    .stButton button {
        width: 100%;
        border-radius: 999px;
        height: 3.3em;
        font-weight: 700;
        font-size: 16px;
        border: none;
        background-color: #e63946 !important;
        color: #ffffff !important;
    }

    .stButton button:hover {
        filter: brightness(1.05);
    }

    .gap-card {
        background: #020617;
        border-radius: 16px;
        padding: 22px 20px;
        border: 1px solid #1e293b;
        box-shadow: 0 10px 30px rgba(15,23,42,0.65);
    }

    .gap-card h3 {
        text-align: right;
        margin-bottom: 1rem;
    }

    .footer-container {
        margin-top: 40px;
        padding-top: 16px;
        border-top: 1px solid #1e293b;
        text-align: center !important;
        font-size: 13px;
        color: #94a3b8;
        direction: rtl;
    }

    .footer-container span.ltr {
        direction: ltr;
        unicode-bidi: bidi-override;
        margin-right: 4px;
    }

    /* جدول النتائج */
    .dataframe td, .dataframe th {
        text-align: right !important;
    }

    @media (max-width: 768px) {
        .block-container {
            padding-left: 0.8rem;
            padding-right: 0.8rem;
        }
        h1 {
            font-size: 1.4rem;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# =================================================================
# 2. إعداد الاتصال بـ Supabase + Gemini
# =================================================================

APP_ID = "missing-topic-generator-v1"

try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
except KeyError:
    st.error("⚠️ تأكد من وجود SUPABASE_URL و SUPABASE_KEY و GEMINI_API_KEY في ملف secrets.toml.")
    st.stop()

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

try:
    genai_client = genai.Client(api_key=GEMINI_API_KEY)
except Exception as e:
    st.error(f"خطأ في تهيئة نموذج Gemini: {e}")
    st.stop()

# =================================================================
# 3. دوال التتبع (visits + CTA) + الكاش المشترك
# =================================================================

def make_content_hash(*parts: str) -> str:
    """إنشاء بصمة موحّدة للمحتوى (لكل تطبيق)."""
    normalized = "\n\n".join(p.strip() for p in parts if p and p.strip())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def track_visit():
    """تسجيل زيارة فريدة + تحديث analytics عبر دالة track_visit في Supabase."""
    if "session_tracked" in st.session_state:
        return

    st.session_state.session_tracked = True
    visitor_id = str(uuid.uuid4())

    try:
        supabase.rpc(
            "track_visit",
            {"p_app_id": APP_ID, "p_visitor_id": visitor_id},
        ).execute()
    except Exception as e:
        print("Track visit error:", e)


def track_cta():
    """تسجيل ضغطة زر التحليل (CTA) في جدول analytics."""
    try:
        supabase.rpc("increment_cta", {"p_app_id": APP_ID}).execute()
    except Exception as e:
        print("CTA error:", e)


def get_cached_result(app_id: str, content_hash: str):
    """إرجاع نتيجة الكاش (إن وجدت) من جدول viral_scores_cache."""
    try:
        res = (
            supabase.table("viral_scores_cache")
            .select("analysis_text")
            .eq("app_id", app_id)
            .eq("content_hash", content_hash)
            .limit(1)
            .execute()
        )
        if res.data:
            return res.data[0]["analysis_text"]
    except Exception as e:
        print("Cache read error:", e)
    return None


def save_cached_result(app_id: str, content_hash: str, analysis_text: str):
    """حفظ النتيجة في جدول الكاش (كـ نص)."""
    try:
        supabase.table("viral_scores_cache").upsert(
            {
                "app_id": app_id,
                "content_hash": content_hash,
                "analysis_text": analysis_text,
            },
            on_conflict="app_id,content_hash",
        ).execute()
    except Exception as e:
        print("Cache write error:", e)


track_visit()  # يُنفَّذ مرة واحدة لكل جلسة

# =================================================================
# 4. دالة استدعاء Gemini لتحليل الفجوات
# =================================================================

def analyze_content_gaps(my_posts: str, competitor_posts: str):
    """
    تحليل قائمة منشوراتك مقابل منشورات المنافسين
    واستخراج مواضيع مفقودة محتملة (Gap Analysis).
    """
    system_prompt = (
        "أنت خبير استراتيجي في المحتوى التسويقي متخصص في تحليل الفجوات (Content Gap Analysis). "
        "قارن بين منشورات العميل ومنشورات المنافسين، واستخرج 5–7 مواضيع استراتيجية مفقودة "
        "من الممكن أن تجذب الجمهور بقوة. أعد الاستجابة بتنسيق JSON فقط."
    )

    user_prompt = (
        "قارن بين قائمتين من المنشورات (للعميل والمنافسين)، "
        "واستخرج مواضيع مفقودة، مع سبب يوضح الفجوة، واقتراح شكل المحتوى المناسب.\n\n"
        f"🧑‍💻 منشورات العميل:\n{my_posts}\n\n"
        f"🏁 منشورات المنافسين:\n{competitor_posts}\n"
    )

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
                        "items": {
                            "type": "OBJECT",
                            "properties": {
                                "topic_title": {"type": "STRING"},
                                "gap_reason": {"type": "STRING"},
                                "format_suggestion": {"type": "STRING"},
                            },
                        },
                    },
                    "summary_analysis": {"type": "STRING"},
                },
            },
            temperature=0.2,
            top_p=0.8,
            top_k=32,
            max_output_tokens=1200,
        ),
    )

    try:
        return json.loads(response.text)
    except json.JSONDecodeError:
        st.error("النموذج لم يرجع JSON صالح. الرد الخام مذكور في سجلات الـ console.")
        print("Raw response:", response.text)
        return None

# =================================================================
# 5. واجهة المستخدم
# =================================================================

st.title("🔍 مُنشئ المحتوى المفقود (Missing Topic Generator)")
st.caption("حلّل منشوراتك ومنشورات منافسيك لاكتشاف المواضيع التي لا يغطيها أحد رغم أن جمهورك يحتاجها.")

with st.expander("💡 كيف يعمل هذا المحلل؟", expanded=False):
    st.markdown(
        """
        هذه الأداة تساعدك على اكتشاف **فرص محتوى جديدة** من خلال مقارنة:
        
        - منشوراتك الحالية (عناوين، أفكار، أو وصف مختصر)
        - منشورات منافسيك المباشرين في نفس المجال
        
        ثم يقوم النموذج بتحليل الفجوات ليقترح عليك:
        
        - عناوين مواضيع لم يتم التركيز عليها بما يكفي  
        - سبب كون هذا الموضوع فرصة قوية (فجوة في السوق/طلب ضمني من الجمهور)  
        - الشكل الأنسب لتقديمه: فيديو قصير، كاروسيل، لايف، سلسلة بوستات…  
        """
    )

st.markdown("---")

col1, col2 = st.columns(2)

with col1:
    my_posts_input = st.text_area(
        "✍️ ألصق هنا عناوين أو ملخصات **آخر 10 منشورات لك**:",
        height=260,
        placeholder="مثال:\n1. 5 أخطاء شائعة في التسويق على إنستغرام\n"
                    "2. كيف تنمو على TikTok في 30 يوماً\n"
                    "3. تجربتي مع أول إطلاق رقمي لمنتج تعليمي...",
    )

with col2:
    competitor_posts_input = st.text_area(
        "📌 ألصق هنا عناوين أو ملخصات **آخر 10 منشورات لمنافسيك**:",
        height=260,
        placeholder="مثال:\n1. كيف تختار فكرة كورس أونلاين مربحة\n"
                    "2. خطة محتوى شهرية جاهزة للحسابات التعليمية\n"
                    "3. أخطاء شائعة في تصميم الصفحات البيعية...",
    )

analyze_button = st.button("🚀 تحليل الفجوات واقتراح المواضيع")

# =================================================================
# 6. منطق الزر + الكاش
# =================================================================

if analyze_button:
    if not my_posts_input.strip() or not competitor_posts_input.strip():
        st.warning("الرجاء إدخال منشوراتك ومنشورات المنافسين حتى يتمكن النظام من المقارنة.")
    elif len(my_posts_input.strip()) < 50 or len(competitor_posts_input.strip()) < 50:
        st.warning("يفضّل إدخال وصف أكثر لكل قائمة (على الأقل 50 حرفاً) للحصول على تحليل أدق.")
    else:
        # تسجيل CTA
        track_cta()

        # بصمة المحتوى لهذا التطبيق
        content_hash = make_content_hash(my_posts_input, competitor_posts_input)

        # 1) محاولة قراءة من الكاش
        cached = get_cached_result(APP_ID, content_hash)
        if cached:
            try:
                analysis_result = json.loads(cached)
                from_cache = True
            except json.JSONDecodeError:
                analysis_result = None
                from_cache = False
        else:
            from_cache = False
            with st.spinner("جاري تحليل المحتوى المُقارَن واكتشاف الفجوات الاستراتيجية..."):
                analysis_result = analyze_content_gaps(my_posts_input, competitor_posts_input)
                if analysis_result:
                    # تخزين في الكاش (كـ نص JSON)
                    save_cached_result(APP_ID, content_hash, json.dumps(analysis_result, ensure_ascii=False))

        if analysis_result:
            st.markdown(
                f"""<div class="gap-card">
                <h3>🎯 الفرص المفقودة: مواضيع يجب التركيز عليها قريباً</h3>
                <p style="margin-bottom:0.5rem;">
                {analysis_result.get("summary_analysis", "تحليل عام لنمط منشوراتك ومنشورات منافسيك.")}
                </p>
                </div>""",
                unsafe_allow_html=True,
            )

            st.markdown("### 📚 قائمة المواضيع المقترحة:")

            missing_topics = analysis_result.get("missing_topics", [])
            if missing_topics:
                df = pd.DataFrame(missing_topics)
                # إعادة تسمية الأعمدة بالعربية
                df.columns = ["الموضوع المقترح", "سبب كونها فجوة / فرصة", "اقتراح شكل المحتوى"]
                st.dataframe(df, use_container_width=True)
            else:
                st.info("النموذج لم يجد فجوات واضحة بين القائمتين. ربما المحتوى متشابه جداً.")

            if from_cache:
                st.caption("✅ تم جلب هذه النتيجة من الكاش لتسريع التحليل وتقليل استهلاك الـ API.")
        else:
            st.error("تعذر الحصول على تحليل صالح من النموذج. يرجى المحاولة لاحقاً.")

# =================================================================
# 7. الفوتر
# =================================================================

st.markdown(
    """
    <div class="footer-container">
        <span>جميع الحقوق محفوظة © 2026 |</span>
        <span class="ltr">AI Product Builder - Layan Khalil</span>
    </div>
    """,
    unsafe_allow_html=True,
)s
