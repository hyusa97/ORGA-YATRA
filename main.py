import streamlit as st
import pandas as pd
import bcrypt

# Streamlit App Configuration
st.set_page_config(page_title="Google Sheets Data", layout="wide")

# Authentication Google Sheets Details
AUTH_SHEET_ID = "1RCIZrxv21hY-xtzDRuC0L50KLCLpZuYWKKatuJoVCT8"
AUTH_SHEET_NAME = "Sheet1"
AUTH_CSV_URL = f"https://docs.google.com/spreadsheets/d/{AUTH_SHEET_ID}/gviz/tq?tqx=out:csv&sheet={AUTH_SHEET_NAME}"

# Load authentication data
def load_auth_data():
    return pd.read_csv(AUTH_CSV_URL)

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
    st.title("🔒 Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password", help="Enter your password")
    login_button = st.button("Login")

    if login_button:
        user_data = auth_df[auth_df["Username"] == username]

        if not user_data.empty:
            stored_hash = user_data.iloc[0]["Password"]
            role = user_data.iloc[0]["Role"]
            name = user_data.iloc[0]["Name"]  # Fetching 'Name' field

            if verify_password(stored_hash, password):
                # Store authentication state in session
                st.session_state.authenticated = True
                st.session_state.user_role = role
                st.session_state.username = username
                st.session_state.user_name = name  # Store user name

                # Persist login across refresh
                st.experimental_set_query_params(logged_in="true")

                st.success(f"✅ Login Successful! Welcome, {name}!")
                st.rerun()
            else:
                st.error("❌ Invalid Credentials")
        else:
            st.error("❌ User not found")

# --- LOGGED-IN USER SEES DASHBOARD ---
else:
    # Sidebar Logout Button
    if st.sidebar.button("Logout"):
        st.session_state.authenticated = False
        st.session_state.user_role = None
        st.session_state.username = None
        st.session_state.user_name = None
        st.experimental_set_query_params(logged_in="false")  # Remove persistent login
        st.rerun()

    # Display logged-in user details
    st.sidebar.write(f"👤 Welcome, **{st.session_state.user_name}**!")

    # --- DASHBOARD CONTENT ---
    SHEET_ID = "1l0RVkf3U0XvWJre74qHy3Nv5n-4TKTCSV5yNVW4Sdbw"
    SHEET_NAME = "Form%20responses%201"
    CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={SHEET_NAME}"

    # Load Data Function
    def load_data(url):
        df = pd.read_csv(url, dayfirst=True)
        df['Collection Date'] = pd.to_datetime(df['Collection Date'], dayfirst=True, errors='coerce').dt.date
        df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce')
        df['Meter Reading'] = pd.to_numeric(df['Meter Reading'], errors='coerce')
        df = df[['Collection Date', 'Vehicle No', 'Amount', 'Meter Reading', 'Name']]
        df['Distance'] = df['Meter Reading'].diff().fillna(0)
        df['Month-Year'] = pd.to_datetime(df['Collection Date']).dt.strftime('%Y-%m')
        return df

    df = load_data(CSV_URL)
    # --- EXPENSE SHEET DETAILS ---
    EXPENSE_SHEET_ID = "1bEquqG2T-obXkw5lWwukx1v_lFnLrFdAf6GlWHZ9J18"
    EXPENSE_SHEET_NAME = "Form%20responses%201"
    EXPENSE_CSV_URL = f"https://docs.google.com/spreadsheets/d/{EXPENSE_SHEET_ID}/gviz/tq?tqx=out:csv&sheet={EXPENSE_SHEET_NAME}"

    # Load Expense Data Function
    def load_expense_data(url):
        df = pd.read_csv(url, dayfirst=True)
        df['Date'] = pd.to_datetime(df['Date'], dayfirst=True, errors='coerce').dt.date
        df['Amount Used'] = pd.to_numeric(df['Amount Used'], errors='coerce')
        df['Month-Year'] = pd.to_datetime(df['Date']).dt.strftime('%Y-%m')
        df = df[['Date', 'Vehicle No', 'Reason of Expense', 'Amount Used', 'Any Bill', 'Month-Year']]
        return df

    expense_df = load_expense_data(EXPENSE_CSV_URL)

    

    # Navigation
    st.sidebar.header("📂 Navigation")
    page = st.sidebar.radio("Go to:", ["Dashboard", "Monthly Summary", "Grouped Data", "Expenses", "Raw Data"])

    # --- 🚀 DASHBOARD SECTION ---
    if page == "Dashboard":
        total_collection = df['Amount'].sum()
        latest_date = df['Collection Date'].max().strftime('%d-%b-%Y')
        col1, col2 = st.columns(2)
        with col1:
            st.metric(label="💰 Total Collection", value=f"₹{total_collection:,.2f}")
        with col2:
            st.metric(label="📅 Last Collection Date", value=latest_date)

        st.write("### 📈 Amount & Distance Over Time")
        st.line_chart(df.set_index("Collection Date")[["Amount", "Distance"]])

        st.write("### 🔍 Recent Collection Data:")
        st.dataframe(df.sort_values(by="Collection Date", ascending=False).head(10))

    # --- 📅 MONTHLY SUMMARY SECTION ---
    elif page == "Monthly Summary":
        st.write("### 📊 Monthly Collection vs Expense")

        collection_summary = df.groupby('Month-Year', as_index=False)['Amount'].sum()
        expense_summary = expense_df.groupby('Month-Year', as_index=False)['Amount Used'].sum()

        merged_summary = pd.concat([collection_summary, expense_summary], axis=0, ignore_index=True)
        final_summary = merged_summary.groupby('Month-Year', as_index=False).sum()
        final_summary.columns = ['Month-Year', 'Total Collection', 'Total Expense']

        st.dataframe(final_summary)
        st.bar_chart(final_summary.set_index("Month-Year"))

        


    # --- 👥 GROUPED DATA SECTION ---
    elif page == "Grouped Data":
        st.write("### 🔍 Grouped Collection Data")
        group_by = st.sidebar.radio("🔄 Group Data By:", ["Name", "Vehicle No"])
        available_months = sorted(df['Month-Year'].dropna().unique(), reverse=True)
        selected_month = st.sidebar.selectbox("📅 Select Month-Year:", available_months)
        df_filtered = df[df['Month-Year'] == selected_month]

        if df_filtered.empty:
            st.warning(f"No data available for {selected_month}")
        else:
            if group_by == "Name":
                df_filtered['Name'] = df_filtered['Name'].str.strip().str.lower().str.title()
                grouped_df = df_filtered.groupby('Name', as_index=False)['Amount'].sum()
                grouped_df.columns = ['Name', 'Total Amount']
            else:
                grouped_df = df_filtered.groupby('Vehicle No', as_index=False)['Amount'].sum()
                grouped_df.columns = ['Vehicle No', 'Total Amount']

            st.dataframe(grouped_df)
            st.bar_chart(grouped_df.set_index(group_by)["Total Amount"])

    # --- 🚗 EXPENSE DETAILS SECTION ---
    if page == "Expenses":
        st.write("### 💸 Expense Details")
        
        total_expense = expense_df["Amount Used"].sum()
        st.metric(label="📉 Total Expenses", value=f"₹{total_expense:,.2f}")

        # Convert Date to Month-Year for aggregation
        expense_df["Month-Year"] = pd.to_datetime(expense_df["Date"], format="%d/%m/%Y").dt.strftime("%Y-%m")

        # Grouping expenses by Month-Year
        monthly_expense = expense_df.groupby("Month-Year", as_index=False)["Amount Used"].sum()
        monthly_expense.columns = ["Month-Year", "Total Expense"]

        # 📊 Monthly Expense Trend
        st.write("### 📊 Monthly Expense Summary")
        st.bar_chart(monthly_expense.set_index("Month-Year")["Total Expense"])

        # 📋 Detailed Expense Breakdown
        st.write("### 📋 Expense Breakdown by Month")
        st.dataframe(monthly_expense)
        
        # 📋 Full Expense Data
        st.write("### 📋 All Expenses")
        st.dataframe(expense_df.sort_values(by="Date", ascending=False))

    # --- 📋 RAW DATA SECTION ---
    elif page == "Raw Data":
        st.write("### 📋 Full Collection Data (Sorted by Date)")
        st.dataframe(df.sort_values(by="Collection Date", ascending=False))
