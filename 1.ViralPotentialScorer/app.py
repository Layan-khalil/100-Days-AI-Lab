import streamlit as st
import uuid
import time
from datetime import datetime
from supabase import create_client, Client
from google import genai
from google.genai import types

# ==========================================
# 1. إعدادات الأمان والاتصال (Secrets)
# ==========================================
try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
    GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
except Exception:
    st.error("Missing Secrets! Please check your settings.")
    st.stop()

# إنشاء العملاء
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
genai_client = genai.Client(api_key=GOOGLE_API_KEY)
APP_ID = "viral-potential-scorer-v1"

# ==========================================
# 2. وظائف الداتا بيس (Database & Analytics)
# ==========================================

def track_visit():
    """تسجيل الزيارة الأولى للجلسة"""
    if 'tracked_session' not in st.session_state:
        st.session_state.tracked_session = True
        visitor_id = str(uuid.uuid4())
        
        try:
            # إضافة سجل الزيارة الخام
            supabase.table("visitor_logs").insert({
                "visitor_id": visitor_id,
                "app_id": APP_ID
            }).execute()
            
            # تحديث عداد الزوار الفريدين والمشاهدات
            supabase.rpc('increment_analytics', {
                'row_id': APP_ID,
                'v_inc': 1,
                'u_inc': 1,
                'r_inc': 0
            }).execute()
        except:
            pass

def track_cta_action():
    """تسجيل ضغطة زر التحليل"""
    try:
        supabase.rpc('increment_cta', {'row_id': APP_ID}).execute()
    except:
        pass

# تشغيل تتبع الزيارة فور تحميل الصفحة
track_visit()

# ==========================================
# 3. التصميم وواجهة المستخدم (UI)
# ==========================================
st.set_page_config(page_title="Viral Scorer | مُحلّل الانتشار", layout="centered")

st.markdown("""
    <style>
    [data-testid="stAppViewContainer"] { direction: rtl; text-align: right; }
    .stTextArea textarea { direction: rtl; text-align: right; border-radius: 12px; font-size: 16px; }
    .stButton button { 
        width: 100%; border-radius: 25px; height: 3.8em; 
        background-color: #e63946 !important; color: white !important; 
        font-weight: bold; font-size: 18px; border: none;
    }
    .score-box { 
        background: #ffffff; padding: 30px; border-radius: 20px; 
        text-align: center; border: 3px solid #e63946; margin: 25px 0;
        box-shadow: 0 4px 15px rgba(230, 57, 70, 0.1);
    }
    .factor-item {
        background: #f8f9fa; padding: 10px 15px; border-right: 5px solid #e63946;
        margin: 5px 0; border-radius: 5px; font-weight: bold;
    }
    .custom-footer { text-align: center; color: #888; margin-top: 60px; padding: 20px; border-top: 1px solid #eee; }
    </style>
""", unsafe_allow_html=True)

st.title("🎯 مُحلّل احتمالية الانتشار الفيروسي")
st.write("أدخل نص منشورك أو سكريبت الفيديو لتحليله بناءً على علم نفس المحتوى (STEPPS).")

with st.expander("💡 تعرف على العوامل الستة للانتشار (Jonah Berger)"):
    st.markdown("""
    - **العملة الاجتماعية:** هل يجعل المحتوى المشارك يبدو ذكياً؟
    - **المحفزات:** هل المحتوى مرتبط بأحداث يومية متكررة؟
    - **المشاعر:** هل يثير عواطف قوية (دهشة، حماس، فضول)؟
    - **الظهور العام:** هل من السهل رؤية وتقليد هذا السلوك؟
    - **القيمة العملية:** هل يقدم فائدة حقيقية أو نصيحة موفرة للجهد؟
    - **القصص:** هل المعلومة مغلفة بقصة مشوقة؟
    """)

post_content = st.text_area("ألصق النص المراد تحليله هنا:", height=180, placeholder="مثلاً: قصة نجاح، نصيحة تعليمية، أو عرض ترويجي...")

# ==========================================
# 4. معالجة التحليل (AI Analytics)
# ==========================================
if st.button("بدء التحليل العلمي 🚀"):
    if not post_content.strip() or len(post_content.strip()) < 15:
        st.warning("الرجاء إدخال نص كافٍ (15 حرفاً على الأقل) ليتمكن النظام من تحليله.")
    else:
        # تسجيل ضغطة الزر في الداتا بيس
        track_cta_action()
        
        with st.spinner("جاري فحص الروابط النفسية في النص..."):
            try:
                # إعدادات صارمة جداً لضمان ثبات النتيجة 100% لنفس النص
                strict_config = types.GenerateContentConfig(
                    temperature=0.0, # صفر تعني ثبات رياضي
                    top_p=0.1,
                    top_k=1,
                    max_output_tokens=1000
                )
                
                analysis_prompt = f"""
                أنت خبير سيكولوجي متخصص في تحليل المحتوى الفيروسي.
                مهمتك: تحليل النص المرفق بناءً على معايير STEPPS الستة.
                
                قواعد صارمة:
                1. يجب أن تكون النتائج والدرجات الرقمية ثابتة تماماً لنفس النص ولا تتغير عند إعادة المحاولة.
                2. في السطر الأول، اكتب فقط: (النتيجة المتوقعة: X/100).
                3. في الأسطر التالية، أعطِ تقييماً لكل عامل من العوامل الستة من 10 (مثلاً: المشاعر: 8/10) مع شرح قصير جداً.
                
                النص المراد تحليله:
                {post_content}
                """

                response = genai_client.models.generate_content(
                    model="gemini-2.0-flash-exp",
                    contents=analysis_prompt,
                    config=strict_config
                )
                
                analysis_result = response.text
                lines = analysis_result.split('\n')
                main_score = lines[0] if lines else "جاري استخراج النتيجة..."
                
                # عرض النتيجة الكبيرة
                st.markdown(f'<div class="score-box"><p style="margin:0; color:#666;">إجمالي احتمالية الانتشار</p><h1 style="color:#e63946; margin:0; font-size:48px;">{main_score}</h1></div>', unsafe_allow_html=True)
                
                st.subheader("📊 تفاصيل العوامل السيكولوجية")
                st.info(analysis_result)
                
            except Exception:
                st.error("عذراً، تعذر الاتصال بمحرك التحليل. تأكد من إعدادات API Key.")

# الفوتر الثابت
st.markdown('<div class="custom-footer">جميع الحقوق محفوظة © 2026 | AI Product Builder - Layan Khalil</div>', unsafe_allow_html=True)