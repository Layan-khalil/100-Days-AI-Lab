import streamlit as st
import pandas as pd
import os
import uuid
import time
from datetime import datetime
from supabase import create_client, Client
from google import genai
from google.genai import types 
import google.api_core.exceptions

# ==========================================
# 1. إعدادات الأمان والاتصال
# ==========================================

try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
    GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
except Exception:
    st.error("⚠️ خطأ في المفاتيح السرية!")
    st.stop()

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
client = genai.Client(api_key=GOOGLE_API_KEY)
APP_ID = "viral-potential-scorer-v1"

# ==========================================
# 2. نظام التتبع لاتخاذ قرار الـ MVP
# ==========================================

def track_metrics():
    # التحقق: هل هذه أول مرة يفتح فيها المتصفح التطبيق في هذه الجلسة؟
    if 'tracked' not in st.session_state:
        visitor_id = str(uuid.uuid4())
        st.session_state.visitor_id = visitor_id
        st.session_state.tracked = True # علامة لمنع التكرار عند إعادة التشغيل
        
        try:
            # 1. تسجيل بصمة الزيارة (مرة واحدة فقط)
            supabase.table("visitor_logs").insert({
                "visitor_id": visitor_id, 
                "app_id": APP_ID
            }).execute()
            
            # 2. تحديث عدادات الإحصائيات (الزوار الفريدين)
            supabase.rpc('increment_analytics', {
                'row_id': APP_ID, 
                'v_inc': 1, 
                'u_inc': 1, 
                'r_inc': 0
            }).execute()
        except:
            pass
    else:
        # إذا قام بعمل Refresh، نزيد عدد المشاهدات والزوار العائدين فقط
        if 'refreshed' not in st.session_state:
            st.session_state.refreshed = True
            try:
                supabase.rpc('increment_analytics', {
                    'row_id': APP_ID, 
                    'v_inc': 1, 
                    'u_inc': 0, 
                    'r_inc': 1 
                }).execute()
            except:
                pass

def track_cta():
    """هذا التابع يقيس 'الرغبة' (Intent) لدى المستخدمين"""
    try:
        supabase.rpc('increment_cta', {'row_id': APP_ID}).execute()
    except:
        pass

# تشغيل نظام التتبع
track_metrics()

# ==========================================
# 3. واجهة التطبيق (نفس التصميم المطلوب)
# ==========================================

st.set_page_config(page_title="مُحلّل إمكانية العدوى الفيروسية", layout="centered")

st.markdown("""
    <style>
    [data-testid="stAppViewContainer"], .main, .stApp { direction: rtl !important; text-align: right !important; }
    div[data-testid="stExpander"] div, div.stMarkdown, p, li { text-align: right !important; direction: rtl !important; }
    h1, h2, h3 { text-align: right !important; direction: rtl !important; }
    .stTextArea textarea { text-align: right !important; direction: rtl !important; border-radius: 15px; font-size: 16px !important; }
    .stButton button { width: 100%; border-radius: 25px; height: 3.5em; font-weight: bold; background-color: #e63946 !important; color: white !important; border: none; }
    .stButton button:hover { background-color: #d62828 !important; }
    .score-box { background: #f0f2f6; padding: 5% 2%; border-radius: 15px; text-align: center !important; border: 2px solid #e63946; margin: 20px 0; }
    .custom-footer { display: flex; justify-content: center; align-items: center; padding: 20px; color: #666; font-size: 0.85em; border-top: 1px solid #eee; margin-top: 50px; direction: rtl !important; gap: 10px; flex-wrap: wrap; }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

st.markdown('<h1 style="text-align:center !important;">🎯 مُحلّل احتمالية الانتشار (Viral Scorer)</h1>', unsafe_allow_html=True)
st.markdown('<p style="text-align:center !important;">اكتشف مدى قابلية منشورك للانتشار الفيروسي باستخدام علم نفس المحتوى والذكاء الاصطناعي.</p>', unsafe_allow_html=True)

with st.expander("💡 كيف يعمل هذا التطبيق؟ شرح عوامل الانتشار الستة"):
    st.markdown("""
    <div style="text-align: right; direction: rtl;">
    يعتمد هذا التطبيق على منهجية العلم <b>"STEPPS"</b> للعالم جونا بيرجر، وهي ستة عوامل تجعل المحتوى ينتشر كالنار في الهشيم:
    <br><br>
    <b>1. العملة الاجتماعية (Social Currency):</b> نحن نشارك الأشياء التي تجعلنا نبدو أذكياء أو مطلعين أو ناجحين أمام الآخرين.
    <br><br>
    <b>2. المحفزات (Triggers):</b> المحتوى الناجح هو الذي يذكره الناس باستمرار لأنه مرتبط ببيئتهم اليومية.
    <br><br>
    <b>3. المشاعر (Emotion):</b> عندما نهتم، نشارك. المشاعر ذات الاستثارة العالية تدفع الناس لاتخاذ إجراء ومشاركة المحتوى.
    <br><br>
    <b>4. الظهور العام (Public):</b> كلما كان من السهل رؤية الآخرين وهم يتفاعلون مع المحتوى، زاد احتمال تقليدهم.
    <br><br>
    <b>5. القيمة العملية (Practical Value):</b> نحن نحب مساعدة الآخرين. المنشورات التي تقدم نصائح حقيقية هي الأكثر انتشاراً.
    <br><br>
    <b>6. القصص (Stories):</b> المعلومات تنتشر بشكل أفضل إذا كانت داخل قصة مشوقة.
    </div>
    """, unsafe_allow_html=True)

st.divider()

post_draft = st.text_area("ألصق مسودة منشورك هنا:", height=200, placeholder="اكتب مسودة منشورك هنا...")

if st.button("تحليل العوامل النفسية 🚀", type="primary") and post_draft:
    if len(post_draft.strip()) < 30:
        st.warning("يرجى إدخال نص أطول قليلاً للحصول على تحليل دقيق.")
    else:
        # تسجيل أن المستخدم مهتم فعلاً بالتحليل (لأغراض الـ MVP)
        track_cta() 
        
        with st.spinner("جاري التحليل يرجى الانتظار قليلاً"):
            time.sleep(10)
            try:
                # طلب التحليل من Gemini 2.0 Flash (الوضع المنطقي الثابت)
                response = client.models.generate_content(
                    model="gemini-2.0-flash-exp",
                    contents=[f"أنت خبير سيكولوجي دقيق. حلل هذا النص بناءً على معايير Jonah Berger (STEPPS). يجب أن تكون الدرجة ثابتة ومنطقية. أجب بالعربية مع ذكر الدرجة من 100 في أول سطر فقط: {post_draft}"],
                    config=types.GenerateContentConfig(temperature=0, top_p=0.1, top_k=1)
                )
                
                full_analysis = response.text
                st.success("✅ تم التحليل بنجاح!")
                
                score_line = full_analysis.splitlines()[0]
                st.markdown(f'<div class="score-box"><p>النتيجة المتوقعة</p><h1 style="color:#e63946;">{score_line}</h1></div>', unsafe_allow_html=True)
                
                st.markdown("### 📊 التحليل التفصيلي")
                st.info(full_analysis)
                
            except Exception as e:
                st.error("عذراً، حدث خطأ أثناء الاتصال بالذكاء الاصطناعي.")

# الفوتر
st.markdown(f'<div class="custom-footer"><span>جميع الحقوق محفوظة © 2026</span><span>|</span><span style="direction: ltr; display: inline-block;">AI Product Builder - Layan Khalil</span></div>', unsafe_allow_html=True)