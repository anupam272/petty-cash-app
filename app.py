import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
from datetime import datetime
from supabase import create_client, Client
import json
import re
import io

try:
    import easyocr
    @st.cache_resource
    def load_ocr_reader():
        return easyocr.Reader(['en'], gpu=False)
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False

@st.cache_resource
def init_supabase() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_ANON_KEY"]
    return create_client(url, key)

try:
    supabase = init_supabase()
except Exception as e:
    st.error("Supabase Connection Error! Please set secrets in Streamlit Cloud.")
    st.stop()

st.set_page_config(page_title="PRISM Petty Cash Management", page_icon="🏢", layout="wide")

# SAP Fiori Horizon Theme Styling
st.markdown("""
    <style>
    .stApp {
        background-color: #f5f6f7;
        font-family: "72", "72full", Arial, Helvetica, sans-serif;
    }
    
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    [data-testid="stFileUploader"] section small {
        display: none !important;
    }

    .main-header {
        font-size: 20px; 
        font-weight: 600; 
        color: #1d2d3e; 
        margin-bottom: 20px; 
        display: flex; 
        align-items: center; 
        gap: 10px;
        border-bottom: 2px solid #0070f2;
        padding-bottom: 10px;
        background-color: #ffffff;
        padding: 12px 16px;
        border-radius: 4px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }

    .stButton>button {
        width: 100%; 
        border-radius: 4px; 
        font-weight: 600; 
        background-color: #0070f2; 
        color: white;
        border: 1px solid #0070f2;
        padding: 6px 16px;
        box-shadow: 0 1px 2px rgba(0,0,0,0.1);
    }
    .stButton>button:hover {
        background-color: #005cc5; 
        color: white;
        border: 1px solid #005cc5;
    }

    section[data-testid="stSidebar"] {
        background-color: #1d2d3e;
        color: #ffffff;
        border-right: 1px solid #2c3e50;
    }
    section[data-testid="stSidebar"] .stMarkdown, 
    section[data-testid="stSidebar"] span, 
    section[data-testid="stSidebar"] p, 
    section[data-testid="stSidebar"] label {
        color: #ffffff !important;
    }
    
    section[data-testid="stSidebar"] div[data-baseweb="radio"] div {
        color: #ffffff !important;
    }

    .fiori-label {
        font-size: 13px !important;
        font-weight: 700 !important;
        color: #32363a !important;
        margin-bottom: 4px;
        letter-spacing: 0.1px;
    }
    .fiori-required {
        color: #bb0000 !important;
        font-weight: 700;
    }
    
    div[data-testid="stForm"] {
        background-color: #ffffff;
        padding: 24px;
        border-radius: 8px;
        border: 1px solid #e5e5e5;
        box-shadow: 0 2px 4px rgba(0,0,0,0.02);
    }
    </style>
""", unsafe_allow_html=True)

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "user_role" not in st.session_state:
    st.session_state.user_role = None
if "username" not in st.session_state:
    st.session_state.username = None
if "user_info" not in st.session_state:
    st.session_state.user_info = None

def check_password_policy(password):
    if len(password) < 8:
        return False, "Password must be at least 8 characters long."
    if not re.search(r"[A-Z]", password):
        return False, "At least 1 Capital letter (A-Z) is required."
    if not re.search(r"\d", password):
        return False, "At least 1 Number (0-9) is required."
    if not re.search(r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>/?]", password):
        return False, "At least 1 Special character (@, #, $) is required."
    return True, "Valid"

def fetch_records():
    res = supabase.table("petty_cash").select("*").order("id", desc=True).execute()
    return pd.DataFrame(res.data) if res.data else pd.DataFrame()

def fetch_hotel_masters():
    try:
        res = supabase.table("hotel_master").select("*").execute()
        return pd.DataFrame(res.data) if res.data else pd.DataFrame()
    except Exception as e:
        st.sidebar.warning(f"Note: hotel_master table issue: {e}")
        return pd.DataFrame()

PRISM_LOGO_URL = "https://www.prismlife.com/img/logo.webp"

st.sidebar.markdown(f"<img src='{PRISM_LOGO_URL}' style='max-width: 100px; margin-bottom: 10px; background: white; padding: 5px; border-radius: 4px;'>", unsafe_allow_html=True)

components.html("""
    <div id="local-time" style="font-size: 12px; color: #73c0ff; font-weight: 600; margin-bottom: 15px; font-family: '72', Arial, sans-serif;">
        📅 Loading local time...
    </div>
    <script>
    function updateTime() {
        const now = new Date();
        const options = { 
            day: '2-digit', 
            month: 'short', 
            year: 'numeric', 
            hour: '2-digit', 
            minute: '2-digit', 
            second: '2-digit',
            hour12: true 
        };
        document.getElementById('local-time').innerText = '📅 ' + now.toLocaleString('en-GB', options);
    }
    updateTime();
    setInterval(updateTime, 1000);
    </script>
""", height=28)

if st.session_state.authenticated:
    user_data = st.session_state.user_info
    st.sidebar.markdown(f"<div style='font-size: 13px; line-height: 1.5;'><span style='color: #b0c4de;'>User:</span> <strong style='color: #ffffff;'>{st.session_state.username}</strong><br><span style='color: #b0c4de;'>Role:</span> <strong style='color: #ffffff;'>{st.session_state.user_role}</strong><br><span style='color: #b0c4de;'>Prism ID:</span> <strong style='color: #ffffff;'>{user_data.get('assigned_prism_id', 'N/A')}</strong></div>", unsafe_allow_html=True)
    st.sidebar.markdown("<hr style='border-color: #2c3e50; margin: 15px 0;'>", unsafe_allow_html=True)
    
    st.sidebar.markdown("<span style='font-size: 11px; text-transform: uppercase; letter-spacing: 1px; color: #8fa1b3; font-weight: bold;'>Navigation</span>", unsafe_allow_html=True)
    page = st.sidebar.radio("", ["Dashboard & Claims", "New Expense Claim", "Approvals Workflow", "Reports & Export"], label_visibility="collapsed")

    st.sidebar.markdown("<br>" * 2, unsafe_allow_html=True)
    if st.sidebar.button("Logout"):
        st.session_state.authenticated = False
        st.session_state.user_role = None
        st.session_state.username = None
        st.session_state.user_info = None
        st.rerun()
else:
    page = "Login"
    st.sidebar.markdown("<span style='color: #b0c4de; font-size: 13px;'>Please log in to access system modules.</span>", unsafe_allow_html=True)

is_admin_or_kapil = st.session_state.user_role in ["Admin", "Super Admin"] or (st.session_state.username and st.session_state.username.lower() == "kapil")

if not st.session_state.authenticated:
    col_logo, col_title = st.columns([2, 6])
    with col_logo:
        st.markdown(f"<img src='{PRISM_LOGO_URL}' style='max-width: 140px; margin-top: 10px;'>", unsafe_allow_html=True)
    with col_title:
        st.markdown("<h3 style='margin: 0; color: #1d2d3e;'>Petty Cash Management Portal</h3>", unsafe_allow_html=True)
    
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        with st.form("login_form"):
            st.markdown("### 🔐 Secure Sign In")
            user_input = st.text_input("Username")
            pass_input = st.text_input("Password", type="password")
            submit = st.form_submit_button("Login")
            
            if submit:
                res = supabase.table("users").select("*").eq("username", user_input.strip()).execute()
                if res.data and res.data[0]["password"] == pass_input.strip():
                    st.session_state.authenticated = True
                    st.session_state.username = res.data[0]["username"]
                    st.session_state.user_role = res.data[0]["role"]
                    st.session_state.user_info = res.data[0]
                    st.success("Login Successful!")
                    st.rerun()
                else:
                    st.error("Invalid Username or Password")
    st.stop()

user_data = st.session_state.user_info
if user_data and not user_data.get("email"):
    st.markdown("<div class='main-header'>🔒 PRISM Security Setup: Register Email & Update Password</div>", unsafe_allow_html=True)
    with st.form("setup_form"):
        st.warning(f"Welcome **{user_data['username']}**! First-time login requires setting up your official email and a strong new password.")
        new_email = st.text_input("Official Email Address:")
        new_pass = st.text_input("New Password:", type="password")
        confirm_pass = st.text_input("Confirm New Password:", type="password")
        setup_submit = st.form_submit_button("Save & Continue")
        
        if setup_submit:
            if not ("@" in new_email and "." in new_email):
                st.error("Please enter a valid email address.")
            elif new_pass != confirm_pass:
                st.error("Passwords do not match.")
            else:
                is_valid, msg = check_password_policy(new_pass)
                if not is_valid:
                    st.error(f"❌ Policy Error: {msg}")
                else:
                    supabase.table("users").update({
                        "email": new_email,
                        "password": new_pass
                    }).eq("id", user_data["id"]).execute()
                    
                    st.session_state.user_info["email"] = new_email
                    st.session_state.user_info["password"] = new_pass
                    st.success("✅ Profile successfully updated! Reloading...")
                    st.rerun()
    st.stop()

assigned_prism = user_data.get("assigned_prism_id", "N/A") if user_data else "N/A"
hotels_df = fetch_hotel_masters()

if page == "Dashboard & Claims":
    st.markdown("<div class='main-header'>📊 Dashboard & Claim Records</div>", unsafe_allow_html=True)
    df = fetch_records()
    
    if not df.empty:
        if not is_admin_or_kapil and assigned_prism:
            df = df[df['prism_id'] == assigned_prism]
            
        if not df.empty:
            with st.expander("🔍 Advanced Filters & Slicer Options", expanded=True):
                col_f1, col_f2, col_f3, col_f4 = st.columns(4)
                
                # 1. Region Filter (using property_region from hotel_master)
                with col_f1:
                    regions = ["All"]
                    if not hotels_df.empty and 'property_region' in hotels_df.columns:
                        regions += sorted([str(r) for r in hotels_df['property_region'].dropna().unique() if str(r).strip() != ""])
                    if len(regions) == 1 and 'region' in df.columns:
                        regions += sorted([str(r) for r in df['region'].dropna().unique() if str(r).strip() != ""])
                    selected_region = st.selectbox("1. Filter by Region", regions)

                # 2. Property / Hotel Name (with Short Name) Filter
                with col_f2:
                    hotel_options = ["All"]
                    filtered_hotels_df = hotels_df.copy()
                    if selected_region != "All" and not filtered_hotels_df.empty and 'property_region' in filtered_hotels_df.columns:
                        filtered_hotels_df = filtered_hotels_df[filtered_hotels_df['property_region'] == selected_region]
                    
                    if not filtered_hotels_df.empty and 'property_name' in filtered_hotels_df.columns:
                        for _, h_row in filtered_hotels_df.iterrows():
                            p_name = h_row.get('property_name', '')
                            s_name = h_row.get('short_name', '')
                            display_str = f"{p_name} ({s_name})" if s_name else p_name
                            if display_str and display_str not in hotel_options:
                                hotel_options.append(display_str)
                    
                    if len(hotel_options) == 1 and 'property_name' in df.columns:
                        sub_df = df if selected_region == "All" else df[df.get('region', '') == selected_region]
                        for p in sorted(sub_df['property_name'].dropna().unique()):
                            if str(p).strip() and str(p) not in hotel_options:
                                hotel_options.append(str(p))
                                
                    selected_property = st.selectbox("2. Hotel / Property Slicer", hotel_options)

                # 3. Date / Year Filter
                with col_f3:
                    df['year'] = pd.to_datetime(df['claim_date'], errors='coerce').dt.year
                    years = ["All"] + sorted([str(int(y)) for y in df['year'].dropna().unique() if pd.notna(y)], reverse=True)
                    selected_year = st.selectbox("3. Filter by Year", years)

                # 4. Vendor / Merchant Filter
                with col_f4:
                    merchants = ["All"] + sorted([str(m) for m in df['merchant'].dropna().unique() if str(m).strip() != ""])
                    selected_merchant = st.selectbox("4. Filter by Vendor / Merchant", merchants)

            filtered_df = df.copy()
            if selected_region != "All":
                if not hotels_df.empty and 'property_region' in hotels_df.columns and 'property_name' in hotels_df.columns:
                    matched_props = hotels_df[hotels_df['property_region'] == selected_region]['property_name'].tolist()
                    filtered_df = filtered_df[filtered_df['property_name'].isin(matched_props)]
                elif 'region' in filtered_df.columns:
                    filtered_df = filtered_df[filtered_df['region'] == selected_region]
                    
            if selected_property != "All":
                clean_prop_name = selected_property.split(" (")[0]
                filtered_df = filtered_df[filtered_df['property_name'] == clean_prop_name]
                
            if selected_year != "All":
                filtered_df = filtered_df[filtered_df['year'].astype(str) == selected_year]
            if selected_merchant != "All":
                filtered_df = filtered_df[filtered_df['merchant'] == selected_merchant]

            col1, col2, col3 = st.columns(3)
            col1.metric("Total Filtered Claims", len(filtered_df))
            col2.metric("Total Amount", f"{filtered_df['amount'].sum():,.2f}")
            col3.metric("Pending Approvals", len(filtered_df[filtered_df['status'].isin(['Pending', 'Submitted'])]))
            
            st.dataframe(filtered_df, use_container_width=True)
            
            # --- Visual Graphs Section ---
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("<div class='main-header'>📈 Petty Cash Visual Analytics & Graphs</div>", unsafe_allow_html=True)
            
            if not filtered_df.empty:
                filtered_df['parsed_date'] = pd.to_datetime(filtered_df['claim_date'], errors='coerce')
                filtered_df['month_year'] = filtered_df['parsed_date'].dt.strftime('%Y-%m')
                
                g_col1, g_col2 = st.columns(2)
                
                with g_col1:
                    st.markdown("##### 📅 Month-wise Petty Cash Amount")
                    monthly_df = filtered_df.groupby('month_year')['amount'].sum().reset_index().sort_values('month_year')
                    if not monthly_df.empty:
                        st.bar_chart(monthly_df.set_index('month_year'))
                    else:
                        st.info("No timeline data available for monthly chart.")

                with g_col2:
                    st.markdown("##### 🏢 Hotel-wise Petty Cash Amount")
                    hotel_chart_df = filtered_df.groupby('property_name')['amount'].sum().reset_index()
                    if not hotel_chart_df.empty:
                        st.bar_chart(hotel_chart_df.set_index('property_name'))
                    else:
                        st.info("No data available for hotel chart.")

                st.markdown("##### 🏷️ Vendor-wise Petty Cash Amount")
                vendor_chart_df = filtered_df.groupby('merchant')['amount'].sum().reset_index()
                if not vendor_chart_df.empty:
                    st.bar_chart(vendor_chart_df.set_index('merchant'))
                else:
                    st.info("No data available for vendor chart.")
            else:
                st.info("No data available in current filter selection to render graphs.")
            
            # --- Uploaded Bills & Receipts Database/Table Section ---
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("<div class='main-header'>📑 Uploaded Bills, Receipts & Invoices Archive</div>", unsafe_allow_html=True)
            try:
                bills_res = supabase.table("petty_cash").select("id, unique_id, receipt_number, merchant, amount, claim_date, receipt_url, submitted_by, property_name").not_.is_("receipt_url", "null").execute()
                if bills_res.data:
                    bills_df = pd.DataFrame(bills_res.data)
                    st.dataframe(bills_df, use_container_width=True)
                else:
                    st.info("No bills or receipts found in storage archive.")
            except Exception as b_err:
                st.info("No separate bills archive table configured or reachable.")
        else:
            st.info("No records found for your assigned property.")
    else:
        st.info("No petty cash claims found in database.")

elif page == "New Expense Claim":
    st.markdown("<div class='main-header'>📝 Submit New Claim with Auto-Validation & OCR Table</div>", unsafe_allow_html=True)
    
    assigned_prism_id = user_data.get("assigned_prism_id", "")
    property_name = ""
    property_short_name = "prop"
    
    if assigned_prism_id:
        try:
            h_res = supabase.table("hotel_master").select("*").eq("prism_id", assigned_prism_id).execute()
            if h_res.data:
                property_name = h_res.data[0].get("property_name", "")
                raw_short = h_res.data[0].get("short_name", assigned_prism_id.split('_')[-1])
                property_short_name = "".join(e for e in raw_short if e.isalnum()).lower()
        except Exception:
            property_short_name = assigned_prism_id.split('_')[-1].lower() if assigned_prism_id else "prop"

    with st.form("claim_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            st.markdown('<p class="fiori-label">Claim Date</p>', unsafe_allow_html=True)
            claim_date = st.date_input("Claim Date", datetime.today(), label_visibility="collapsed")
            
            st.markdown('<p class="fiori-label">Entry Date</p>', unsafe_allow_html=True)
            entry_date = st.date_input("Entry Date", datetime.today(), label_visibility="collapsed")
            
            st.markdown('<p class="fiori-label">Petty Cash Slip / Receipt Number <span class="fiori-required">*</span> <span style="font-weight: 400; color: #666; font-size: 11px;">(e.g. 1024)</span></p>', unsafe_allow_html=True)
            receipt_number = st.text_input("Petty Cash Slip / Receipt Number", label_visibility="collapsed")
            
            st.markdown('<p class="fiori-label">Category <span class="fiori-required">*</span></p>', unsafe_allow_html=True)
            category = st.selectbox("Category", ["Travel", "Office Supplies", "Maintenance", "Food & Beverage", "Utility", "Other"], label_visibility="collapsed")
            
        with col2:
            st.markdown('<p class="fiori-label">Amount</p>', unsafe_allow_html=True)
            amount = st.number_input("Amount", min_value=0.0, step=10.0, format="%.2f", label_visibility="collapsed")
            
            st.markdown('<p class="fiori-label">Merchant / Vendor Name <span class="fiori-required">*</span></p>', unsafe_allow_html=True)
            merchant = st.text_input("Merchant / Vendor Name", label_visibility="collapsed")
            
            st.markdown('<p class="fiori-label">Description / Reason <span class="fiori-required">*</span></p>', unsafe_allow_html=True)
            description = st.text_area("Description / Reason", label_visibility="collapsed")
            
        st.markdown("<hr style='margin: 15px 0; border-color: #eee;'>", unsafe_allow_html=True)
        st.markdown('<p class="fiori-label">📎 Bill / Receipt Attachments <span class="fiori-required">*</span> <span style="font-weight: 400; color: #666;">(Mandatory - Multiple Allowed)</span></p>', unsafe_allow_html=True)
        uploaded_files = st.file_uploader(
            "Upload receipts/bills (Images or PDFs)", 
            type=["png", "jpg", "jpeg", "pdf"], 
            accept_multiple_files=True,
            label_visibility="collapsed"
        )
        
        submitted = st.form_submit_button("Submit & Validate Claim")
        if submitted:
            if not uploaded_files:
                st.error("❌ Submission Failed: At least 1 Bill / Receipt attachment is required!")
                st.stop()
            if not receipt_number.strip():
                st.error("❌ Petty Cash Slip / Receipt Number is mandatory.")
                st.stop()
            if amount <= 0:
                st.error("❌ Please enter a valid Amount.")
                st.stop()
            if not merchant.strip() or not description.strip():
                st.error("❌ Merchant Name and Description are mandatory.")
                st.stop()
                
            clean_rec_check = receipt_number.strip()
            
            try:
                existing_check = supabase.table("petty_cash").select("id").eq("receipt_number", clean_rec_check).eq("prism_id", assigned_prism_id).execute()
                if existing_check.data:
                    st.error(f"❌ **Duplicate Error:** Receipt Number `{clean_rec_check}` has already been submitted for this property!")
                    st.stop()
            except Exception as db_err:
                st.error(f"❌ Database error during duplicate check: {str(db_err)}.")
                st.stop()

            extracted_receipt_rows = []
            amount_matched = False
            
            if OCR_AVAILABLE and uploaded_files:
                with st.spinner("🤖 Scanning receipt items & amounts via OCR..."):
                    try:
                        reader = load_ocr_reader()
                        for f_idx, file_obj in enumerate(uploaded_files):
                            file_bytes = file_obj.read()
                            file_obj.seek(0)
                            
                            ocr_results = reader.readtext(file_bytes, detail=0)
                            full_text_str = " ".join(ocr_results)
                            
                            found_numbers = re.findall(r'\d+(?:\.\d{1,2})?', full_text_str)
                            clean_numbers = [float(n) for n in found_numbers if float(n) > 0]
                            max_detected_amt = max(clean_numbers) if clean_numbers else 0.0
                            
                            extracted_receipt_rows.append({
                                "Receipt Index": f_idx + 1,
                                "File Name": file_obj.name,
                                "Merchant": merchant,
                                "Max Amount Found": max_detected_amt,
                                "Extracted Snippet": full_text_str[:100] + "..."
                            })
                            
                            for num in clean_numbers:
                                if abs(num - amount) < 1.0:
                                    amount_matched = True
                                    break
                    except Exception as e:
                        pass

            if extracted_receipt_rows:
                st.markdown("### 📋 Auto-Generated Receipt Verification Table")
                st.dataframe(pd.DataFrame(extracted_receipt_rows), use_container_width=True)
                
                if not amount_matched:
                    st.error(f"❌ **Validation Failed:** Entered amount `{amount}` does not match any numeric value found in the attached receipt scan!")
                    st.stop()
                else:
                    st.success("✅ **Validation Passed:** Amount verified against receipt items table.")

            try:
                uploaded_urls = []
                for idx, file_obj in enumerate(uploaded_files):
                    file_ext = file_obj.name.split(".")[-1]
                    clean_rec = re.sub(r'[^a-zA-Z0-9]', '', receipt_number)
                    file_name = f"{property_short_name}_inv_{clean_rec}_{idx+1}.{file_ext}"
                    file_bytes = file_obj.read()
                    storage_path = f"receipts/{file_name}"
                    
                    supabase.storage.from_("petty_cash_receipts").upload(
                        path=storage_path, 
                        file=file_bytes, 
                        file_options={"content-type": file_obj.type}
                    )
                    public_url = supabase.storage.from_("petty_cash_receipts").get_public_url(storage_path)
                    uploaded_urls.append(public_url)
                
                prism_clean = assigned_prism_id.replace('DE_', '') if assigned_prism_id else 'GENERAL'
                unique_id = f"Prism{prism_clean}-{int(datetime.now().timestamp())}"
                
                new_data = {
                    "created_at": datetime.now().isoformat(),
                    "submitted_by": st.session_state.username,
                    "claim_date": str(claim_date),
                    "entry_date": str(entry_date),
                    "receipt_number": receipt_number,
                    "category": category,
                    "amount": amount,
                    "currency": "",
                    "merchant": merchant,
                    "description": description,
                    "status": "Submitted",
                    "property_name": property_name,
                    "prism_id": assigned_prism_id,
                    "unique_id": unique_id,
                    "receipt_url": ", ".join(uploaded_urls)
                }
                supabase.table("petty_cash").insert(new_data).execute()
                st.success(f"✅ Claim Submitted Successfully! Unique ID: {unique_id}")
            except Exception as e:
                st.error(f"❌ Error submitting claim: {str(e)}")

elif page == "Approvals Workflow":
    st.markdown("<div class='main-header'>✅ Pending Approvals</div>", unsafe_allow_html=True)
    if st.session_state.user_role in ["Manager", "Admin", "Super Admin", "PPM", "GM"] or st.session_state.username.lower() == "kapil":
        df = fetch_records()
        if not df.empty:
            pending_df = df[df["status"].isin(["Pending", "Submitted"])]
            if not pending_df.empty:
                for idx, row in pending_df.iterrows():
                    amt_val = row.get('amount', 0)
                    cat_val = row.get('category', 'General')
                    date_val = row.get('claim_date', '')
                    row_id = row['id']
                    
                    with st.expander(f"Claim #{row_id} - Slip/Receipt: {row.get('receipt_number', 'N/A')} - Amount: {amt_val} ({row['submitted_by']})"):
                        st.write(f"**Unique ID:** {row.get('unique_id', 'N/A')}")
                        st.write(f"**Property Name:** {row.get('property_name', 'N/A')} ({row.get('prism_id', 'N/A')})")
                        st.write(f"**Petty Cash Slip / Receipt Number:** {row.get('receipt_number', 'N/A')}")
                        st.write(f"**Category:** {cat_val}")
                        st.write(f"**Merchant:** {row.get('merchant', 'N/A')} | **Date:** {date_val}")
                        st.write(f"**Description:** {row.get('description', '')}")
                        if row.get('receipt_url'):
                            st.markdown(f"**Receipt Link:** [View Receipt]({row.get('receipt_url')})")
                        
                        col1, col2 = st.columns(2)
                        if col1.button(f"Approve #{row_id}", key=f"app_{row_id}"):
                            supabase.table("petty_cash").update({"status": "Approved"}).eq("id", row_id).execute()
                            st.success(f"Claim #{row_id} Approved!")
                            st.rerun()
                        if col2.button(f"Reject #{row_id}", key=f"rej_{row_id}"):
                            supabase.table("petty_cash").update({"status": "Rejected"}).eq("id", row_id).execute()
                            st.error(f"Claim #{row_id} Rejected!")
                            st.rerun()
            else:
                st.info("No pending approvals.")
        else:
            st.info("No records found.")
    else:
        st.warning("You do not have approval permissions.")

elif page == "Reports & Export":
    st.markdown("<div class='main-header'>📥 Export Reports & Uploaded Bills Archive</div>", unsafe_allow_html=True)
    df = fetch_records()
    if not df.empty:
        if not is_admin_or_kapil and assigned_prism:
            df = df[df['prism_id'] == assigned_prism]
            
        st.markdown("### 📊 Claims Report Table")
        st.dataframe(df, use_container_width=True)
        
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='PrismPettyCashReport')
            
        st.download_button(
            label="📊 Download Excel Report",
            data=buffer.getvalue(),
            file_name=f"prism_petty_cash_report_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.ms-excel"
        )
        
        st.markdown("<br><hr>", unsafe_allow_html=True)
        st.markdown("### 📑 Uploaded Bills, Receipts & Invoices Table")
        try:
            bills_archive = supabase.table("petty_cash").select("unique_id, claim_date, merchant, amount, receipt_url, submitted_by, property_name").not_.is_("receipt_url", "null").execute()
            if bills_archive.data:
                b_df = pd.DataFrame(bills_archive.data)
                st.dataframe(b_df, use_container_width=True)
            else:
                st.info("No bills archive records found.")
        except Exception:
            st.info("Bills archive table view not available.")
    else:
        st.info("No data available to export.")
