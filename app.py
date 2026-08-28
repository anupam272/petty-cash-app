import streamlit as st
import pandas as pd
from datetime import datetime
from supabase import create_client, Client
import json
import re
import io

# OCR Import check
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

st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .main-header {font-size: 26px; font-weight: bold; color: #111111; margin-bottom: 20px; display: flex; align-items: center; gap: 10px;}
    .stButton>button {width: 100%; border-radius: 6px; font-weight: 600; background-color: #111111; color: white;}
    .stButton>button:hover {background-color: #333333; color: white;}
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

PRISM_LOGO_URL = "https://www.prismlife.com/img/logo.webp"

if not st.session_state.authenticated:
    col_logo, col_title = st.columns([2, 6])
    with col_logo:
        st.markdown(f"<img src='{PRISM_LOGO_URL}' style='max-width: 140px; margin-top: 10px;'>", unsafe_allow_html=True)
    with col_title:
        st.markdown("<h3 style='margin: 0; color: #11;'>Petty Cash Management Portal</h3>", unsafe_allow_html=True)
    
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

st.sidebar.markdown(f"<img src='{PRISM_LOGO_URL}' style='max-width: 110px; margin-bottom: 10px;'>", unsafe_allow_html=True)
st.sidebar.caption(f"User: **{st.session_state.username}**")
st.sidebar.caption(f"Role: **{st.session_state.user_role}**")
assigned_prism = user_data.get("assigned_prism_id", "N/A") if user_data else "N/A"
st.sidebar.caption(f"Prism ID: **{assigned_prism}**")
st.sidebar.markdown("---")

page = st.sidebar.radio("Navigation", ["Dashboard & Claims", "New Expense Claim", "Approvals Workflow", "Reports & Export"])

if st.sidebar.button("Logout"):
    st.session_state.authenticated = False
    st.session_state.user_role = None
    st.session_state.username = None
    st.session_state.user_info = None
    st.rerun()

if page == "Dashboard & Claims":
    st.markdown("<div class='main-header'>📊 Dashboard & Claim Records</div>", unsafe_allow_html=True)
    df = fetch_records()
    if not df.empty:
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Claims", len(df))
        amt_col = 'invoice_amount' if 'invoice_amount' in df.columns else 'amount'
        col2.metric("Total Amount", f"₹ {df[amt_col].sum():,.2f}")
        col3.metric("Pending Approvals", len(df[df['status'].isin(['Pending', 'Submitted'])]))
        
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No petty cash claims found.")

elif page == "New Expense Claim":
    st.markdown("<div class='main-header'>📝 Submit New Claim with Duplicate & OCR Validation</div>", unsafe_allow_html=True)
    
    assigned_prism_id = user_data.get("assigned_prism_id", "")
    assigned_region = user_data.get("assigned_region", "")
    hotel_name = ""
    
    currency = "₹"
    if assigned_region and assigned_region.lower() == "europe":
        currency = "EUR"
    
    if assigned_prism_id:
        try:
            h_res = supabase.table("hotel_master").select("property_name", "currency").eq("prism_id", assigned_prism_id).execute()
            if h_res.data:
                hotel_name = h_res.data[0].get("property_name", "")
                db_currency = h_res.data[0].get("currency", "")
                if db_currency:
                    currency = db_currency
        except Exception:
            pass

    with st.form("claim_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            claim_date = st.date_input("Entry Date", datetime.today())
            category = st.selectbox("Expense Type*", ["Travel", "Office Supplies", "Maintenance", "Food & Beverage", "Utility", "Other"])
            subtype = st.text_input("Subtype (e.g., Taxi, Stationery)")
            invoice_amount = st.number_input(f"Invoice Amount ({currency})", min_value=0.0, step=10.0, format="%.2f")
        with col2:
            vendor_name = st.text_input("Vendor Name*")
            receipt_no = st.text_input("Receipt / Bill No.*")
            description = st.text_area("Description / Reason")
            remarks = st.text_input("Remarks (Optional)")
            
        st.markdown("---")
        st.markdown("**📎 Bill / Receipt Attachments (Mandatory - Multiple Allowed)**")
        uploaded_files = st.file_uploader(
            "Upload receipts/bills (Images or PDFs)", 
            type=["png", "jpg", "jpeg", "pdf"], 
            accept_multiple_files=True
        )
        
        submitted = st.form_submit_button("Submit & Validate Claim")
        if submitted:
            if not uploaded_files:
                st.error("❌ Submission Failed: At least 1 Bill / Receipt attachment is required!")
                st.stop()
            if invoice_amount <= 0:
                st.error("❌ Please enter a valid Invoice Amount.")
                st.stop()
            if not vendor_name.strip() or not receipt_no.strip():
                st.error("❌ Vendor Name and Receipt No. are mandatory.")
                st.stop()
                
            # 1. DUPLICATE RECEIPT CHECK IN DATABASE
            try:
                dup_check = supabase.table("petty_cash").select("id, receipt_no, vendor_name").eq("oyo_id", assigned_prism_id).eq("receipt_no", receipt_no.strip()).execute()
                if dup_check.data:
                    st.error(f"❌ **Duplicate Blocked:** Receipt Number `{receipt_no}` has already been submitted for this property! You cannot reuse the same invoice/receipt.")
                    st.stop()
            except Exception as d_err:
                pass

            extracted_receipt_rows = []
            amount_matched = False
            
            # 2. OCR VERIFICATION & ITEMIZATION TABLE
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
                                "Vendor": vendor_name,
                                "Max Amount Found": max_detected_amt,
                                "Extracted Snippet": full_text_str[:100] + "..."
                            })
                            
                            for num in clean_numbers:
                                if abs(num - invoice_amount) < 1.0:
                                    amount_matched = True
                                    break
                    except Exception as e:
                        pass

            if extracted_receipt_rows:
                st.markdown("### 📋 Auto-Generated Receipt Verification Table")
                st.dataframe(pd.DataFrame(extracted_receipt_rows), use_container_width=True)
                
                if not amount_matched:
                    st.error(f"❌ **Validation Failed:** Entered amount `{invoice_amount}` does not match any numeric value found in the attached receipt scan!")
                    st.stop()
                else:
                    st.success("✅ **Validation Passed:** Amount verified against receipt items table.")

            # 3. UPLOAD & SAVE CLAIM
            try:
                uploaded_urls = []
                for idx, file_obj in enumerate(uploaded_files):
                    file_ext = file_obj.name.split(".")[-1]
                    unique_suffix = int(datetime.now().timestamp() * 1000)
                    file_name = f"{assigned_prism_id}_{claim_date}_{receipt_no}_{idx+1}_{unique_suffix}.{file_ext}"
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
                    "unique_id": unique_id,
                    "created_at": datetime.now().isoformat(),
                    "submitted_by": st.session_state.username,
                    "entry_date": str(claim_date),
                    "oyo_id": assigned_prism_id,
                    "property_name": hotel_name,
                    "property_region": assigned_region,
                    "currency": currency,
                    "exp_type": category,
                    "subtype": subtype,
                    "invoice_amount": invoice_amount,
                    "amount": invoice_amount,
                    "vendor_name": vendor_name,
                    "receipt_no": receipt_no,
                    "description": description,
                    "remarks": remarks,
                    "status": "Submitted",
                    "receipt_url": json.dumps(uploaded_urls)
                }
                supabase.table("petty_cash").insert(new_data).execute()
                st.success(f"✅ Claim Submitted Successfully! Unique ID: {unique_id}")
            except Exception as e:
                st.error(f"❌ Error submitting claim: {str(e)}")

elif page == "Approvals Workflow":
    st.markdown("<div class='main-header'>✅ Pending Approvals</div>", unsafe_allow_html=True)
    if st.session_state.user_role in ["Manager", "Admin", "PPM", "GM"]:
        df = fetch_records()
        if not df.empty:
            pending_df = df[df["status"].isin(["Pending", "Submitted"])]
            if not pending_df.empty:
                for idx, row in pending_df.iterrows():
                    amt_val = row.get('invoice_amount', row.get('amount', 0))
                    cat_val = row.get('exp_type', row.get('category', 'General'))
                    date_val = row.get('entry_date', row.get('claim_date', ''))
                    row_id = row['id']
                    
                    with st.expander(f"Claim #{row_id} - {row.get('currency', '₹')} {amt_val} ({row['submitted_by']})"):
                        st.write(f"**Unique ID:** {row.get('unique_id', 'N/A')}")
                        st.write(f"**Category:** {cat_val} / {row.get('subtype', '')}")
                        st.write(f"**Vendor:** {row.get('vendor_name', 'N/A')} | **Receipt No:** {row.get('receipt_no', 'N/A')}")
                        st.write(f"**Reason:** {row.get('description', '')}")
                        st.write(f"**Date:** {date_val}")
                        
                        receipt_data = row.get('receipt_url')
                        if receipt_data:
                            try:
                                urls = json.loads(receipt_data) if isinstance(receipt_data, str) else receipt_data
                                if isinstance(urls, list):
                                    st.markdown("**Attached Receipts:**")
                                    for u_idx, u_link in enumerate(urls):
                                        st.markdown(f"- [View Attachment {u_idx+1}]({u_link})")
                                elif isinstance(urls, str):
                                    st.markdown(f"- [View Attachment]({urls})")
                            except Exception:
                                st.markdown(f"- [View Attachment]({receipt_data})")
                        
                        col1, col2 = st.columns(2)
                        if col1.button(f"Approve #{row_id}", key=f"app_{row_id}"):
                            supabase.table("petty_cash").update({"status": "Approved", "approved_by": st.session_state.username}).eq("id", row_id).execute()
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
    st.markdown("<div class='main-header'>📥 Export Reports</div>", unsafe_allow_html=True)
    df = fetch_records()
    if not df.empty:
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
    else:
        st.info("No data available to export.")
