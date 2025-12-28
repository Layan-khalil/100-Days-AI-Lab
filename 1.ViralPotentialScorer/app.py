import streamlit as st
import pandas as pd
import os
import uuid
import time
from supabase import create_client, Client
from google import genai

# ==========================================
# 1. إعدادات الأمان والاتصال (Secrets Management)
# ==========================================

# الطريقة الرسمية في Streamlit لقراءة المفاتيح السرية سواء محلياً أو في Vercel
try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
    GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
except Exception:
    st.error("⚠️ خطأ: المفاتيح السرية غير موجودة! يرجى إضافتها في Settings > Environment Variables")
    st.stop()

# إنشاء عملاء الاتصال
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
client = genai.Client(api_key=GOOGLE_API_KEY)

# --- معرف التطبيق الفريد للمنظمة ---
APP_ID = "viral-potential-scorer-v1"

# ==========================================
# 2. نظام التتبع (Analytics Engine)
# ==========================================

def track_metrics():
    if 'visitor_id' not in st.session_state:
        st.session_state.visitor_id = str(uuid.uuid4())
        st.session_state.start_time = time.time()
        try:
            # التحقق هل الزائر عائد أم جديد
            res = supabase.table("visitor_logs").select("*").eq("visitor_id", st.session_state.visitor_id).eq("app_id", APP_ID).execute()
            is_returning = len(res.data) > 0
            
            if not is_returning:
                supabase.table("visitor_logs").insert({"visitor_id": st.session_state.visitor_id, "app_id": APP_ID}).execute()
                supabase.rpc('increment_analytics', {'row_id': APP_ID, 'v_inc': 1, 'u_inc': 1, 'r_inc': 0}).execute()
            else:
                supabase.rpc('increment_analytics', {'row_id': APP_ID, 'v_inc': 1, 'u_inc': 0, 'r_inc': 1}).execute()
        except:
            pass

def track_cta():
    try:
        supabase.rpc('increment_cta', {'row_id': APP_ID}).execute()
    except:
        pass

# تشغيل التتبع فوراً
track_metrics()

# ==========================================
# 3. إعدادات واجهة التطبيق (UI Settings)
# ==========================================

st.set_page_config(
    page_title="مُحلّل إمكانية العدوى الفيروسية",
    layout="centered", # التنسيق المركزي أفضل لجودة العرض على الموبايل
    initial_sidebar_state="collapsed",
)

# تضمين CSS مباشرة لضمان عدم حدوث خطأ إذا لم يُرفع الملف الخارجي
st.markdown("""
    <style>
    .main { text-align: right; direction: rtl; }
    .stTextArea textarea { text-align: right; direction: rtl; border-radius: 15px; }
    .stButton button { width: 100%; border-radius: 25px; height: 3em; font-weight: bold; }
    .custom-footer { text-align: center; padding: 20px; color: #666; font-size: 0.9em; border-top: 1px solid #eee; margin-top: 50px; }
    .score-box { background: #f0f2f6; padding: 20px; border-radius: 15px; text-align: center; border: 2px solid #4CAF50; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 4. المنطق البرمجي والواجهة (App Logic)
# ==========================================

st.title("🎯 مُحلّل احتمالية الانتشار (Viral Scorer)")
st.write("اكتشف مدى قابلية منشورك للانتشار الفيروسي باستخدام علم نفس المحتوى والذكاء الاصطناعي.")

post_draft = st.text_area(
    "ألصق مسودة منشورك هنا:",
    height=200,
    placeholder="اكتب التغريدة أو نص الفيديو هنا..."
)

analyze_button = st.button("تحليل العوامل النفسية 🚀", type="primary")

if analyze_button and post_draft:
    if len(post_draft.strip()) < 30: # تقليل الحد الأدنى قليلاً للتغريدات القصيرة
        st.warning("يرجى إدخال نص أطول قليلاً للحصول على تحليل دقيق.")
        st.stop()

    prompt_template = f"""
    أنت خبير في سيكولوجية الجماهير وعلم نفس الانتشار. حلل النص التالي بناءً على معايير Jonah Berger و Steal Like an Artist.
    
    [النص: {post_draft}]

    المطلوب تحليل دقيق باللغة العربية:
    1. درجة الانتشار الفيروسي (0-100): [أعطِ رقماً فقط]
    2. العواطف المحركة: [حدد العاطفة ونسبتها]
    3. تقييم الـ Hook: [لماذا سينجذب الناس في أول ثانيتين؟]
    4. 3 نصائح ذهبية لزيادة المشاركات (Shares).
    """

    track_cta() 

    with st.spinner("جاري فحص المحتوى بالذكاء الاصطناعي..."):
        try:
            # استخدام الموديل المستقر Gemini 2.0 Flash
            response = client.models.generate_content(
                model="gemini-2.0-flash-exp",
                contents=[prompt_template]
            )

            full_analysis = response.text
            st.success("✅ تم التحليل بنجاح!")

            # عرض النتيجة بشكل مميز
            st.markdown(f"""
            <div class="score-box">
                <p style="margin:0; font-size:1.2em;">النتيجة المتوقعة</p>
                <h1 style="margin:0; color:#4CAF50;">{full_analysis.splitlines()[0] if full_analysis else '--'}</h1>
            </div>
            """, unsafe_allow_html=True)

            st.markdown("### 📊 التحليل التفصيلي")
            st.info(full_analysis)

        except Exception as e:
            st.error(f"حدث خطأ في الاتصال بالذكاء الاصطناعي: {e}")

# ==========================================
# 5. التذييل وتتبع الوقت
# ==========================================

st.markdown(
    '<div class="custom-footer">جميع الحقوق محفوظة © 2026 | AI Product Builder - Layan Khalil</div>', 
    unsafe_allow_html=True
)

if 'start_time' in st.session_state:
    duration = time.time() - st.session_state.start_time
    try:
        supabase.rpc('update_time', {'row_id': APP_ID, 'sec': duration}).execute()
    except:
        pass