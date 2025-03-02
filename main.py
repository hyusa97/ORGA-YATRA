import streamlit as st
import pandas as pd
import bcrypt
from google.oauth2.service_account import Credentials

# Streamlit App Configuration
st.set_page_config(page_title="Google Sheets Dashboard", layout="wide")

# Authentication Google Sheets Details
AUTH_SHEET_ID = "1RCIZrxv21hY-xtzDRuC0L50KLCLpZuYWKKatuJoVCT8"
AUTH_SHEET_NAME = "Sheet1"
AUTH_CSV_URL = f"https://docs.google.com/spreadsheets/d/{AUTH_SHEET_ID}/gviz/tq?tqx=out:csv&sheet={AUTH_SHEET_NAME}"


# Load credentials from Streamlit Secrets (create a copy)
creds_dict = dict(st.secrets["gcp_service_account"])  # ✅ Create a mutable copy

# Fix private key formatting
creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")

# ✅ Fix: Ensure correct Google API scopes
try:
    creds = Credentials.from_service_account_info(
        creds_dict, 
        scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    )
    client = gspread.authorize(creds)
    auth_df = client.open_by_key(AUTH_SHEET_ID).worksheet(AUTH_SHEET_NAME)
except Exception as e:
    st.error(f"❌ Failed to connect to Google Sheets: {e}")
    st.stop()



# Load authentication data
#def load_auth_data():
#    return pd.read_csv(AUTH_CSV_URL)

#auth_df = load_auth_data()

# Function to Verify Password
def verify_password(stored_hash, entered_password):
    return bcrypt.checkpw(entered_password.encode(), stored_hash.encode())

# Initialize Session State for Authentication
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
    st.session_state.user_role = None
    st.session_state.username = None
    st.session_state.user_name = None

# --- LOGIN PAGE ---
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

# --- LOGGED-IN USER SEES DASHBOARD ---
else:
    if st.sidebar.button("🚪 Logout"):
        st.session_state.authenticated = False
        st.session_state.user_role = None
        st.session_state.username = None
        st.session_state.user_name = None
        st.experimental_set_query_params(logged_in="false")
        st.rerun()

    st.sidebar.write(f"👤 **Welcome, {st.session_state.user_name}!**")

    # --- DATA LOADING ---
    COLLECTION_SHEET_ID = "1l0RVkf3U0XvWJre74qHy3Nv5n-4TKTCSV5yNVW4Sdbw"
    COLLECTION_SHEET_NAME = "Form%20responses%201"
    COLLECTION_CSV_URL = f"https://docs.google.com/spreadsheets/d/{COLLECTION_SHEET_ID}/gviz/tq?tqx=out:csv&sheet={COLLECTION_SHEET_NAME}"

    EXPENSE_SHEET_ID = "1bEquqG2T-obXkw5lWwukx1v_lFnLrFdAf6GlWHZ9J18"
    EXPENSE_SHEET_NAME = "Form%20responses%201"
    EXPENSE_CSV_URL = f"https://docs.google.com/spreadsheets/d/{EXPENSE_SHEET_ID}/gviz/tq?tqx=out:csv&sheet={EXPENSE_SHEET_NAME}"

    def load_data(url):
        df = pd.read_csv(url, dayfirst=True, dtype={"Vehicle No": str})  # Ensure Vehicle No remains a string
        df['Collection Date'] = pd.to_datetime(df['Collection Date'], dayfirst=True, errors='coerce').dt.date
        df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce')
        df['Meter Reading'] = pd.to_numeric(df['Meter Reading'], errors='coerce')
        df['Distance'] = df['Meter Reading'].diff().fillna(0)
        df['Month-Year'] = pd.to_datetime(df['Collection Date']).dt.strftime('%Y-%m')
        return df[['Collection Date', 'Vehicle No', 'Amount', 'Meter Reading', 'Name', 'Distance', 'Month-Year']]

    def load_expense_data(url):
        df = pd.read_csv(url, dayfirst=True, dtype={"Vehicle No": str})  # Ensure Vehicle No remains a string
        df['Date'] = pd.to_datetime(df['Date'], dayfirst=True, errors='coerce').dt.date
        df['Amount Used'] = pd.to_numeric(df['Amount Used'], errors='coerce')
        df['Month-Year'] = pd.to_datetime(df['Date']).dt.strftime('%Y-%m')
        return df[['Date', 'Vehicle No', 'Reason of Expense', 'Amount Used', 'Any Bill', 'Month-Year']]

    df = load_data(COLLECTION_CSV_URL)
    expense_df = load_expense_data(EXPENSE_CSV_URL)

    # --- DASHBOARD UI ---
    st.sidebar.header("📂 Navigation")
    page = st.sidebar.radio("Go to:", ["Dashboard", "Monthly Summary", "Grouped Data", "Expenses", "Raw Data"])

    if page == "Dashboard":
        st.title("📊 Orga Yatra Dashboard")
        
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
        st.subheader("📅 "+formatted_last_month+"   Overview")

        col4, col5 = st.columns(2)
        col4.metric(label="📈 "+formatted_last_month+"  Collection", value=f"₹{last_month_collection:,.2f}")
        col5.metric(label="📉"+formatted_last_month+" Expenses", value=f"₹{last_month_expense:,.2f}")

        st.markdown("---")
        st.write("### 📈 Collection & Distance Trend")
        st.line_chart(df.set_index("Collection Date")[["Amount", "Distance"]])

        st.write("### 🔍 Recent Collection Data:")
        st.dataframe(df.sort_values(by="Collection Date", ascending=False).head(10))

    elif page == "Monthly Summary":
        st.title("📊 Monthly Collection vs Expense")
        collection_summary = df.groupby('Month-Year', as_index=False)['Amount'].sum()
        expense_summary = expense_df.groupby('Month-Year', as_index=False)['Amount Used'].sum()

        summary = collection_summary.merge(expense_summary, on='Month-Year', how='outer').fillna(0)
        summary.columns = ['Month-Year', 'Total Collection', 'Total Expense']

        st.dataframe(summary)
        st.bar_chart(summary.set_index("Month-Year"))

    elif page == "Grouped Data":
        st.title("🔍 Grouped Collection Data")
        group_by = st.sidebar.radio("🔄 Group Data By:", ["Name", "Vehicle No"])
        selected_month = st.sidebar.selectbox("📅 Select Month-Year:", sorted(df['Month-Year'].unique(), reverse=True))
        df_filtered = df[df['Month-Year'] == selected_month]

        if group_by == "Name":
            grouped_df = df_filtered.groupby('Name', as_index=False)['Amount'].sum()
        else:
            grouped_df = df_filtered.groupby('Vehicle No', as_index=False)['Amount'].sum()

        st.dataframe(grouped_df)
        st.bar_chart(grouped_df.set_index(group_by)["Amount"])

    elif page == "Expenses":
        st.title("💸 Expense Details")
        st.dataframe(expense_df.sort_values(by="Date", ascending=False))

    elif page == "Raw Data":
        st.title("📋 Full Collection Data")
        st.dataframe(df.sort_values(by="Collection Date", ascending=False))
