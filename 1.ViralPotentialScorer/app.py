import streamlit as st
import uuid
from supabase import create_client, Client
from google import genai
from google.genai import types

# ==========================================
# 1. إعدادات الاتصال (Secrets)
# ==========================================
try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
    GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
except Exception:
    st.error("⚠️ فشل في تحميل المفاتيح السرية (Secrets).")
    st.stop()

# تهيئة العملاء
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
genai_client = genai.Client(api_key=GOOGLE_API_KEY)
APP_ID = "viral-potential-scorer-v1"

# ==========================================
# 2. وظائف التتبع المحدثة (Database Integration)
# ==========================================

def track_visit():
    """تسجيل الزيارة وتحديث الإحصائيات عبر RPC"""
    if 'session_tracked' not in st.session_state:
        st.session_state.session_tracked = True
        visitor_id = str(uuid.uuid4())
        
        try:
            # 1. تسجيل بصمة الزائر في visitor_logs
            supabase.table("visitor_logs").insert({
                "visitor_id": visitor_id,
                "app_id": APP_ID
            }).execute()
            
            # 2. استدعاء دالة increment_analytics لتحديث العدادات
            # يتم إرسال 1 للمشاهدات، 1 للزوار الفريدين، 0 للعائدين (كبداية)
            supabase.rpc('increment_analytics', {
                'row_id': APP_ID,
                'v_inc': 1,
                'u_inc': 1,
                'r_inc': 0
            }).execute()
        except Exception as e:
            # طباعة الخطأ في سجلات السيرفر فقط للمطور
            print(f"Tracking Error: {e}")

def track_cta_event():
    """تسجيل ضغطة زر التحليل (CTA) عبر RPC"""
    try:
        supabase.rpc('increment_cta', {'row_id': APP_ID}).execute()
    except Exception as e:
        print(f"CTA Error: {e}")

# تنفيذ التتبع عند تحميل الصفحة
track_visit()

# ==========================================
# 3. واجهة المستخدم والتصميم (RTL Support)
# ==========================================
st.set_page_config(page_title="Viral Scorer | مُحلّل الانتشار", layout="centered")

# تنسيق RTL لكامل التطبيق مع استثناء الفوتر
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;700&display=swap');
    
    html, body, [data-testid="stAppViewContainer"], .main {
        direction: rtl !important;
        text-align: right !important;
        font-family: 'Cairo', sans-serif;
    }
    
    .stTextArea textarea {
        direction: rtl !important;
        text-align: right !important;
        border-radius: 12px;
    }
    
    .stButton button {
        width: 100%;
        border-radius: 25px;
        height: 3.5em;
        background-color: #e63946 !important;
        color: white !important;
        font-weight: bold;
        border: none;
    }
    
    .score-box {
        background: #f8f9fa;
        padding: 25px;
        border-radius: 15px;
        text-align: center;
        border: 2px solid #e63946;
        margin: 20px 0;
    }

    
    .custom-footer {
        position: fixed; bottom: 0; right: 0; left: 0;
        text-align: center; padding: 10px;
        background-color: #f8fafc; color: #64748b;
        font-size: 0.85em; border-top: 1px solid #e2e8f0; z-index: 100;
    }
    </style>
""", unsafe_allow_html=True)

st.title("🎯 مُحلّل احتمالية الانتشار")

# Expander الشرح تحت العنوان
with st.expander("💡 عن التطبيق وكيفية التحليل"):
    st.markdown("""
    يعتمد هذا المحلل على معايير **STEPPS** العلمية (العملة الاجتماعية، المحفزات، المشاعر، الظهور العام، القيمة العملية، والقصص).
    أدخل نصك وسيقوم الذكاء الاصطناعي بقياس مدى قابليته للانتشار بناءً على هذه العوامل السيكولوجية.
    """)

post_text = st.text_area("ألصق نص المنشور أو سكريبت الفيديو هنا:", height=150)

# ==========================================
# 4. معالجة التحليل بالذكاء الاصطناعي الثابت
# ==========================================
if st.button("تحليل الآن 🚀"):
    if not post_text.strip():
        st.warning("يرجى إدخال نص للتحليل.")
    else:
        # تسجيل ضغطة الزر في قاعدة البيانات
        track_cta_event()
        
        with st.spinner("جاري التحليل العلمي..."):
            try:
                # إعدادات صارمة جداً لمنع التشتت (Deterministic)
                gen_config = types.GenerateContentConfig(
                    temperature=0.0,
                    top_p=0.1,
                    top_k=1,
                    max_output_tokens=800
                )
                
                # صياغة البرومبت لضمان ثبات النتائج لكل عامل
                prompt = f"""
                أنت خبير محتوى فيروسي. حلل النص التالي بناءً على معايير STEPPS لـ Jonah Berger.
                يجب أن تكون الدرجة والنتائج ثابتة تماماً لنفس النص عند تكرار التحليل.
                
                التنسيق المطلوب باللغة العربية:
                1. في السطر الأول فقط: (النتيجة المتوقعة: X/100)
                2. ثم تقييم العوامل الستة من 10 مع شرح موجز لكل منها.
                
                النص: {post_text}
                """
                
                response = genai_client.models.generate_content(
                    model="gemini-2.0-flash-exp",
                    contents=prompt,
                    config=gen_config
                )
                
                full_response = response.text
                # استخراج السطر الأول (الدرجة) لعرضه بشكل مميز
                score_header = full_response.split('\n')[0]
                
                st.markdown(f'<div class="score-box"><h2 style="color:#e63946; margin:0;">{score_header}</h2></div>', unsafe_allow_html=True)
                st.info(full_response)
                
            except Exception:
                st.error("عذراً، حدث خطأ في محرك التحليل. يرجى المحاولة لاحقاً.")

# الفوتر بتنسيق LTR
st.markdown(
    '<div class="custom-footer">جميع الحقوق محفوظة © 2026 | AI Product Builder - Layan Khalil</div>', 
    unsafe_allow_html=True
)