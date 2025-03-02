import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import bcrypt

# ✅ Load Google Sheets API Credentials
creds_dict = dict(st.secrets["gcp_service_account"])  # Create a mutable copy
creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")  # Fix private key formatting

# ✅ Authenticate with Google Sheets
try:
    creds = Credentials.from_service_account_info(
        creds_dict,
        scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    )
    client = gspread.authorize(creds)
except Exception as e:
    st.error(f"❌ Google Sheets Authentication Failed: {e}")
    st.stop()

# ✅ Google Sheets IDs & Names
AUTH_SHEET_ID = "1RCIZrxv21hY-xtzDRuC0L50KLCLpZuYWKKatuJoVCT8"
AUTH_SHEET_NAME = "Sheet1"

COLLECTION_SHEET_ID = "1l0RVkf3U0XvWJre74qHy3Nv5n-4TKTCSV5yNVW4Sdbw"
COLLECTION_SHEET_NAME = "Form responses 1"

EXPENSE_SHEET_ID = "1bEquqG2T-obXkw5lWwukx1v_lFnLrFdAf6GlWHZ9J18"
EXPENSE_SHEET_NAME = "Form responses 1"

# ✅ Function to Load Google Sheets Data
def load_sheet_data(sheet_id, sheet_name):
    try:
        sheet = client.open_by_key(sheet_id).worksheet(sheet_name)
        data = sheet.get_all_records()
        df = pd.DataFrame(data)

        if 'Collection Date' in df.columns:
            df['Collection Date'] = pd.to_datetime(df['Collection Date'], errors='coerce')
            df['Month-Year'] = df['Collection Date'].dt.strftime('%Y-%m')

        return df
    except Exception as e:
        st.error(f"❌ Failed to load data from {sheet_name}: {e}")
        return pd.DataFrame()  # Return empty DataFrame to prevent crashes

# ✅ Load Authentication Data
auth_df = load_sheet_data(AUTH_SHEET_ID, AUTH_SHEET_NAME)

# ✅ Function to Verify Password
def verify_password(stored_hash, entered_password):
    return bcrypt.checkpw(entered_password.encode(), stored_hash.encode())

# ✅ Initialize Session State for Authentication
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
    st.session_state.user_role = None
    st.session_state.username = None
    st.session_state.user_name = None

# --- 🔒 LOGIN PAGE ---
if not st.session_state.authenticated:
    st.title("🔒 Secure Login")
    username = st.text_input("👤 Username")
    password = st.text_input("🔑 Password", type="password")
    login_button = st.button("Login")

    if login_button:
        user_data = auth_df[auth_df["Username"] == username]

        if not user_data.empty:
            stored_hash = user_data.iloc[0]["Password"]
            role = user_data.iloc[0]["Role"]
            name = user_data.iloc[0]["Name"]

            if verify_password(stored_hash, password):
                st.session_state.authenticated = True
                st.session_state.user_role = role
                st.session_state.username = username
                st.session_state.user_name = name
                st.experimental_set_query_params(logged_in="true")

                st.success(f"✅ Welcome, {name}!")
                st.rerun()
            else:
                st.error("❌ Invalid Credentials")
        else:
            st.error("❌ User not found")

# --- ✅ LOGGED-IN USER SEES DASHBOARD ---
else:
    if st.sidebar.button("🚪 Logout"):
        st.session_state.authenticated = False
        st.session_state.user_role = None
        st.session_state.username = None
        st.session_state.user_name = None
        st.experimental_set_query_params(logged_in="false")
        st.rerun()

    st.sidebar.write(f"👤 **Welcome, {st.session_state.user_name}!**")

    # ✅ Load Google Sheets Data
    df = load_sheet_data(COLLECTION_SHEET_ID, COLLECTION_SHEET_NAME)
    expense_df = load_sheet_data(EXPENSE_SHEET_ID, EXPENSE_SHEET_NAME)

    # ✅ Debugging: Print column names
    st.write("✅ Columns in df:", df.columns.tolist())  
    st.write("✅ Columns in expense_df:", expense_df.columns.tolist())

    # --- 📊 DASHBOARD UI ---
    st.sidebar.header("📂 Navigation")
    page = st.sidebar.radio("Go to:", ["Dashboard", "Monthly Summary", "Grouped Data", "Expenses", "Raw Data"])

    if page == "Dashboard":
        st.title("📊 Orga Yatra Dashboard")

        if not df.empty and not expense_df.empty and 'Month-Year' in df.columns:
            total_collection = df['Amount'].sum()
            total_expense = expense_df['Amount Used'].sum()
            remaining_amount = total_collection - total_expense

            last_month = df['Month-Year'].max()
            last_month_collection = df[df['Month-Year'] == last_month]['Amount'].sum()
            last_month_expense = expense_df[expense_df['Month-Year'] == last_month]['Amount Used'].sum()

            col1, col2, col3 = st.columns(3)
            col1.metric(label="💰 Total Collection", value=f"₹{total_collection:,.2f}")
            col2.metric(label="📉 Total Expenses", value=f"₹{total_expense:,.2f}")
            col3.metric(label="💵 Remaining Balance", value=f"₹{remaining_amount:,.2f}")

            st.markdown("---")
            formatted_last_month = pd.to_datetime(last_month).strftime("%b %Y")
            st.subheader("📅 " + formatted_last_month + " Overview")

            col4, col5 = st.columns(2)
            col4.metric(label="📈 " + formatted_last_month + " Collection", value=f"₹{last_month_collection:,.2f}")
            col5.metric(label="📉 " + formatted_last_month + " Expenses", value=f"₹{last_month_expense:,.2f}")

            st.markdown("---")
            st.write("### 📈 Collection & Distance Trend")
            st.line_chart(df.set_index("Collection Date")[["Amount", "Distance"]])

            st.write("### 🔍 Recent Collection Data:")
            st.dataframe(df.sort_values(by="Collection Date", ascending=False).head(10))
        else:
            st.warning("⚠ No data available or 'Month-Year' column missing!")

    elif page == "Monthly Summary":
        st.title("📊 Monthly Collection vs Expense")
        if not df.empty and not expense_df.empty and 'Month-Year' in df.columns:
            collection_summary = df.groupby('Month-Year', as_index=False)['Amount'].sum()
            expense_summary = expense_df.groupby('Month-Year', as_index=False)['Amount Used'].sum()
            summary = collection_summary.merge(expense_summary, on='Month-Year', how='outer').fillna(0)
            summary.columns = ['Month-Year', 'Total Collection', 'Total Expense']
            st.dataframe(summary)
            st.bar_chart(summary.set_index("Month-Year"))
        else:
            st.warning("⚠ No data available!")

    elif page == "Expenses":
        st.title("💸 Expense Details")
        if not expense_df.empty:
            st.dataframe(expense_df.sort_values(by="Date", ascending=False))
        else:
            st.warning("⚠ No expense data available!")

    elif page == "Raw Data":
        st.title("📋 Full Collection Data")
        if not df.empty:
            st.dataframe(df.sort_values(by="Collection Date", ascending=False))
        else:
            st.warning("⚠ No collection data available!")
