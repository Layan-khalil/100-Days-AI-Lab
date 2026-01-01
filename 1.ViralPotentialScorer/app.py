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
    st.error("⚠️ خطأ في المفاتيح السرية.")
    st.stop()

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
genai_client = genai.Client(api_key=GOOGLE_API_KEY)
APP_ID = "viral-potential-scorer-v1"

# ==========================================
# 2. نظام التتبع (Analytics)
# ==========================================
def track_visit():
    if 'visit_logged' not in st.session_state:
        st.session_state.visit_logged = True
        try:
            vid = str(uuid.uuid4())
            supabase.table("visitor_logs").insert({"visitor_id": vid, "app_id": APP_ID}).execute()
            supabase.rpc('increment_analytics', {'row_id': APP_ID, 'v_inc': 1, 'u_inc': 1, 'r_inc': 0}).execute()
        except:
            pass

track_visit()

# ==========================================
# 3. واجهة المستخدم (UI & CSS)
# ==========================================
st.set_page_config(page_title="Viral Scorer", layout="centered")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;700&display=swap');
    
    html, body, [data-testid="stAppViewContainer"] {
        direction: rtl !important;
        text-align: right !important;
        font-family: 'Cairo', sans-serif;
    }
    
    /* توسيط العنوان */
    .main-title {
        text-align: center !important;
        color: #e63946;
        font-weight: 700;
        margin-bottom: 30px;
    }
    
    div[data-testid="stExpander"] {
        direction: rtl !important;
        text-align: right !important;
        border-radius: 10px;
    }
    
    .stTextArea textarea {
        direction: rtl !important;
        text-align: right !important;
        border-radius: 12px;
    }
    
    .stButton button {
        width: 100%;
        border-radius: 25px;
        background-color: #e63946 !important;
        color: white !important;
        font-weight: bold;
        height: 3.5em;
        border: none;
    }
    
    .score-box {
        background: #ffffff;
        padding: 25px;
        border-radius: 15px;
        text-align: center;
        border: 2px solid #e63946;
        margin: 20px 0;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
    }

    .footer {
        direction: rtl !important;
        text-align: center !important;
        color: #888;
        margin-top: 60px;
        padding-top: 20px;
        border-top: 1px solid #eee;
        font-size: 0.9em;
    }
    </style>
""", unsafe_allow_html=True)

# العنوان في منتصف الصفحة
st.markdown('<h1 class="main-title">🎯 مُحلّل احتمالية الانتشار</h1>', unsafe_allow_html=True)

# الشرح المفصل داخل Expander
with st.expander("💡 عن التطبيق وكيف يتم التقييم؟"):
    st.markdown("""
    يتم تقييم المحتوى بناءً على إطار **STEPPS** العلمي، وإليك شرح العوامل الستة:
    - **العملة الاجتماعية:** قدرة المحتوى على تحسين صورة الشخص الذي يشاركه وجعله يبدو ذكياً أو مطلعاً أمام محيطه.
    - **المحفزات:** ربط الفكرة بعناصر من البيئة المحيطة أو أحداث يومية متكررة تضمن بقاء الفكرة حاضرة في الأذهان.
    - **الممشاعر:** استثارة عواطف قوية مثل الدهشة، الإثارة، أو الفخر، لأن المشاعر ذات الطاقة العالية تزيد من نسب المشاركة.
    - **الظهور العام:** تصميم المحتوى بحيث يسهل على الآخرين رؤية وتقليد السلوك المرتبط به، مما يخلق تأثيراً اجتماعياً فورياً.
    - **القيمة العملية:** تقديم معلومات مفيدة، نصائح حقيقية، أو حلول لمشاكل تساعد الناس في حياتهم وتوفر وقتهم.
    - **القصص:** صياغة الفكرة داخل رواية أو قصة مشوقة تجذب الانتباه وتجعل الرسالة الأساسية سهلة الحفظ والنقل للآخرين.
    """)

st.markdown("### أدخل نص المنشور أو سكريبت الفيديو:")
post_input = st.text_area("", height=150, placeholder="ابدأ الكتابة هنا...")

# ==========================================
# 4. محرك التحليل الثابت (Strict AI)
# ==========================================
if st.button("حلل المحتوى الآن 🚀"):
    if not post_input.strip():
        st.warning("يرجى إدخال نص للتحليل.")
    else:
        try:
            supabase.rpc('increment_cta', {'row_id': APP_ID}).execute()
        except:
            pass
            
        with st.spinner("جاري التحليل العلمي الثابت..."):
            try:
                # إعدادات صارمة للثبات (Deterministic Configuration)
                strict_config = types.GenerateContentConfig(
                    temperature=0.0, 
                    top_p=0.1, 
                    top_k=1,
                    candidate_count=1
                )
                
                # توجيه الموديل للالتزام بالثبات المطلق
                prompt = f"""
                أنت خبير سيكولوجي متخصص في تحليل المحتوى. حلل النص المرفق بناءً على معايير STEPPS الستة.
                قاعدة حتمية: يجب أن تكون الدرجة النهائية والتحليلات الرقمية ثابتة تماماً لنفس النص في كل مرة يتم فيها التحليل.
                
                المطلوب:
                1. السطر الأول: (النتيجة المتوقعة: X/100).
                2. تفصيل تقييم كل عامل من العوامل الستة من 10 مع ذكر السبب باختصار شديد.
                
                النص المراد تحليله:
                {post_input}
                """
                
                response = genai_client.models.generate_content(
                    model="gemini-2.0-flash-exp",
                    contents=prompt,
                    config=strict_config
                )
                
                res_text = response.text
                first_line = res_text.split('\n')[0]
                
                st.markdown(f'<div class="score-box"><h1 style="color:#e63946; margin:0;">{first_line}</h1></div>', unsafe_allow_html=True)
                st.info(res_text)
                
            except Exception:
                st.error("عذراً، حدث خطأ تقني في محرك التحليل.")

# الفوتر المحدث
st.markdown('<div class="footer">جميع الحقوق محفوظة © 2026 | AI Product Builder - Layan Khalil</div>', unsafe_allow_html=True)