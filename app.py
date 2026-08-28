
import streamlit as st
import pandas as pd
from datetime import datetime
from supabase import create_client, Client
import io

# 1. Database Connection (Secrets)
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

# 2. App Page Config
st.set_page_config(page_title="Petty Cash Mgt", page_icon="💰", layout="wide")

# Custom Styling
st.markdown("""
    <style>
    .main-header {font-size: 26px; font-weight: bold; color: #1E3A8A; margin-bottom: 20px;}
    .stButton>button {width: 100%; border-radius: 5px;}
    </style>
""", unsafe_allow_html=True)

# 3. Session State Initialization
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "user_role" not in st.session_state:
    st.session_state.user_role = None
if "username" not in st.session_state:
    st.session_state.username = None

# Helper Functions
def fetch_records():
    res = supabase.table("petty_cash").select("*").order("id", desc=True).execute()
    return pd.DataFrame(res.data) if res.data else pd.DataFrame()

# 4. Authentication Logic
if not st.session_state.authenticated:
    st.markdown("<div class='main-header'>🔐 Prism Petty Cash Management - Login</div>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        with st.form("login_form"):
            user_input = st.text_input("Username")
            pass_input = st.text_input("Password", type="password")
            submit = st.form_submit_button("Login")
            
            if submit:
                # Query database for credentials
                res = supabase.table("users").select("*").eq("username", user_input.strip()).execute()
                if res.data and res.data[0]["password"] == pass_input.strip():
                    st.session_state.authenticated = True
                    st.session_state.username = res.data[0]["username"]
                    st.session_state.user_role = res.data[0]["role"]
                    st.success("Login Successful!")
                    st.rerun()
                else:
                    st.error("Invalid Username or Password")
    st.stop()

# 5. Sidebar Menu
st.sidebar.title(f"👤 Welcome, {st.session_state.username}")
st.sidebar.caption(f"Role: **{st.session_state.user_role}**")
page = st.sidebar.radio("Navigation", ["Dashboard & Claims", "New Expense Claim", "Approvals Workflow", "Reports & Export"])

if st.sidebar.button("Logout"):
    st.session_state.authenticated = False
    st.rerun()

# 6. Page Routing
if page == "Dashboard & Claims":
    st.markdown("<div class='main-header'>📊 Dashboard & Claim Records</div>", unsafe_allow_html=True)
    df = fetch_records()
    if not df.empty:
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Claims", len(df))
        col2.metric("Total Amount", f"₹ {df['amount'].sum():,.2f}")
        col3.metric("Pending Approvals", len(df[df['status'] == 'Pending']))
        
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No petty cash claims found.")

elif page == "New Expense Claim":
    st.markdown("<div class='main-header'>📝 Submit New Petty Cash Claim</div>", unsafe_allow_html=True)
    with st.form("claim_form"):
        col1, col2 = st.columns(2)
        with col1:
            claim_date = st.date_input("Date", datetime.today())
            category = st.selectbox("Category", ["Office Supplies", "Travel & Fuel", "Food & Tea", "Maintenance", "Others"])
            amount = st.number_input("Amount (₹)", min_value=1.0, step=10.0)
        with col2:
            description = st.text_area("Description / Reason")
            merchant = st.text_input("Merchant / Paid To")
            
        submitted = st.form_submit_button("Submit Claim")
        if submitted:
            new_data = {
                "created_at": datetime.now().isoformat(),
                "submitted_by": st.session_state.username,
                "claim_date": str(claim_date),
                "category": category,
                "amount": amount,
                "description": description,
                "merchant": merchant,
                "status": "Pending"
            }
            supabase.table("petty_cash").insert(new_data).execute()
            st.success("Claim Submitted Successfully!")

elif page == "Approvals Workflow":
    st.markdown("<div class='main-header'>✅ Pending Approvals</div>", unsafe_allow_html=True)
    if st.session_state.user_role in ["Manager", "Admin", "PPM", "GM"]:
        df = fetch_records()
        if not df.empty:
            pending_df = df[df["status"] == "Pending"]
            if not pending_df.empty:
                for idx, row in pending_df.iterrows():
                    with st.expander(f"Claim #{row['id']} - ₹{row['amount']} ({row['submitted_by']})"):
                        st.write(f"**Category:** {row['category']}")
                        st.write(f"**Reason:** {row['description']}")
                        st.write(f"**Date:** {row['claim_date']}")
                        
                        col1, col2 = st.columns(2)
                        if col1.button(f"Approve #{row['id']}", key=f"app_{row['id']}"):
                            supabase.table("petty_cash").update({"status": "Approved"}).eq("id", row['id']).execute()
                            st.success(f"Claim #{row['id']} Approved!")
                            st.rerun()
                        if col2.button(f"Reject #{row['id']}", key=f"rej_{row['id']}"):
                            supabase.table("petty_cash").update({"status": "Rejected"}).eq("id", row['id']).execute()
                            st.error(f"Claim #{row['id']} Rejected!")
                            st.rerun()
            else:
                st.info("No pending approvals.")
    else:
        st.warning("You do not have approval permissions.")

elif page == "Reports & Export":
    st.markdown("<div class='main-header'>📥 Export Reports</div>", unsafe_allow_html=True)
    df = fetch_records()
    if not df.empty:
        st.dataframe(df)
        
        # Excel Export Buffer
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='PettyCashReport')
            
        st.download_button(
            label="📊 Download Excel Report",
            data=buffer.getvalue(),
            file_name=f"petty_cash_report_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.ms-excel"
        )
