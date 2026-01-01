import streamlit as st
import uuid
import hashlib
from supabase import create_client, Client
from google import genai
from google.genai import types

# =========================================================
# 1) تحميل Secrets
# =========================================================
try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
    GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
except Exception:
    st.error("⚠️ فشل في تحميل مفاتيح الاتصال. تأكد من إضافة Secrets في Streamlit Cloud.")
    st.stop()

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
genai_client = genai.Client(api_key=GOOGLE_API_KEY)

APP_ID = "viral-potential-scorer-v1"

# =========================================================
# 2) وظائف التتبع (RLS عبر الدوال فقط)
# =========================================================
def track_visit():
    """تسجيل زيارة عبر دالة track_visit"""
    if "visitor_id" not in st.session_state:
        st.session_state.visitor_id = uuid.uuid4()

    try:
        supabase.rpc(
            "track_visit",
            {
                "p_app_id": APP_ID,
                "p_visitor_id": str(st.session_state.visitor_id)
            }
        ).execute()
    except Exception as e:
        print(f"[TRACK VISIT ERROR] {e}")

def track_cta():
    """تسجيل ضغطة CTA"""
    try:
        supabase.rpc("increment_cta", {"p_app_id": APP_ID}).execute()
    except Exception as e:
        print(f"[CTA ERROR] {e}")

track_visit()

# =========================================================
# 3) كاش النتائج — ثابت لكل نص
# =========================================================
def hash_content(text: str):
    return hashlib.sha256(text.strip().encode()).hexdigest()

def get_cached_result(content_hash):
    try:
            res = (
                supabase.table("viral_scores_cache")
                .select("analysis_text")
                .eq("app_id", APP_ID)
                .eq("content_hash", content_hash)
                .limit(1)
                .execute()
            )

            if res.data:
                return res.data[0]["analysis_text"]
    except Exception as e:
        print(f"[CACHE FETCH ERROR] {e}")

    return None

def save_result_to_cache(content_hash, analysis_text):
    try:
        supabase.table("viral_scores_cache").insert({
            "app_id": APP_ID,
            "content_hash": content_hash,
            "analysis_text": analysis_text
        }).execute()
    except Exception as e:
        print(f"[CACHE SAVE ERROR] {e}")

# =========================================================
# 4) إعدادات الصفحة + RTL + محاذاة كاملة يمين
# =========================================================
st.set_page_config(page_title="🎯 مُحلّل احتمالية الانتشار", layout="centered")

st.markdown("""
<style>

html, body, [data-testid="stAppViewContainer"], .main {
    direction: rtl !important;
    text-align: right !important;
    font-family: "Cairo", sans-serif;
}

/* كل النصوص والمخرجات بمحاذاة يمين */
p, div, span, textarea, .stMarkdown, .stTextArea textarea {
    direction: rtl !important;
    text-align: right !important;
}

/* المخرجات داخل الصندوق — محاذاة يمين */
.output-box {
    background: #ffffff;
    border: 2px solid #e63946;
    border-radius: 14px;
    padding: 20px;
    margin-top: 15px;
    line-height: 1.9;
    direction: rtl !important;
    text-align: right !important;
}

/* صندوق النتيجة */
.score-box {
    background: #f8f9fa;
    border: 3px solid #e63946;
    border-radius: 18px;
    padding: 25px;
    margin-top: 20px;
    text-align: center;
}

/* زر CTA */
.stButton button {
    width: 100%;
    height: 3.5em;
    border-radius: 25px;
    font-weight: bold;
    background:#e63946;
    color:white;
    border:none;
}

/* الفوتر LTR */
.footer-ltr {
    direction:ltr !important;
    text-align:center !important;
    margin-top:45px;
    color:#777;
}
            

</style>
""", unsafe_allow_html=True)

# =========================================================
# 5) واجهة التطبيق
# =========================================================
st.title("🎯 مُحلّل احتمالية الانتشار الفيروسي")

with st.expander("💡 شرح العوامل النفسية (STEPPS)"):
    st.markdown("""
**✔️ العملة الاجتماعية** — هل يجعل الشخص يبدو أذكى / أقوى عند مشاركته؟  
**✔️ المحفزات** — هل يتكرر ارتباطه بأحداث يومية أو كلمات شائعة؟  
**✔️ المشاعر** — هل يثير دهشة / حماس / فضول قوي؟  
**✔️ الظهور العام** — هل من السهل تقليده أو رؤية تأثيره اجتماعياً؟  
**✔️ القيمة العملية** — هل يقدم فائدة حقيقية قابلة للتطبيق؟  
**✔️ القصة** — هل الفكرة مغلفة بسرد قصصي يسهل تذكره؟  
""")

post_text = st.text_area("ألصق النص هنا:", height=170)

# =========================================================
# 6) زر التحليل
# =========================================================
if st.button("تحليل الآن 🚀"):

    if not post_text.strip():
        st.warning("يرجى إدخال نص للتحليل.")
        st.stop()

    track_cta()

    content_hash = hash_content(post_text)

    cached = get_cached_result(content_hash)

    # ========= استخدام النتيجة من الكاش =========
    if cached:
        st.success("✔ تم استخدام نتيجة محفوظة سابقاً (ثبات كامل)")
        st.markdown(f'<div class="output-box">{cached}</div>', unsafe_allow_html=True)
        st.stop()

    # ========= توليد تحليل جديد =========
    with st.spinner("جاري إجراء التحليل العلمي..."):
        try:
            config = types.GenerateContentConfig(
                temperature=0.0,
                top_p=0.1,
                top_k=1,
                max_output_tokens=900
            )

            prompt = f"""
أنت خبير علم نفس المحتوى الفيروسي.
حلّل النص التالي وفق عوامل STEPPS الستة.

❗ هام:
لا تحسب نتيجة إجمالية نهائية.
اكتب تقييم كل عامل فقط، مع شرح قصير ثابت.

النص:
{post_text}
"""

            response = genai_client.models.generate_content(
                model="gemini-2.0-flash-exp",
                contents=prompt,
                config=config
            )

            analysis_text = response.text.strip()

            save_result_to_cache(content_hash, analysis_text)

            st.markdown(f'<div class="output-box">{analysis_text}</div>', unsafe_allow_html=True)

        except Exception:
            st.error("حدث خطأ أثناء التحليل. يرجى المحاولة لاحقاً.")

# =========================================================
# 7) فوتر
# =========================================================
st.markdown('<div class="footer-ltr">جميع الحقوق محفوظة © 2026 | AI Product Builder - Layan Khalil</div>', unsafe_allow_html=True)

