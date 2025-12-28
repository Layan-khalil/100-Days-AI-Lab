import streamlit as st
from google import genai
from google.genai import types as g_types
import json

# =================================================================
# 1. إعدادات الصفحة والتنسيق (RTL & Professional UI)
# =================================================================

st.set_page_config(
    page_title="مُنشئ مسارات التحويل المُصغّرة",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# قواعد CSS لفرض التنسيق والزر العريض والمحاذاة
st.markdown("""
<style>
    /* فرض اتجاه اليمين للغة العربية */
    html, body, .block-container, .stApp { direction: rtl !important; }
    h1, h2, h3, h4, h5, h6, p, .stMarkdown, .stText, .stAlert, label { text-align: right !important; direction: rtl !important; }

    /* محاذاة الـ Expander لليمين */
    div[data-testid="stExpander"] .stMarkdown p, 
    div[data-testid="stExpander"] .stMarkdown li {
        text-align: right !important;
        direction: rtl !important;
    }

    /* === تنسيق الزر العريض (Stretch) === */
    div.stButton > button { 
        font-weight: bold !important; 
        width: 100% !important; 
        background-color: #10b981 !important; /* أخضر نمو */
        color: white !important; 
        border-radius: 10px !important; 
        padding: 15px !important; 
        font-size: 1.2em !important; 
        border: none !important;
        box-shadow: 0 4px 15px rgba(16, 185, 129, 0.3) !important; 
        display: block !important;
        margin-top: 10px !important;
    }
    div.stButton > button:hover { 
        background-color: #059669 !important; 
        transform: translateY(-2px) !important; 
    }

    /* بطاقة المسار */
    .path-card {
        background-color: #f0fdf4;
        padding: 25px;
        border-radius: 15px;
        border-right: 8px solid #10b981;
        margin-top: 25px;
        text-align: right !important;
    }

    .step-box {
        background-color: white;
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #d1fae5;
        margin-bottom: 15px;
    }

    .step-number {
        background-color: #10b981;
        color: white;
        width: 25px;
        height: 25px;
        display: inline-block;
        text-align: center;
        border-radius: 50%;
        margin-left: 10px;
        font-weight: bold;
    }

    .custom-footer {
        position: fixed; bottom: 0; right: 0; left: 0;
        text-align: center; padding: 10px;
        background-color: #f8fafc; color: #64748b;
        font-size: 0.85em; border-top: 1px solid #e2e8f0; z-index: 100;
    }

    #MainMenu, footer, header { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# =================================================================
# 2. تهيئة نموذج Gemini
# =================================================================
client = None
try:
    client = genai.Client(api_key="")
except Exception:
    client = None

# =================================================================
# 3. دالة إنشاء مسار التحويل
# =================================================================

def build_conversion_path(topic, target_offer):
    if not client:
        return {"error": "فشل الاتصال بالذكاء الاصطناعي."}

    system_instruction = (
        "You are a Conversion Rate Optimization (CRO) Expert. "
        "Create a 3-step micro-conversion path for a given topic and offer. "
        "Step 1: High-impact CTA. Step 2: Irresistible Lead Magnet. Step 3: Engaging follow-up message. "
        "Output ONLY in Arabic JSON."
    )

    response_schema = {
        "type": "OBJECT",
        "properties": {
            "cta": {"type": "STRING", "description": "عبارة النداء لاتخاذ إجراء (CTA)"},
            "lead_magnet": {"type": "STRING", "description": "نوع المغناطيس الجاذب والمحتوى الخاص به"},
            "follow_up": {"type": "STRING", "description": "رسالة المتابعة الموصى بها"},
            "strategy_logic": {"type": "STRING", "description": "لماذا هذا المسار فعال؟"}
        },
        "required": ["cta", "lead_magnet", "follow_up", "strategy_logic"]
    }

    try:
        prompt = f"الموضوع: {topic}, العرض النهائي: {target_offer}. صمم مسار تحويل مصغر."
        response = client.models.generate_content(
            model='gemini-2.5-flash-preview-09-2025',
            contents=prompt,
            config=g_types.GenerateContentConfig(
                system_instruction=system_instruction,
                response_mime_type="application/json",
                response_schema=response_schema
            )
        )
        return json.loads(response.text)
    except Exception as e:
        return {"error": "حدث خطأ أثناء إنشاء المسار."}

# =================================================================
# 4. واجهة المستخدم
# =================================================================

st.title("🔗 مُنشئ مسارات التحويل المُصغّرة")
st.write("حول جمهورك العابر إلى مشتركين أوفياء عبر مسار تحويل ذكي مكون من 3 خطوات.")

with st.expander("💡 ما هو التحويل المُصغّر (Micro-Conversion)؟"):
    st.markdown("""
    <div style="text-align: right; direction: rtl;">
    التحويل المصغر هو إجراء بسيط يسبق عملية الشراء الكبرى، مثل تحميل دليل مجاني أو الاشتراك في نشرة بريدية. 
    الفكرة هي تقليل "المقاومة" لدى العميل وبناء الثقة تدريجياً عبر:
    <ul>
        <li><b>نداء إجراء (CTA):</b> يثير الفضول ولا يطلب الكثير.</li>
        <li><b>مغناطيس (Lead Magnet):</b> يعطي قيمة فورية مقابل البريد الإلكتروني.</li>
        <li><b>المتابعة:</b> تضمن عدم نسيان العميل لك وتجهزه للخطوة التالية.</li>
    </ul>
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")

col1, col2 = st.columns(2)
with col1:
    topic = st.text_input("1. موضوع المحتوى أو المنشور:", placeholder="مثلاً: نصائح لزيادة إنتاجية العمل عن بعد")
with col2:
    offer = st.text_input("2. العرض أو الخدمة النهائية:", placeholder="مثلاً: كورس إدارة الوقت الاحترافي")

# الزر العريض
if st.button("🚀 توليد مسار التحويل الآن", use_container_width=True):
    if not topic.strip() or not offer.strip():
        st.warning("الرجاء إدخال الموضوع والعرض لضمان دقة المسار.")
    else:
        with st.spinner("جاري تصميم هندسة التحويل..."):
            result = build_conversion_path(topic, offer)
            
            if "error" in result:
                st.error(result["error"])
            else:
                st.markdown("### 🗺️ مسار التحويل المقترح")
                st.markdown(f"""
                <div class="path-card">
                    <div class="step-box">
                        <span class="step-number">1</span> <b>عبارة النداء (CTA):</b><br>
                        <p style="color: #065f46; margin-top: 5px;">{result.get('cta', '')}</p>
                    </div>
                    <div class="step-box">
                        <span class="step-number">2</span> <b>المغناطيس الجاذب (Lead Magnet):</b><br>
                        <p style="color: #065f46; margin-top: 5px;">{result.get('lead_magnet', '')}</p>
                    </div>
                    <div class="step-box">
                        <span class="step-number">3</span> <b>رسالة المتابعة الأولى:</b><br>
                        <p style="color: #065f46; margin-top: 5px;">{result.get('follow_up', '')}</p>
                    </div>
                    <p style="font-size: 0.9em; border-top: 1px solid #d1fae5; padding-top: 10px;">
                        🎯 <b>المنطق الاستراتيجي:</b> {result.get('strategy_logic', '')}
                    </p>
                </div>
                """, unsafe_allow_html=True)

st.markdown('<div style="height: 100px;"></div>', unsafe_allow_html=True)
st.markdown(
    '<div class="custom-footer">جميع الحقوق محفوظة © 2026 | AI Product Builder - Layan Khalil</div>', 
    unsafe_allow_html=True
)