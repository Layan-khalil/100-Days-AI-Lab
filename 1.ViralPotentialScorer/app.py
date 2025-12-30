import streamlit as st
import uuid
import time
from supabase import create_client, Client
from google import genai
from google.genai import types

# ==========================================
# 1. إعدادات الأمان والاتصال
# ==========================================
try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
    GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
except Exception as e:
    st.error("⚠️ فشل في تحميل المفاتيح السرية (Secrets). تأكد من إعدادات الـ Cloud.")
    st.stop()

# تهيئة العملاء
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
genai_client = genai.Client(api_key=GOOGLE_API_KEY)
APP_ID = "viral-potential-scorer-v1"

# ==========================================
# 2. نظام التتبع وتشخيص الأخطاء (DB Tracking)
# ==========================================

def track_visit():
    """يسجل الزيارة ويطبع الخطأ في الـ Logs إذا فشل"""
    if 'tracked_once' not in st.session_state:
        st.session_state.tracked_once = True
        vid = str(uuid.uuid4())
        
        try:
            # محاولة الإدخال في جدول visitor_logs
            res_log = supabase.table("visitor_logs").insert({
                "visitor_id": vid, 
                "app_id": APP_ID
            }).execute()
            
            # محاولة تحديث جدول analytics
            res_rpc = supabase.rpc('increment_analytics', {
                'row_id': APP_ID, 
                'v_inc': 1, 
                'u_inc': 1, 
                'r_inc': 0
            }).execute()
            
        except Exception as e:
            # طباعة الخطأ في سجلات السيرفر للمطور
            st.write(f"<!-- DB Error Trace: {str(e)} -->", unsafe_allow_html=True)
            print(f"CRITICAL DB ERROR: {e}")

def track_cta():
    """يسجل ضغطة الزر ويطبع الخطأ في الـ Logs إذا فشل"""
    try:
        supabase.rpc('increment_cta', {'row_id': APP_ID}).execute()
    except Exception as e:
        print(f"CTA EVENT ERROR: {e}")

# تنفيذ التتبع فوراً
track_visit()

# ==========================================
# 3. واجهة المستخدم (UI Design)
# ==========================================
st.set_page_config(page_title="Viral Scorer | مُحلّل الانتشار", layout="centered")

st.markdown("""
    <style>
    [data-testid="stAppViewContainer"] { direction: rtl; text-align: right; }
    .stTextArea textarea { direction: rtl; text-align: right; border-radius: 12px; border: 1px solid #ddd; }
    .stButton button { 
        width: 100%; border-radius: 25px; height: 3.5em; 
        background-color: #e63946 !important; color: white !important; 
        font-weight: bold; border: none; transition: 0.3s;
    }
    .stButton button:hover { background-color: #c1121f !important; transform: scale(1.02); }
    .score-box { 
        background: #f8f9fa; padding: 20px; border-radius: 15px; 
        text-align: center; border: 2px solid #e63946; margin: 20px 0;
        box-shadow: 0 4px 10px rgba(0,0,0,0.05);
    }
    .footer { text-align: center; color: #777; font-size: 0.8em; margin-top: 50px; border-top: 1px solid #eee; padding-top: 20px; }
    </style>
""", unsafe_allow_html=True)

st.title("🎯 مُحلّل احتمالية الانتشار")
st.markdown("حلل منشوراتك بناءً على معايير علم نفس المحتوى الستة (STEPPS) لضمان أعلى وصول.")

post_input = st.text_area("ألصق نص المنشور أو الفيديو هنا:", height=150, placeholder="اكتب هنا...")

# ==========================================
# 4. محرك التحليل (AI Analytics)
# ==========================================
if st.button("تحليل الآن 🚀"):
    if not post_input.strip():
        st.warning("يرجى إدخال نص أولاً.")
    else:
        track_cta() # تسجيل المحاولة في الداتا بيس
        
        with st.spinner("جاري التحليل العلمي..."):
            try:
                # إعدادات لضمان ثبات النتيجة 100% (Deterministic)
                generation_config = types.GenerateContentConfig(
                    temperature=0.0, # لا يوجد عشوائية
                    top_p=0.1,
                    top_k=1
                )
                
                # توجيه الموديل للالتزام بالمعايير والدرجات الثابتة
                prompt_text = f"""
                حلل النص التالي بناءً على معايير STEPPS لـ Jonah Berger.
                يجب أن تكون الدرجة النهائية ثابتة ومنطقية ولا تتغير عند إعادة طلب نفس النص.
                
                التنسيق المطلوب:
                1. في أول سطر: (النتيجة: X/100)
                2. ثم تقييم العوامل الستة من 10 مع شرح بسيط جداً.
                
                النص: {post_input}
                """
                
                response = genai_client.models.generate_content(
                    model="gemini-2.5-flash-preview-09-2025",
                    contents=prompt_text,
                    config=generation_config
                )
                
                output = response.text
                final_score = output.split('\n')[0]
                
                st.markdown(f'<div class="score-box"><h2 style="color:#e63946;">{final_score}</h2></div>', unsafe_allow_html=True)
                st.info(output)
                
            except Exception as e:
                st.error("تعذر الاتصال بالذكاء الاصطناعي حالياً. يرجى المحاولة لاحقاً.")

st.markdown('<div class="footer">جميع الحقوق محفوظة © 2026 | AI Product Builder - Layan Khalil</div>', unsafe_allow_html=True)