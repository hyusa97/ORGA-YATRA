import streamlit as st
import pandas as pd
import numpy as np
import time
import bcrypt
import matplotlib.pyplot as plt
import gspread
from google.oauth2.service_account import Credentials

# Streamlit App Configuration
st.set_page_config(page_title="Google Sheets Dashboard", layout="wide")


# Load Google Sheet IDs securely
AUTH_SHEET_ID = st.secrets["sheets"]["AUTH_SHEET_ID"]
COLLECTION_SHEET_ID = st.secrets["sheets"]["COLLECTION_SHEET_ID"]
EXPENSE_SHEET_ID = st.secrets["sheets"]["EXPENSE_SHEET_ID"]
INVESTMENT_SHEET_ID = st.secrets["sheets"]["INVESTMENT_SHEET_ID"]


# Authentication Google Sheets Details

AUTH_SHEET_NAME = "Sheet1"


# --- DATA LOADING ---
COLLECTION_SHEET_NAME = "collection"
COLLECTION_CSV_URL = f"https://docs.google.com/spreadsheets/d/{COLLECTION_SHEET_ID}/gviz/tq?tqx=out:csv&sheet={COLLECTION_SHEET_NAME}"

# --- EXPENSE DATA ---

EXPENSE_SHEET_NAME = "expense"
EXPENSE_CSV_URL = f"https://docs.google.com/spreadsheets/d/{EXPENSE_SHEET_ID}/gviz/tq?tqx=out:csv&sheet={EXPENSE_SHEET_NAME}"

# --- INVESTMENT DATA ---

INVESTMENT_SHEET_NAME = "Investment_Details"
INVESTMENT_CSV_URL = f"https://docs.google.com/spreadsheets/d/{INVESTMENT_SHEET_ID}/gviz/tq?tqx=out:csv&sheet={INVESTMENT_SHEET_NAME}"

# ✅ Load credentials from Streamlit Secrets (Create a Copy)
creds_dict = dict(st.secrets["gcp_service_account"])  # Create a mutable copy

# ✅ Fix private key formatting
creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")

# ✅ Function to Connect to Google Sheets (with Caching)
@st.cache_data(ttl=300)  # Cache for 5 minutes
def connect_to_sheets():
    try:
        creds = Credentials.from_service_account_info(
            creds_dict, 
            scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        )
        client = gspread.authorize(creds)
        
        # Open sheets once and reuse them
        AUTH_sheet = client.open_by_key(st.secrets["sheets"]["AUTH_SHEET_ID"]).worksheet(AUTH_SHEET_NAME)
        COLLECTION_sheet = client.open_by_key(st.secrets["sheets"]["COLLECTION_SHEET_ID"]).worksheet(COLLECTION_SHEET_NAME)
        EXPENSE_sheet = client.open_by_key(st.secrets["sheets"]["EXPENSE_SHEET_ID"]).worksheet(EXPENSE_SHEET_NAME)
        INVESTMENT_sheet = client.open_by_key(st.secrets["sheets"]["INVESTMENT_SHEET_ID"]).worksheet(INVESTMENT_SHEET_NAME)
        
        return AUTH_sheet, COLLECTION_sheet, EXPENSE_sheet, INVESTMENT_sheet

    except Exception as e:
        st.error(f"❌ Failed to connect to Google Sheets: {e}")
        st.stop()

# ✅ Get cached sheets
AUTH_sheet, COLLECTION_sheet, EXPENSE_sheet, INVESTMENT_sheet = connect_to_sheets()

# Function to load authentication data securely
@st.cache_data(ttl=300)  # Cache for 5 minutes
def load_auth_data():
    data = AUTH_sheet.get_all_records()
    df = pd.DataFrame(data)
    return df

# Load authentication data
auth_df = load_auth_data()

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

    @st.cache_data(ttl=300)  # Cache for 5 minutes
    def load_data(url):
        df = pd.read_csv(url, dayfirst=True, dtype={"Vehicle No": str})  # Ensure Vehicle No remains a string
        
        df['Collection Date'] = pd.to_datetime(df['Collection Date'], dayfirst=True, errors='coerce').dt.date
        df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce')
        df['Meter Reading'] = pd.to_numeric(df['Meter Reading'], errors='coerce')

        # Calculate Distance
        df['Distance'] = df['Meter Reading'].diff().fillna(0)

        # Replace negative distances with the average of positive distances
        positive_avg_distance = df[df['Distance'] > 0]['Distance'].mean()
        df.loc[df['Distance'] < 0, 'Distance'] = np.round(positive_avg_distance)

        # Month-Year Column
        df['Month-Year'] = pd.to_datetime(df['Collection Date']).dt.strftime('%Y-%m')

        return df[['Collection Date', 'Vehicle No', 'Amount', 'Meter Reading', 'Name', 'Distance', 'Month-Year']]

    @st.cache_data(ttl=300)  # Cache for 5 minutes
    def load_expense_data(url):
        df = pd.read_csv(url, dayfirst=True, dtype={"Vehicle No": str})  # Ensure Vehicle No remains a string
        df['Date'] = pd.to_datetime(df['Date'], dayfirst=True, errors='coerce').dt.date
        df['Amount Used'] = pd.to_numeric(df['Amount Used'], errors='coerce')
        df['Month-Year'] = pd.to_datetime(df['Date']).dt.strftime('%Y-%m')
        return df[['Date', 'Vehicle No', 'Reason of Expense', 'Amount Used', 'Any Bill', 'Month-Year']]
    
    @st.cache_data(ttl=300)  # Cache for 5 minutes    
    def load_investment_data(url):
        df = pd.read_csv(url, dayfirst=True)

        # Strip spaces from column names to avoid formatting issues
        df.columns = df.columns.str.strip()

        # Ensure required columns exist
        required_columns = ["Date", "Investment Type", "Amount", "Comment", "Received From"]
        missing_columns = [col for col in required_columns if col not in df.columns]

        if missing_columns:
            st.error(f"❌ Missing columns in Investment Data: {missing_columns}")
            return pd.DataFrame()  # Return empty DataFrame to avoid crashing

        # Rename columns for consistency
        df.rename(columns={"Amount": "Investment Amount", "Received From": "Investor Name"}, inplace=True)

        # Convert data types
        df['Date'] = pd.to_datetime(df['Date'], dayfirst=True, errors='coerce').dt.date
        df['Investment Amount'] = pd.to_numeric(df['Investment Amount'], errors='coerce')
        df['Month-Year'] = pd.to_datetime(df['Date']).dt.strftime('%Y-%m')

        return df[['Date', 'Investment Type', 'Investment Amount', 'Comment', 'Investor Name', 'Month-Year']]


    


    df = load_data(COLLECTION_CSV_URL)
    expense_df = load_expense_data(EXPENSE_CSV_URL)
    investment_df = load_investment_data(INVESTMENT_CSV_URL)


    # --- DASHBOARD UI ---
    st.sidebar.header("📂 Navigation")
    page = st.sidebar.radio("Go to:", ["Dashboard", "Monthly Summary", "Grouped Data", "Expenses", "Investment", "Collection Data"])

    if page == "Dashboard":
        st.title("📊 Orga Yatra Dashboard")
        
        total_collection = df['Amount'].sum()
        total_expense = expense_df['Amount Used'].sum()
        total_investment = investment_df['Investment Amount'].sum()

        remaining_fund = total_collection + total_investment - total_expense

        last_month = df['Month-Year'].max()
        last_month_collection = df[df['Month-Year'] == last_month]['Amount'].sum()
        last_month_expense = expense_df[expense_df['Month-Year'] == last_month]['Amount Used'].sum()

        col1, col2, col3, col4 = st.columns(4)
        col1.metric(label="💰 Total Collection", value=f"₹{total_collection:,.2f}")
        col2.metric(label="📉 Total Expenses", value=f"₹{total_expense:,.2f}")
        col3.metric(label="💸 Total Investment", value=f"₹{total_investment:,.2f}")
        col4.metric(label="💵 Remaining Balance", value=f"₹{remaining_fund:,.2f}")


        st.markdown("---")
        formatted_last_month = pd.to_datetime(last_month).strftime("%b %Y")  
        st.subheader("📅 "+formatted_last_month+"   Overview")

        col4, col5 = st.columns(2)
        col4.metric(label="📈"+formatted_last_month+"  Collection", value=f"₹{last_month_collection:,.2f}")
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

        # Group expenses by Month-Year and sum them
        expense_summary = expense_df.groupby('Month-Year', as_index=False)['Amount Used'].sum()

        # Display the summary table
        st.write("### 📊 Monthly Expense Summary")
        st.dataframe(expense_summary)

        # Plot bar chart
        st.write("### 📉 Expense Trend")
        st.bar_chart(expense_summary.set_index("Month-Year"))

        # Display detailed expense data
        st.write("### 🔍 Detailed Expense Data")
        st.dataframe(expense_df.sort_values(by="Date", ascending=False))


    elif page == "Collection Data":
        st.title("📋 Full Collection Data")
        st.dataframe(df.sort_values(by="Collection Date", ascending=False))


    elif page == "Investment":
        st.title("📈 Investment Details")

        # Group investment data by investor
        investment_summary = investment_df.groupby('Investor Name', as_index=False)['Investment Amount'].sum()

        # Group investment data by Month-Year
        monthly_investment = investment_df.groupby('Month-Year', as_index=False)['Investment Amount'].sum()

        # Group investment data by Investment Type
        investment_type_summary = investment_df.groupby('Investment Type', as_index=False)['Investment Amount'].sum()

        # --- ARRANGE PIE CHARTS SIDE BY SIDE ---
        col1, col2 = st.columns(2)

        with col1:
            st.write("### 🎯 Investment by Investor")
            fig1, ax1 = plt.subplots(figsize=(3.5, 3.5))  # Smaller size
            ax1.pie(
                investment_summary['Investment Amount'], 
                labels=investment_summary['Investor Name'], 
                autopct='%1.1f%%', 
                startangle=90, 
                colors=plt.cm.Paired.colors
            )
            ax1.axis("equal")  # Keep it circular
            st.pyplot(fig1)

        with col2:
            st.write("### 💰 Investment by Type")
            fig2, ax2 = plt.subplots(figsize=(3.5, 3.5))  # Same size as investor pie
            ax2.pie(
                investment_type_summary['Investment Amount'], 
                labels=investment_type_summary['Investment Type'], 
                autopct='%1.1f%%', 
                startangle=90, 
                colors=plt.cm.Set3.colors, 
                wedgeprops=dict(width=0.4)  # Donut chart effect
            )
            ax2.axis("equal")
            st.pyplot(fig2)

        # --- SMALLER BAR CHART FOR MONTHLY INVESTMENT ---
        st.write("### 📊 Monthly Investment Trend")
        st.bar_chart(monthly_investment.set_index("Month-Year"), use_container_width=True, height=200)

        # --- DISPLAY DETAILED DATA ---
        st.write("### 🔍 Detailed Investment Data")
        st.dataframe(investment_df.sort_values(by="Date", ascending=False))
