import streamlit as st
import pandas as pd
import os
import uuid
import time
from supabase import create_client, Client
from google import genai
import google.api_core.exceptions

# ==========================================
# 1. إعدادات الأمان والاتصال (Secrets Management)
# ==========================================

try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
    GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
except Exception:
    st.error("⚠️ خطأ: المفاتيح السرية غير موجودة! يرجى إضافتها في Settings > Secrets")
    st.stop()

# إنشاء عملاء الاتصال
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
client = genai.Client(api_key=GOOGLE_API_KEY)

# --- معرف التطبيق الفريد ---
APP_ID = "viral-potential-scorer-v1"

# ==========================================
# 2. نظام التتبع (Analytics Engine)
# ==========================================

def track_metrics():
    if 'visitor_id' not in st.session_state:
        st.session_state.visitor_id = str(uuid.uuid4())
        st.session_state.start_time = time.time()
        try:
            res = supabase.table("visitor_logs").select("*").eq("visitor_id", st.session_state.visitor_id).eq("app_id", APP_ID).execute()
            if len(res.data) == 0:
                supabase.table("visitor_logs").insert({"visitor_id": st.session_state.visitor_id, "app_id": APP_ID}).execute()
                supabase.rpc('increment_analytics', {'row_id': APP_ID, 'v_inc': 1, 'u_inc': 1, 'r_inc': 0}).execute()
            else:
                supabase.rpc('increment_analytics', {'row_id': APP_ID, 'v_inc': 1, 'u_inc': 0, 'r_inc': 1}).execute()
        except: pass

def track_cta():
    try: supabase.rpc('increment_cta', {'row_id': APP_ID}).execute()
    except: pass

track_metrics()

# ==========================================
# 3. إعدادات واجهة التطبيق (UI Settings)
# ==========================================

st.set_page_config(
    page_title="مُحلّل إمكانية العدوى الفيروسية",
    layout="centered",
    initial_sidebar_state="collapsed",
)

st.markdown("""
    <style>
    [data-testid="stAppViewContainer"], .main, .stApp {
        direction: rtl !important;
        text-align: right !important;
    }
    
    div[data-testid="stExpander"] div, div.stMarkdown, p, li {
        text-align: right !important;
        direction: rtl !important;
    }

    h1, h2, h3 {
        text-align: right !important;
        direction: rtl !important;
    }

    .stTextArea textarea {
        text-align: right !important;
        direction: rtl !important;
        border-radius: 15px;
        font-size: 16px !important;
    }

    .stButton button {
        width: 100%;
        border-radius: 25px;
        height: 3.5em;
        font-weight: bold;
    }
    
    .score-box {
        background: #f0f2f6;
        padding: 5% 2%;
        border-radius: 15px;
        text-align: center !important;
        border: 2px solid #4CAF50;
        margin: 20px 0;
    }

    .custom-footer { 
        display: flex;
        justify-content: center;
        align-items: center;
        padding: 20px;
        color: #666;
        font-size: 0.85em;
        border-top: 1px solid #eee;
        margin-top: 50px;
        direction: rtl !important;
        gap: 10px;
        flex-wrap: wrap;
    }

    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 4. واجهة التطبيق (App UI)
# ==========================================

st.markdown('<h1 style="text-align:center !important;">🎯 مُحلّل احتمالية الانتشار (Viral Scorer)</h1>', unsafe_allow_html=True)
st.markdown('<p style="text-align:center !important;">اكتشف مدى قابلية منشورك للانتشار الفيروسي باستخدام علم نفس المحتوى والذكاء الاصطناعي.</p>', unsafe_allow_html=True)

with st.expander("💡 كيف يعمل هذا التطبيق؟ شرح عوامل الانتشار الستة"):
    st.markdown("""
    <div style="text-align: right; direction: rtl;">
    يعتمد هذا التطبيق على منهجية العلم <b>"STEPPS"</b> للعالم جونا بيرجر، وهي ستة عوامل تجعل المحتوى ينتشر كالنار في الهشيم:
    <br><br>
    <b>1. العملة الاجتماعية (Social Currency):</b> نحن نشارك الأشياء التي تجعلنا نبدو أذكياء أو مطلعين أو ناجحين أمام الآخرين. المحتوى الذي يمنح المستخدم قيمة اجتماعية يرتفع احتمال مشاركته.
    <br><br>
    <b>2. المحفزات (Triggers):</b> المحتوى الناجح هو الذي يذكره الناس باستمرار لأنه مرتبط ببيئتهم اليومية. (مثلاً: منشور عن القهوة سيتذكره الناس كل صباح تلقائياً).
    <br><br>
    <b>3. المشاعر (Emotion):</b> عندما نهتم، نشارك. المشاعر ذات الاستثارة العالية (مثل الدهشة، الإعجاب، أو الفضول الشديد) تدفع الناس لاتخاذ إجراء ومشاركة المحتوى.
    <br><br>
    <b>4. الظهور العام (Public):</b> كلما كان من السهل رؤية الآخرين وهم يتفاعلون مع المحتوى، زاد احتمال تقليدهم. الناس يقلدون ما يرونه شائعاً ومنتشراً.
    <br><br>
    <b>5. القيمة العملية (Practical Value):</b> نحن نحب مساعدة الآخرين. المنشورات التي تقدم نصائح حقيقية، توفيراً للوقت، أو توفيراً للمال هي الأكثر انتشاراً لأنها مفيدة.
    <br><br>
    <b>6. القصص (Stories):</b> المعلومات تنتشر بشكل أفضل إذا كانت داخل قصة مشوقة. القصص هي "الأوعية" التي تحمل الأفكار وتجعلها سهلة الحفظ والانتقال.
    </div>
    """, unsafe_allow_html=True)

st.divider()

post_draft = st.text_area(
    "ألصق مسودة منشورك هنا:", 
    height=200, 
    placeholder="اكتب مسودة منشورك، تغريدتك، أو نص الفيديو هنا..."
)

if st.button("تحليل العوامل النفسية 🚀", type="primary") and post_draft:
    if len(post_draft.strip()) < 30:
        st.warning("يرجى إدخال نص أطول قليلاً للحصول على تحليل دقيق.")
    else:
        track_cta() 
        
        # استخدام الـ Spinner مع رسالة توضح الانتظار
        with st.spinner("جاري التحليل يرجى الانتظار قليلاً"):
            # تنفيذ الانتظار المطلوب (10 ثوانٍ)
            time.sleep(10)
            
            try:
                # محاولة الاتصال بـ Gemini 2.0
                response = client.models.generate_content(
                    model="gemini-2.0-flash-exp",
                    contents=[f"حلل هذا النص بناءً على معايير Jonah Berger (STEPPS): {post_draft}. أجب بالعربية مع ذكر الدرجة من 100 في أول سطر."]
                )
                
                full_analysis = response.text
                st.success("✅ تم التحليل بنجاح!")
                
                score_line = full_analysis.splitlines()[0]
                st.markdown(f'<div class="score-box"><p>النتيجة المتوقعة</p><h1 style="color:#4CAF50;">{score_line}</h1></div>', unsafe_allow_html=True)
                
                st.markdown("### 📊 التحليل التفصيلي")
                st.info(full_analysis)
                
            except Exception as e:
                if "429" in str(e):
                    st.error("عذراً، يبدو أن ضغط المستخدمين عالٍ جداً حالياً. يرجى الانتظار دقيقة واحدة ثم إعادة المحاولة.")
                else:
                    st.error(f"حدث خطأ غير متوقع: {e}")

# ==========================================
# 5. الفوتر (Footer)
# ==========================================

st.markdown(
    f"""
    <div class="custom-footer">
        <span>جميع الحقوق محفوظة © 2026</span>
        <span>|</span>
        <span style="direction: ltr; display: inline-block;">AI Product Builder - Layan Khalil</span>
    </div>
    """, 
    unsafe_allow_html=True
)