import streamlit as st
import pandas as pd
import numpy as np
import time
import bcrypt
import matplotlib.pyplot as plt
import gspread
from google.oauth2.service_account import Credentials
from datetime import date, time, datetime, timedelta
import pytz
from urllib.parse import quote
import streamlit.components.v1 as components





# Function to get the background color based on amount
def get_background_style(amount):
    if amount == 0:
        return "linear-gradient(135deg, #880044, #440022);" # Very Bad
    elif 1 <= amount <= 299:
        return "linear-gradient(135deg, #4da6ff, #0077b6);" # Good
    elif amount == 300:
        return "linear-gradient(135deg, #FFD400, #FFB800);" # Happy
    elif amount > 300:
        return "linear-gradient(135deg, #00FF7F, #00994C);" # More Happy
    return "linear-gradient(135deg, #4da6ff, #0077b6);" # Default if none match

# HTML + CSS for both sets of cards
html_content = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600&display=swap');

.card-container {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
    justify-content: flex-start;
    align-items: flex-start;
}
.card {
    border-radius: 12px;
    padding: 12px;
    box-shadow: 0 6px 12px rgba(0, 0, 0, 0.2);
    width: 160px;
    height: 120px; /* Increased height to fit content better */
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    transition: transform 0.3s ease, box-shadow 0.3s ease;
    font-family: 'Poppins', sans-serif;
    position: relative;
    overflow: hidden;
}
.card::before {
    content: '';
    position: absolute;
    top: -10px;
    left: -10px;
    width: 30px;
    height: 30px;
    background: #ffffff30;
    border-radius: 50%;
    transform: scale(0);
    transition: transform 0.4s ease;
}
.card:hover::before {
    transform: scale(20);
}
.card:hover {
    transform: translateY(-4px);
    box-shadow: 0 10px 18px rgba(0, 0, 0, 0.35);
}

.vehicle-no {
    font-size: 1.1em;
    font-weight: 600;
    margin-bottom: 5px;
    z-index: 1;
    color: #ffffff;
    text-align: center;
}

/* Explicitly set color to black for all other text elements */
.date,
.meter-reading-header,
.info-left,
.info-right,
.info-value,
.info-value.name {
    color: #000000;
}

.card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 5px;
    z-index: 1;
}

.date, .meter-reading-header {
    font-size: 0.7em;
    font-weight: 600;
    opacity: 1;
    z-index: 1;
}

.info-row {
    display: flex;
    justify-content: space-between;
    align-items: flex-end;
    margin-top: auto;
}

.info-left, .info-right {
    display: flex;
    flex-direction: column;
    font-size: 0.75em;
    z-index: 1;
}
.info-value {
    font-weight: 600;
}
.info-value.name {
    text-align: right;
}
</style>

<div class="card-container">
"""


# Start building HTML for all buttons
buttons_html = """
        <style>
        .button-container {
            display: flex;
            flex-wrap: wrap; /* wrap into next line if too many */
            gap: 12px;       /* spacing between buttons */
        }
        .custom-btn {
            background: linear-gradient(135deg, #ff512f, #dd2476);
            color: white !important;
            padding: 12px 20px;
            font-size: 16px;          /* ✅ vehicle number bigger */
            font-weight: 700;
            border: none;
            border-radius: 12px;
            cursor: pointer;
            box-shadow: 0 4px 6px rgba(0,0,0,0.2);
            transition: all 0.3s ease;
            text-decoration: none !important;
            display: flex;            /* ✅ flexbox for stacking */
            flex-direction: column;   /* ✅ stack vertically */
            align-items: center;      /* ✅ center horizontally */
            justify-content: center;  /* ✅ center vertically */
        }
        .vehicle-no {
            font-size: 16px;
            font-weight: 700;
        }
        .missing-date {
            margin-top: 4px;
            font-size: 12px;      /* ✅ smaller */
            font-weight: 400;
            color: #000000;       /* ✅ light white/grey */
        }
        .custom-btn:hover {
            transform: translateY(-3px);
            box-shadow: 0 6px 10px rgba(0,0,0,0.3);
            background: linear-gradient(135deg, #dd2476, #ff512f);
        }
        </style>
        <div class="button-container">
        """

# Streamlit App Configuration
st.set_page_config(page_title="Google Sheets Dashboard", layout="wide")


# Load Google Sheet IDs securely
AUTH_SHEET_ID = st.secrets["sheets"]["AUTH_SHEET_ID"]
COLLECTION_SHEET_ID = st.secrets["sheets"]["COLLECTION_SHEET_ID"]
EXPENSE_SHEET_ID = st.secrets["sheets"]["EXPENSE_SHEET_ID"]
INVESTMENT_SHEET_ID = st.secrets["sheets"]["INVESTMENT_SHEET_ID"]
BANK_SHEET_ID = st.secrets["sheets"]["BANK_SHEET_ID"]


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


# --- Bank DATA ---

BANK_SHEET_NAME = "Bank_Transaction"
BANK_CSV_URL = f"https://docs.google.com/spreadsheets/d/{BANK_SHEET_ID}/gviz/tq?tqx=out:csv&sheet={BANK_SHEET_NAME}"

# ✅ Load credentials from Streamlit Secrets (Create a Copy)
creds_dict = dict(st.secrets["gcp_service_account"])  # Create a mutable copy

# ✅ Fix private key formatting
creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")

# ✅ Function to Connect to Google Sheets (with Caching)
@st.cache_resource  # Cache for 5 minutes
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
        BANK_sheet = client.open_by_key(st.secrets["sheets"]["BANK_SHEET_ID"]).worksheet(BANK_SHEET_NAME)
        
        return AUTH_sheet, COLLECTION_sheet, EXPENSE_sheet, INVESTMENT_sheet , BANK_sheet

    except Exception as e:
        st.error(f"❌ Failed to connect to Google Sheets: {e}")
        st.stop()




# ✅ Get cached sheets
AUTH_sheet, COLLECTION_sheet, EXPENSE_sheet, INVESTMENT_sheet ,BANK_sheet= connect_to_sheets()

# Function to load authentication data securely
@st.cache_resource # Cache for 5 minutes
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

    @st.cache_resource # Cache for 5 minutes
    def load_data(url):
        df = pd.read_csv(url, dayfirst=True, dtype={"Vehicle No": str})  # Ensure Vehicle No remains a string
        
        df['Collection Date'] = pd.to_datetime(df['Collection Date'], dayfirst=True, errors='coerce').dt.date
        df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce')
        df['Meter Reading'] = pd.to_numeric(df['Meter Reading'], errors='coerce')

        # Assuming df is your DataFrame and it's already sorted by 'Collection Date'
        df = df.sort_values(by=['Vehicle No', 'Collection Date'])

        # Calculate distance for each vehicle separately
        df['Distance'] = df.groupby('Vehicle No')['Meter Reading'].diff().fillna(0)

        # Replace negative distances with the average of positive distances
        positive_avg_distance = df[df['Distance'] > 0]['Distance'].mean()
        df.loc[df['Distance'] < 0, 'Distance'] = np.round(positive_avg_distance)

        # Month-Year Column
        df['Month-Year'] = pd.to_datetime(df['Collection Date']).dt.strftime('%Y-%m')

        return df[['Collection Date', 'Vehicle No', 'Amount', 'Meter Reading', 'Name', 'Distance', 'Month-Year','Received By']]

    @st.cache_resource  # Cache for 5 minutes
    def load_expense_data(url):
        df = pd.read_csv(url, dayfirst=True, dtype={"Vehicle No": str})  # Ensure Vehicle No remains a string
        df['Date'] = pd.to_datetime(df['Date'], dayfirst=True, errors='coerce').dt.date
        df['Amount Used'] = pd.to_numeric(df['Amount Used'], errors='coerce')
        df['Month-Year'] = pd.to_datetime(df['Date']).dt.strftime('%Y-%m')
        return df[['Date', 'Vehicle No', 'Reason of Expense', 'Amount Used', 'Any Bill', 'Month-Year','Expense By']]
    
    @st.cache_resource  # Cache for 5 minutes    
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

    @st.cache_resource
    def load_bank_data(url):
        df = pd.read_csv(url, dayfirst=True)
        df['Date'] = pd.to_datetime(df['Date'], dayfirst=True, errors='coerce').dt.date
        df['Month-Year'] = pd.to_datetime(df['Date']).dt.strftime('%Y-%m')
        return df

    


    df = load_data(COLLECTION_CSV_URL)
    expense_df = load_expense_data(EXPENSE_CSV_URL)
    investment_df = load_investment_data(INVESTMENT_CSV_URL)
    bank_df = load_bank_data(BANK_CSV_URL)


    # Calculate credits and debits
    # Ensure Amount is numeric
    bank_df['Amount'] = pd.to_numeric(bank_df['Amount'], errors='coerce').fillna(0)

    # Calculate total credits and debits
    Collection_Credit_Bank=bank_df[bank_df['Transaction Type'].isin(['Collection_Credit'])]['Amount'].sum()
    Investment_Credit_Bank=bank_df[bank_df['Transaction Type'].isin(['Investment_Credit'])]['Amount'].sum()
    Payment_Credit_Bank=bank_df[bank_df['Transaction Type'].isin(['Payment_Credit'])]['Amount'].sum()
    ## by ayush
    settlement_credit = bank_df[bank_df['Transaction Type'].isin(['Settlement_Credit'])]['Amount'].sum()

    total_credits = Collection_Credit_Bank+Investment_Credit_Bank+Payment_Credit_Bank+settlement_credit

    Expence_Debit_Bank=bank_df[bank_df['Transaction Type'].isin(['Expence_Debit'])]['Amount'].sum()
    
    Settlement_Debit_Bank=bank_df[bank_df['Transaction Type'].isin(['Settlement_Debit'])]['Amount'].sum()
    total_debits = Expence_Debit_Bank+Settlement_Debit_Bank

    bank_balance = total_credits - total_debits

    # === Individual Summary ===
    # Initialize all required variables
    # For Govind Kumar
    govind_collection_credit = 0
    govind_settlement_credit = 0
    govind_investment_credit = 0
    govind_total_credit = 0
    govind_expense_debit = 0
    govind_settlement_debit = 0
    govind_total_debit = 0

    # For Kumar Gaurav
    gaurav_collection_credit = 0
    gaurav_settlement_credit = 0
    gaurav_investment_credit = 0
    gaurav_total_credit = 0
    gaurav_expense_debit = 0
    gaurav_settlement_debit = 0
    gaurav_total_debit = 0

    # Filter data by person and assign values
    govind_df = bank_df[bank_df['Transaction By'] == 'Govind Kumar']
    gaurav_df = bank_df[bank_df['Transaction By'] == 'Kumar Gaurav']

    # Govind Kumar
    govind_collection_credit = govind_df[govind_df['Transaction Type'] == 'Collection_Credit']['Amount'].sum()
    govind_settlement_credit = govind_df[govind_df['Transaction Type'] == 'Settlement_Credit']['Amount'].sum()
    govind_investment_credit = govind_df[govind_df['Transaction Type'] == 'Investment_Credit']['Amount'].sum()
    govind_total_credit = govind_collection_credit + govind_settlement_credit + govind_investment_credit

    govind_expense_debit = govind_df[govind_df['Transaction Type'] == 'Expence_Debit']['Amount'].sum()
    govind_settlement_debit = govind_df[govind_df['Transaction Type'] == 'Settlement_Debit']['Amount'].sum()
    govind_total_debit = govind_expense_debit + govind_settlement_debit

    # Kumar Gaurav
    gaurav_collection_credit = gaurav_df[gaurav_df['Transaction Type'] == 'Collection_Credit']['Amount'].sum()
    gaurav_settlement_credit = gaurav_df[gaurav_df['Transaction Type'] == 'Settlement_Credit']['Amount'].sum()
    gaurav_investment_credit = gaurav_df[gaurav_df['Transaction Type'] == 'Investment_Credit']['Amount'].sum()
    gaurav_total_credit = gaurav_collection_credit + gaurav_settlement_credit + gaurav_investment_credit

    gaurav_expense_debit = gaurav_df[gaurav_df['Transaction Type'] == 'Expence_Debit']['Amount'].sum()
    gaurav_settlement_debit = gaurav_df[gaurav_df['Transaction Type'] == 'Settlement_Debit']['Amount'].sum()
    gaurav_total_debit = gaurav_expense_debit + gaurav_settlement_debit

    #------------Bank Calculation End-----------------



    #-------------Remaining Balance at you ----------





    #---------------Remaining Balance calculation end------------
    ## Current month loss calculation ##
    # ---------- Base DF ----------
    perf_df = df.copy()
    perf_df["Collection Date"] = pd.to_datetime(
    perf_df["Collection Date"], dayfirst=True, errors="coerce"
    ).dt.normalize()
    perf_df["Amount"] = pd.to_numeric(perf_df["Amount"], errors="coerce").fillna(0)
    perf_df = perf_df.dropna(subset=["Collection Date"])


        #st.write(f"start_date: {custom_start_date}, end_date: {custom_end_date}")

    # ---------- Loss Matrix preprocessing ----------
    def apply_loss_matrix_logic(input_df: pd.DataFrame) -> pd.DataFrame:
        df_proc = input_df.copy()
        df_proc = df_proc.dropna(subset=["Collection Date"]).copy()
        df_proc["Amount"] = pd.to_numeric(df_proc["Amount"], errors="coerce").fillna(0)

        # Subtract 300 and flip sign
        df_proc["Amount"] = (df_proc["Amount"] - 300) * -1

        # Handle multi-vehicle for same driver/date
        df_proc = df_proc.sort_values(by=["Collection Date", "Name", "Vehicle No"])
        updated_rows = []
        grouped = df_proc.groupby(["Collection Date", "Name"], group_keys=False)

        for (date, driver), group in grouped:
            if driver != "Zero Collection" and len(group) > 1:
                total_amt = group["Amount"].sum()

                first_loss = (total_amt - 300) #* -1

                second_loss = 300 + first_loss

                first_row = group.iloc[0].copy().to_dict()
                second_row = group.iloc[1].copy().to_dict()

                if first_loss <= -300:
                    first_loss = 0
                else:
                    second_row["Name"] = "Zero Collection"


                first_row["Amount"] = first_loss
                second_row["Amount"] = second_loss
                     

                updated_rows.extend([first_row, second_row])
            else:
                updated_rows.extend(group.to_dict("records"))

        return pd.DataFrame(updated_rows)
    # Apply new Loss Matrix logic
    perf_df_lm = apply_loss_matrix_logic(perf_df)
    # apply your exact driver vs company split here

    #-------- current month loss ---------#
    today = pd.Timestamp.today().normalize()
    current_month_df = perf_df_lm[
        (perf_df_lm["Collection Date"].dt.year == today.year) &
        (perf_df_lm["Collection Date"].dt.month == today.month)
        ]
    current_total_loss = max(0, current_month_df["Amount"].sum() if not current_month_df.empty else 0)
    current_company_loss = max(0, current_month_df.loc[current_month_df["Name"] == "Zero Collection", "Amount"].sum() if not current_month_df.empty else 0)
    current_driver_loss = max(0, current_total_loss - current_company_loss)

    



    # --- DASHBOARD UI ---
    st.sidebar.header("📂 Navigation")
    page = st.sidebar.radio("Go to:", ["Dashboard", "Monthly Summary", "Grouped Data", "Expenses", "Investment", "Collection Data", "Bank Transaction", "Performance" ])

    if page == "Dashboard":
        st.title("📊 VayuVolt Dashboard")
        
        # Get latest month
        last_month = df['Month-Year'].max()

        # Optional: Clean column names in case of leading/trailing spaces
        df.columns = df.columns.str.strip()
        expense_df.columns = expense_df.columns.str.strip()
        investment_df.columns = investment_df.columns.str.strip()
        
        # === Individual Totals (Govind Kumar) ===
        govind_total_collection = df[df['Received By'].isin(['Govind Kumar'])]['Amount'].sum()
        govind_total_investment = investment_df[investment_df['Investor Name'].isin(['Govind Kumar'])]['Investment Amount'].sum()
        govind_total_expense = expense_df[expense_df['Expense By'].isin(['Govind Kumar'])]['Amount Used'].sum()

        govind_last_month_collection = df[(df['Received By'].isin(['Govind Kumar'])) & (df['Month-Year'] == last_month)]['Amount'].sum()
        govind_last_month_expense = expense_df[(expense_df['Expense By'].isin(['Govind Kumar'])) & (expense_df['Month-Year'] == last_month)]['Amount Used'].sum()

        # === Individual Totals (Kumar Gaurav) ===
        gaurav_total_collection = df[df['Received By'].isin(['Kumar Gaurav'])]['Amount'].sum()
        gaurav_total_investment = investment_df[investment_df['Investor Name'].isin(['Kumar Gaurav'])]['Investment Amount'].sum()
        gaurav_total_expense = expense_df[expense_df['Expense By'].isin(['Kumar Gaurav'])]['Amount Used'].sum()

        gaurav_last_month_collection = df[(df['Received By'].isin(['Kumar Gaurav'])) & (df['Month-Year'] == last_month)]['Amount'].sum()
        gaurav_last_month_expense = expense_df[(expense_df['Expense By'].isin(['Kumar Gaurav'])) & (expense_df['Month-Year'] == last_month)]['Amount Used'].sum()

        # === Combined Totals ===
        total_collection = govind_total_collection + gaurav_total_collection
        total_investment = govind_total_investment + gaurav_total_investment + Investment_Credit_Bank
        total_expense = govind_total_expense + gaurav_total_expense + govind_expense_debit +gaurav_expense_debit

        remaining_fund_gaurav= (gaurav_total_collection - gaurav_total_expense - gaurav_collection_credit + gaurav_settlement_debit - gaurav_settlement_credit + gaurav_total_investment)
        remaining_fund_govind= (govind_total_collection - govind_total_expense - govind_collection_credit + govind_settlement_debit - govind_settlement_credit + govind_total_investment)
        Net_balance=remaining_fund_gaurav + remaining_fund_govind + bank_balance

        last_month_collection = govind_last_month_collection + gaurav_last_month_collection
        last_month_expense = govind_last_month_expense + gaurav_last_month_expense

        collection_percentage_current_month = round((last_month_collection/(last_month_collection + current_total_loss)) * 100)
        total_loss_percentage_current_month = round((current_total_loss/(last_month_collection + current_total_loss)) * 100)
  

        col1, col2, col3, col4, col5,col6,col7 = st.columns(7)
        col1.metric(label="💰 Total Collection", value=f"₹{total_collection:,.0f}")
        col2.metric(label="📉 Total Expenses", value=f"₹{total_expense:,.0f}")
        col3.metric(label="💸 Total Investment", value=f"₹{total_investment:,.0f}")
        col4.metric(label="💵 Govind Balance", value=f"₹{remaining_fund_govind:,.0f}")
        col5.metric(label="💵 Gaurav Balance", value=f"₹{remaining_fund_gaurav:,.0f}")
        col6.metric(label="🏦 Bank Balance", value=f"₹{bank_balance:,.0f}")
        col7.metric(label="🏦 Net Balance", value=f"₹{Net_balance:,.0f}")


        st.markdown("---")
        formatted_last_month = pd.to_datetime(last_month).strftime("%b %Y")  
        st.subheader("📅 "+formatted_last_month+"   Overview")

        col4, col5, col6, col7, col8, col9, col10 = st.columns(7)
        col4.metric(label="📈"+formatted_last_month+"  Collection", value=f"₹{last_month_collection:,.0f}")
        col5.metric(label=" ", value=f"{collection_percentage_current_month:,.0f}%", delta=f"{collection_percentage_current_month:,.0f}%", delta_color="normal")
        col6.metric(label="📉"+formatted_last_month+" Expenses", value=f"₹{last_month_expense:,.0f}")
        col7.metric(label="📉"+formatted_last_month+" Driver Loss", value= f"{max(current_driver_loss,0):,.0f}")
        col8.metric(label="📉"+formatted_last_month+" Company Loss",value= f"{max(current_company_loss,0):,.0f}")
        col9.metric(label="📉"+formatted_last_month+" Total Loss",value= f"{max(current_total_loss,0):,.0f}")
        col10.metric(label=" ", value=f"{total_loss_percentage_current_month:,.0f}%", delta=f"{total_loss_percentage_current_month:,.0f}%", delta_color="inverse")




        st.markdown("---")
        
        # Convert Collection Date to datetime
        df["Collection Date"] = pd.to_datetime(df["Collection Date"])
        
        # Default full data before filtering
        filtered_df = df.copy()
        
        # === RADIO BUTTONS CENTERED BELOW CHART ===
        col1, col2, col3 = st.columns([1, 3, 1])  # Center the middle column
        with col2:
            range_option = st.radio(
                "",
                ["1 Week", "1 Month", "3 Months", "6 Months", "1 Year", "3 Years", "5 Years", "Max"],
                horizontal=True,
                index =2
            )
        
        # Determine the date range based on selection
        today = pd.to_datetime("today")
        if range_option == "1 Week":
            start_date = today - pd.Timedelta(weeks=1)
        elif range_option == "1 Month":
            start_date = today - pd.DateOffset(months=1)
        elif range_option == "3 Months":
            start_date = today - pd.DateOffset(months=3)
        elif range_option == "6 Months":
            start_date = today - pd.DateOffset(months=6)
        elif range_option == "1 Year":
            start_date = today - pd.DateOffset(years=1)
        elif range_option == "3 Years":
            start_date = today - pd.DateOffset(years=3)
        elif range_option == "5 Years":
            start_date = today - pd.DateOffset(years=5)
        else:
            start_date = df["Collection Date"].min()
        
        # Filter data based on selected date range
        filtered_df = df[df["Collection Date"] >= start_date]
        
        # === RERENDER CHART ===
        st.line_chart(filtered_df.set_index("Collection Date")[["Amount", "Distance"]])


        ## changes start here by Ayush

        
        # Pending Collection
        # Clean 'Vehicle No' column: ensure all values are strings with no leading/trailing spaces
        df['Vehicle No'] = df['Vehicle No'].astype(str).str.strip()
        # Convert 'Collection Date' to datetime format (day first), coerce invalid values to NaT, and keep only the date part
        df['Collection Date'] = pd.to_datetime(df['Collection Date'], dayfirst=True, errors='coerce').dt.date
        
        # Start date for pending collection tracking
        start_date = date(2025, 8, 1)
        
        # Get all unique vehicle numbers
        baseline_vehicles = df['Vehicle No'].unique()

        # If no vehicles found for the dataset, show warning
        if len(baseline_vehicles)==0:
            st.warning("no rows found for 1 august")
            baseline_vehicles = df['Vehicle No'].unique()

        # Get the current time in Asia/Kolkata timezone and Get today's date and yesterday's date
        tz = pytz.timezone("Asia/Kolkata")
        now = datetime.now(tz)
        latest_date = date.today()
        yesterday = latest_date - timedelta(days=1)
        cur_hour = now.hour
        # If current time is after 4 PM, include today in the date range, else only till yesterday
        if cur_hour >= 16:
            all_dates = pd.date_range(start=start_date, end=latest_date)
        else:
            all_dates = pd.date_range(start=start_date, end= yesterday)
        all_dates = [d.date() for d in all_dates.to_pydatetime()]

        # Determine baseline collection dates for each vehicle 
        first_dates = df.groupby('Vehicle No')['Collection Date'].min()
        baseline_dates = {}
        for v,f_date in first_dates.items():
            if f_date <= start_date:
                baseline_dates[v] = start_date
            else:
                baseline_dates[v] = f_date

        # --- Identify missing collection entries
        missing_entries = []

        for cur_date in all_dates:
            # Vehicles that should be active on this date
            active_vehicles = [v for v, base_date in baseline_dates.items() if base_date <= cur_date]
            # Vehicles that actually have a collection entry on this date
            vehicles_on_date = df[df['Collection Date'] == cur_date]['Vehicle No'].unique()

            # Vehicles that are missing collection on this date
            missing_vehicles = [v for v in active_vehicles if v not in vehicles_on_date]
            for v in missing_vehicles:
                # Get vehicle's collection history before the current date
                vehicle_history= df[(df['Vehicle No']== v) & (df['Collection Date']< cur_date)].sort_values('Collection Date')

                # Filter rows with non-zero collection amounts
                non_zero_history = vehicle_history[vehicle_history['Amount'] > 0]
                if not non_zero_history.empty:
                    # Last date when non-zero collection happened
                    last_non_zero_row = non_zero_history.iloc[-1]
                    last_non_zero_date = last_non_zero_row['Collection Date']
                    last_non_zero_amount = last_non_zero_row['Amount']
                    last_meter_reading = last_non_zero_row['Meter Reading']
                    last_driver_name = last_non_zero_row['Name']
                

                else:
                    # If no non-zero collection ever happened
                    last_non_zero_date =None
                    last_non_zero_amount = None
                    last_meter_reading = None

                    # Get last driver name if any history exists 
                    if not vehicle_history.empty:
                        last_driver_name = vehicle_history.iloc[-1]['Name']
                    else:
                        last_driver_name = None

                
                # Calculate number of days since last non-zero collection with zero amount
                if last_non_zero_date:
                    zero_days = vehicle_history[
                        (vehicle_history['Collection Date']> last_non_zero_date)& (vehicle_history['Amount'] == 0)
                    ].shape[0]

                else:
                    zero_days = 0

                
                
                missing_entries.append({"Missing Date": cur_date, "Vehicle No":v, "Last Meter Reading": last_meter_reading, "Last Assigned Name": last_driver_name, "Last Collected Amount": last_non_zero_amount, "Last Collection date": last_non_zero_date, "Zero Collection from(Days)":zero_days })
        
        missing_df = pd.DataFrame(missing_entries)


        # Display pending collection data        
        
        if missing_df.empty:
            st.write("### 🔍 Recent Collection:")
            Recent_Collection = df.sort_values(by="Collection Date", ascending=False).head(14)
            Recent_Collection["Collection Date"] = pd.to_datetime(Recent_Collection["Collection Date"])
            Recent_Collection["Collection Date"] = Recent_Collection["Collection Date"].dt.strftime("%d %b %Y")
            for _, row in Recent_Collection.iterrows():
                bg_style = get_background_style(row['Amount'])
                        
                html_content += f"""
                    <div class="card" style="background: {bg_style}">
                        <div class="vehicle-no">{row['Vehicle No']}</div>
                        <hr style="border-top: 2px solid #000; margin-top: 5px; margin-bottom: 5px;">
                        <div class="card-header">
                            <div class="date">{row['Collection Date']}</div>
                            <div class="meter-reading-header">{row['Meter Reading']} Km</div>
                        </div>
                        <div class="info-row">
                            <div class="info-left">
                                <div class="info-value">₹ {row['Amount']}</div>
                                <div class="info-value">{row['Distance']} km</div>
                            </div>
                            <div class="info-right">
                                <div class="info-value name">{row['Name']}</div>
                            </div>
                        </div>
                    </div>
                """

            html_content += "</div>"

            # Render HTML
            components.html(html_content, height=300, scrolling=True)
        else:
            st.subheader("🕒 Pending Collection:")
            form_base = "https://docs.google.com/forms/d/e/1FAIpQLSdnNBpKKxpWVkrZfj0PLKW8K26-3i0bO43hBADOHvGcpGqjvA/viewform?usp=pp_url"

            

            # Add each button to the HTML string
            for _, row in missing_df.iterrows():
                form_link = (
                    f"{form_base}"
                    f"&entry.1817078140={quote(str(row['Missing Date']))}"
                    f"&entry.424776091={quote(str(row['Vehicle No']))}"
                    f"&entry.1100483606={quote(str(row['Last Collected Amount']))}"  
                    f"&entry.1947342081={quote(str(row['Last Meter Reading']))}"
                    f"&entry.1812763042={quote(str(row['Last Assigned Name']))}"
                    f"&entry.1925700467={quote('Govind Kumar')}"
                )

                buttons_html += f"""
        <a href="{form_link}" target="_blank" class="custom-btn">
            <span class="vehicle-no">{row['Vehicle No']}</span>
            <span class="missing-date">{row['Missing Date']}</span>
        </a>
        """

            buttons_html += "</div>"

            # Render all buttons at once
            st.markdown(buttons_html, unsafe_allow_html=True)
            



        ## changes by ayush end here ##############################

    elif page == "Monthly Summary":
        st.title("📊 Monthly Summary Report")
    
        # --- Monthly Aggregation ---
        # Govind and Gaurav Collection
        govind_monthly = df[df['Received By'] == 'Govind Kumar'].groupby('Month-Year', as_index=False)['Amount'].sum().rename(columns={"Amount": "Govind Collection"})
        gaurav_monthly = df[df['Received By'] == 'Kumar Gaurav'].groupby('Month-Year', as_index=False)['Amount'].sum().rename(columns={"Amount": "Gaurav Collection"})
    
        # Govind and Gaurav Expenses
        govind_expense_monthly = expense_df[expense_df['Expense By'] == 'Govind Kumar'].groupby('Month-Year', as_index=False)['Amount Used'].sum().rename(columns={"Amount Used": "Govind Expense"})
        gaurav_expense_monthly = expense_df[expense_df['Expense By'] == 'Kumar Gaurav'].groupby('Month-Year', as_index=False)['Amount Used'].sum().rename(columns={"Amount Used": "Gaurav Expense"})
    
        # Merge all
        monthly_summary = pd.merge(govind_monthly, gaurav_monthly, on="Month-Year", how="outer")
        monthly_summary = pd.merge(monthly_summary, govind_expense_monthly, on="Month-Year", how="outer")
        monthly_summary = pd.merge(monthly_summary, gaurav_expense_monthly, on="Month-Year", how="outer")
    
        monthly_summary.fillna(0, inplace=True)
    
        # Total columns
        monthly_summary["Total Collection"] = monthly_summary["Govind Collection"] + monthly_summary["Gaurav Collection"]
        monthly_summary["Total Expense"] = monthly_summary["Govind Expense"] + monthly_summary["Gaurav Expense"]
    
        # Net Balance
        monthly_summary["Net Balance"] = monthly_summary["Total Collection"] - monthly_summary["Total Expense"]
    
        # Percentage Change
        monthly_summary["Collection Change (%)"] = monthly_summary["Total Collection"].pct_change().fillna(0) * 100
        monthly_summary["Expense Change (%)"] = monthly_summary["Total Expense"].pct_change().fillna(0) * 100
    
        # Reorder columns
        ordered_columns = [
            "Month-Year", 
            "Govind Collection", "Gaurav Collection", 
            "Total Collection", "Collection Change (%)", 
            "Govind Expense", "Gaurav Expense", 
            "Total Expense", "Expense Change (%)", 
            "Net Balance"
        ]
        monthly_summary = monthly_summary[ordered_columns]
    
        # === UI ===
        st.subheader("📅 Monthly Breakdown")
        st.dataframe(monthly_summary.style.format({
            "Govind Collection": "₹{:.0f}",
            "Gaurav Collection": "₹{:.0f}",
            "Total Collection": "₹{:.0f}",
            "Collection Change (%)": "{:+.1f}%",
            "Govind Expense": "₹{:.0f}",
            "Gaurav Expense": "₹{:.0f}",
            "Total Expense": "₹{:.0f}",
            "Expense Change (%)": "{:+.1f}%",
            "Net Balance": "₹{:.0f}"
        }), use_container_width=True)
    
        # === Charts ===
        chart_option = st.radio("📊 Show Chart for:", ["Collection vs Expense", "Net Balance Trend"])
        
        if chart_option == "Collection vs Expense":
            chart_df = monthly_summary[["Month-Year", "Total Collection", "Total Expense"]].set_index("Month-Year")
            st.bar_chart(chart_df)
        else:
            net_df = monthly_summary[["Month-Year", "Net Balance"]].set_index("Month-Year")
            st.line_chart(net_df)
    
        # === Download Option ===
        csv = monthly_summary.to_csv(index=False).encode("utf-8")
        st.download_button("⬇️ Download Monthly Summary (CSV)", data=csv, file_name="monthly_summary.csv", mime="text/csv")


    elif page == "Grouped Data":
        st.title("🔍 Grouped Collection Data")
    
        group_by = st.sidebar.radio("🔄 Group Data By:", ["Name", "Vehicle No"])
        selected_month = st.sidebar.selectbox("📅 Select Month-Year:", ["All"] + sorted(df['Month-Year'].unique(), reverse=True))
    
        chart_type = st.sidebar.radio("📈 Show Chart For:", ["Amount", "Distance", "Both"])
        top_n = st.sidebar.slider("🔢 Show Top N Groups", min_value=3, max_value=20, value=10)
    
        # Filter by month
        df_filtered = df.copy()
        if selected_month != "All":
            df_filtered = df[df['Month-Year'] == selected_month]
    
        # Grouping logic
        grouped_df = df_filtered.groupby(group_by, as_index=False).agg({
            "Amount": "sum",
            "Distance": "sum",
            "Collection Date": "count"
        }).rename(columns={"Collection Date": "Total Collections"})
    
        # Add averages
        grouped_df["Avg Amount"] = grouped_df["Amount"] / grouped_df["Total Collections"]
        grouped_df["Avg Distance"] = grouped_df["Distance"] / grouped_df["Total Collections"]
    
        # Sort and get top N
        grouped_df = grouped_df.sort_values(by="Amount", ascending=False).head(top_n)
    
        # Display Data
        st.subheader(f"📊 Top {top_n} - Grouped by {group_by}")
        st.dataframe(grouped_df.style.format({
            "Amount": "₹{:.0f}",
            "Distance": "{:.0f} km",
            "Avg Amount": "₹{:.0f}",
            "Avg Distance": "{:.1f} km"
        }), use_container_width=True)
    
        # Download CSV
        csv_grouped = grouped_df.to_csv(index=False).encode("utf-8")
        st.download_button("⬇️ Download Grouped Data", data=csv_grouped, file_name="grouped_data.csv", mime="text/csv")
    
        # Chart View
        st.subheader("📈 Grouped Chart")
    
        if chart_type == "Amount":
            st.bar_chart(grouped_df.set_index(group_by)["Amount"])
        elif chart_type == "Distance":
            st.bar_chart(grouped_df.set_index(group_by)["Distance"])
        else:
            st.line_chart(grouped_df.set_index(group_by)[["Amount", "Distance"]])
    

    elif page == "Expenses":
        st.title("💸 Expense Insights")
    
        # Add Expense Button
        col1, col2 = st.columns([6, 1])
        with col2:
            st.markdown(
                f'<a href="https://forms.gle/y1F2diJeG6WBfTmu9" target="_blank">'
                f'<button style="background-color:#4CAF50; color:white; padding:8px 16px; font-size:14px; border:none; border-radius:5px;">➕ Add Expenses</button>'
                f'</a>',
                unsafe_allow_html=True
            )
    
        # ─────────────────────────────────────────────────────
        # 🔹 Preprocessing
        expense_df["Date"] = pd.to_datetime(expense_df["Date"], errors='coerce')
        expense_df["Year"] = expense_df["Date"].dt.year
        expense_df["Month"] = expense_df["Date"].dt.strftime('%B')
        expense_df["Month_Num"] = expense_df["Date"].dt.month
        expense_df["YearMonth"] = expense_df["Date"].dt.to_period("M").astype(str)
    
        # ─────────────────────────────────────────────────────
        # 🔹 Static Metrics (Not Filter Dependent)
        total_manual_expense = expense_df["Amount Used"].sum()
        total_bank_expense = govind_expense_debit + gaurav_expense_debit
        total_expense = total_manual_expense + total_bank_expense
    
        col1, col2, col3 = st.columns(3)
        col1.metric("🧾 Manual Entry Expense (Sheet)", f"₹{total_manual_expense:,.0f}")
        col2.metric("🏦 Bank Debits (Govind + Gaurav)", f"₹{total_bank_expense:,.0f}")
        col3.metric("💰 Total Expense (Combined)", f"₹{total_expense:,.0f}")
    
        st.markdown("---")
    
        # ─────────────────────────────────────────────────────
        # 🔹 Filter: Expense By
        st.sidebar.markdown("### 🔍 Filter")
        expense_by_options = ["All"] + sorted(expense_df["Expense By"].dropna().unique().tolist())
        selected_expense_by = st.sidebar.selectbox("Expense By", expense_by_options)
        # ─────────────────────────────────────────────────────
        #edit by ayush
        st.sidebar.markdown("**📅 Filter By Date**")

        year_month_option = st.sidebar.selectbox(
            "",
            ["All", "Current Month", "Last 6 Months", "Current Year", "Custom Date"],
            key="exp_range_select",
        )

        custom_start_date, custom_end_date = None, None
        if year_month_option == "Custom Date":
            min_date = date(2024, 1, 1)
            max_date = date.today()

            custom_start_date = st.sidebar.date_input(
                "Select Start Date",
                value=date.today(),
                min_value=min_date,
                max_value=max_date,
                key="exp_start_date_picker"
            )

            if custom_start_date < max_date:
                next_day = custom_start_date + timedelta(days=1)
                custom_end_date = st.sidebar.date_input(
                    "Select End Date",
                    value=next_day,
                    min_value=next_day,
                    max_value=max_date,
                    key="exp_end_date_picker"
                )

        today = pd.Timestamp.today().normalize()

    
        # ─────────────────────────────────────────────────────
        # 🔹 Apply expense by Filter
        if selected_expense_by == "All":
            filtered_df = expense_df.copy()
        else:
            filtered_df = expense_df[expense_df["Expense By"] == selected_expense_by]

        #apply date filter
        if year_month_option == "Current Month":
            start_date = today.replace(day=1)
            filtered_df = filtered_df[filtered_df["Date"] >= start_date]
        elif year_month_option == "Last 6 Months":
            start_date = today - pd.DateOffset(months=6)
            filtered_df = filtered_df[filtered_df["Date"] >= start_date]
        elif year_month_option == "Current Year":
            start_date = today.replace(month=1, day=1)
            filtered_df = filtered_df[filtered_df["Date"] >= start_date]
        elif (year_month_option == "Custom Date" and isinstance(custom_start_date, date) and isinstance(custom_end_date, date)):
            filtered_df = filtered_df[
                (filtered_df["Date"].dt.date >= custom_start_date) & (filtered_df["Date"].dt.date <= custom_end_date)]

    
        # ─────────────────────────────────────────────────────
        # 🔹 Month-on-Month Summary (Last 12 Months)
        st.subheader("📊 Month-on-Month Expense (Last 12 Months)")
    
        recent_12_months = (
            expense_df["YearMonth"]
            .dropna()
            .sort_values()
            .unique()
        )[-12:]
    
        momo_df = (
            filtered_df[filtered_df["YearMonth"].isin(recent_12_months)]
            .groupby(["YearMonth", "Expense By"])["Amount Used"]
            .sum()
            .reset_index()
            .sort_values(by="YearMonth")
        )
    
        pivot_df = momo_df.pivot(index="YearMonth", columns="Expense By", values="Amount Used").fillna(0)
    
        st.bar_chart(pivot_df)

        # 🔹 Total of Filtered Data
        total_filtered_expense = filtered_df["Amount Used"].sum()
        st.metric("📌 Total Filtered Expense", f"₹{total_filtered_expense:,.0f}")




        # ─────────────────────────────────────────────────────
        # 🔹 View Filtered Table with Clickable Links
        st.subheader("📋 Filtered Expense Table")
        display_df = filtered_df.sort_values(by="Date", ascending=False).copy()
        if "Any Bill" in display_df.columns:
            url_mask = display_df["Any Bill"].astype(str).str.startswith("http")
            display_df.loc[~url_mask, "Any Bill"] = None  # hide non-URLs

        st.dataframe(
            display_df,
            use_container_width = True,
            height = 420,
            column_config={
                "Any Bill": st.column_config.LinkColumn("Any Bill", display_text="View Bill"),
                "Amount Used": st.column_config.NumberColumn("Amount Used", format="₹%d"),
                "Date": st.column_config.DateColumn("Date", format="YYYY-MM-DD"),
            },
            hide_index=False
        )



    
    elif page == "Investment":
        st.title("📈 Investment Details")
    
        # Add Investment Button (Top Right)
        col1, col2 = st.columns([6, 1])
        with col2:
            st.markdown(
                f'<a href="https://forms.gle/tse55G9Mp6CBqSmT9" target="_blank">'
                f'<button style="background-color:#4CAF50; color:white; padding:8px 16px; font-size:14px; border:none; border-radius:5px;">➕ Add Investment</button>'
                f'</a>',
                unsafe_allow_html=True
            )
    
        # --- 1. From Investment Sheet ---
        sheet_total_investment = investment_df["Investment Amount"].sum()
    
        # --- 2. From Bank Transactions ---
        bank_investment_df = bank_df[bank_df["Transaction Type"] == "Investment_Credit"].copy()
    
        # Rename for consistency
        bank_investment_df.rename(columns={
            "Transaction By": "Investor Name",
            "Amount": "Investment Amount",
            "Reason": "Comment"
        }, inplace=True)
    
        # Add source
        investment_df["Source"] = "Manual Sheet"
        bank_investment_df["Source"] = "Bank Transaction"
    
        # Clean and align columns
        investment_df_clean = investment_df[["Date", "Investor Name", "Investment Amount", "Investment Type", "Comment", "Month-Year", "Source"]]
        bank_investment_df_clean = bank_investment_df[["Date", "Investor Name", "Investment Amount", "Comment", "Source"]]
    
        bank_investment_df_clean["Investment Type"] = "Bank Credit"
        bank_investment_df_clean["Month-Year"] = pd.to_datetime(bank_investment_df_clean["Date"]).dt.strftime('%Y-%m')
    
        # Final order of bank data
        bank_investment_df_clean = bank_investment_df_clean[["Date", "Investor Name", "Investment Amount", "Investment Type", "Comment", "Month-Year", "Source"]]
    
        # Combine both
        full_investment_df = pd.concat([investment_df_clean, bank_investment_df_clean], ignore_index=True)
    
        # --- Total Summary ---
        total_combined_investment = full_investment_df["Investment Amount"].sum()
    
        col1, col2, col3 = st.columns(3)
        col1.metric("📄 From Sheet", f"₹{sheet_total_investment:,.0f}")
        col2.metric("🏦 From Bank", f"₹{bank_investment_df['Investment Amount'].sum():,.0f}")
        col3.metric("💰 Total Investment", f"₹{total_combined_investment:,.0f}")
    
        st.markdown("---")
    
        # --- 📊 Split Charts in Equal Bordered Columns ---
        col1, col2 = st.columns(2)
    
        with col1:
            st.markdown("#### 👥 Investment Share (Govind vs Gaurav)")
            pie_df = full_investment_df[full_investment_df["Investor Name"].isin(["Govind Kumar", "Kumar Gaurav"])]
            investor_totals = pie_df.groupby("Investor Name", as_index=False)["Investment Amount"].sum()
    
            if not investor_totals.empty:
                fig1, ax1 = plt.subplots(figsize=(3.5, 3.5))
                ax1.pie(
                    investor_totals["Investment Amount"],
                    labels=investor_totals["Investor Name"],
                    autopct='%1.1f%%',
                    startangle=90,
                    colors=plt.cm.Pastel1.colors
                )
                ax1.axis("equal")
                st.pyplot(fig1)
            else:
                st.info("No investment data available for Govind or Gaurav.")
    
        with col2:
            st.markdown("#### 🧾 Manual vs Bank Investment by Investor")
            manual_df = investment_df_clean[investment_df_clean["Investor Name"].isin(["Govind Kumar", "Kumar Gaurav"])]
            bank_df_investor = bank_investment_df_clean[bank_investment_df_clean["Investor Name"].isin(["Govind Kumar", "Kumar Gaurav"])]
    
            manual_summary = manual_df.groupby("Investor Name")["Investment Amount"].sum().rename("Manual Sheet")
            bank_summary = bank_df_investor.groupby("Investor Name")["Investment Amount"].sum().rename("Bank Transaction")
    
            comparison_df = pd.concat([manual_summary, bank_summary], axis=1).fillna(0)
            st.bar_chart(comparison_df)
    
        st.markdown("---")
    
        # --- 🎯 Investor Filter + Summary ---
        st.sidebar.markdown("### 🔎 Filter Investment Records by Investor")
    
        # Unique investor names
        investors_list = full_investment_df["Investor Name"].dropna().unique().tolist()
        investors_list.sort()
        investors_list.insert(0, "All")
    
        selected_investor = st.sidebar.selectbox("Select Investor", investors_list)
    
        # Filter data
        if selected_investor != "All":
            filtered_df = full_investment_df[full_investment_df["Investor Name"] == selected_investor]
        else:
            filtered_df = full_investment_df
    
        # --- 💼 Total Investment by Each Investor ---
        st.markdown("#### 💼 Total Investment by Each Investor")
    
        summary_by_investor = full_investment_df.groupby("Investor Name")["Investment Amount"].sum().reset_index()
        summary_by_investor.columns = ["Investor Name", "Total Investment (₹)"]
        summary_by_investor["Total Investment (₹)"] = summary_by_investor["Total Investment (₹)"].apply(lambda x: f"₹{x:,.0f}")
    
        st.dataframe(summary_by_investor)
        st.markdown("---")
    
        # --- 📋 Final Investment Table ---
        if "Date" in filtered_df.columns:
            filtered_df["Date"] = pd.to_datetime(filtered_df["Date"], dayfirst=True, errors="coerce")
            filtered_df = filtered_df.dropna(subset=["Date"])
            filtered_df = filtered_df.sort_values(by="Date", ascending=False)
    
            st.subheader("📋 All Investment Records")
            st.dataframe(filtered_df)
        else:
            st.warning("⚠️ 'Date' column not found in investment data.")


    
    elif page == "Collection Data":
        st.title("📊 Collection Data")

        # Add Collection Button (Top Right)
        col1, col2 = st.columns([6, 1])
        with col2:
            st.markdown(
                f'<a href="https://forms.gle/ZyvCBLFaPC1szPGd7" target="_blank">'
                f'<button style="background-color:#4CAF50; color:white; padding:8px 16px; font-size:14px; border:none; border-radius:5px;">➕ Add Collection</button>'
                f'</a>',
                unsafe_allow_html=True
            )
    
        # Ensure date column is in datetime format
        df["Collection Date"] = pd.to_datetime(df["Collection Date"])
    
        # Sort by Collection Date descending
        df = df.sort_values("Collection Date", ascending=False)
    
        # Calculate previous amount per vehicle
        df = df.sort_values(["Vehicle No", "Collection Date"])
        df["Previous Amount"] = df.groupby("Vehicle No")["Amount"].shift(1)
        df["Change"] = df["Amount"] - df["Previous Amount"]
    
        # KPIs based on all data
        total_collection = df["Amount"].sum()
        total_vehicles = df["Vehicle No"].nunique()
        best_vehicle = df.groupby("Vehicle No")["Amount"].mean().idxmax()
        worst_vehicle = df.groupby("Vehicle No")["Amount"].mean().idxmin()
    
        # Show KPI Metrics
        col1, col2, col3, col4, col5 = st.columns(5)
        col1.metric("💰 Total Collection", f"₹{total_collection:,.0f}")
        col2.metric("🚐 Total Vehicles", total_vehicles)
        col3.metric("🏆 Best Vehicle", best_vehicle)
        col4.metric("📉 Worst Vehicle", worst_vehicle)
        col5.metric("📄 Total Records", len(df))
    
        st.markdown("---")
    
    # edit by ayush starts
        # Vehicle filter
        st.sidebar.markdown("### 🚗 Filter by Vehicle")
        #vehicle_list = ["All"] + sorted(df["Vehicle No"].unique())
        #selected_vehicle = st.sidebar.selectbox("###🚗 Filter by Vehicle", vehicle_list)
        selected_vehicle = st.sidebar.selectbox("", ["All"] + sorted(df["Vehicle No"].unique()),key = "vehicle_select",)
    

        # ensure date column is datetime
        df["Collection Date"] = pd.to_datetime(df["Collection Date"], dayfirst=True, errors="coerce")
        #custom date
        # apply vehicle filter
        if selected_vehicle != "All":
            filtered_df = df[df["Vehicle No"] == selected_vehicle].copy()
        else:
            filtered_df = df.copy()

        #custom_year, custom_month = None, None
        st.sidebar.markdown("### 📅 Filter by Date")
        year_month_option = st.sidebar.selectbox(
            "",
            ["All", "Current Month", "Last 6 Months", "Current Year", "Custom Date"],
            key="range_select",
        )

        custom_start_date, custom_end_date = None, None
        if year_month_option == "Custom Date":
            min_date = date(2024, 1, 1)
            max_date = date.today()
            #all_dates = sorted(filtered_df["Collection Date"].dt.date.dropna().unique().tolist())
            #custom_start_date = st.sidebar.selectbox("Select Start Date" , [None] + all_dates,format_func=lambda d: "— Select start date —" if d is None else d.strftime("%d %b %Y"), key="start_date_select", index=0,)
            #possible_end_dates = [d for d in all_dates if d > custom_start_date]
            #years = sorted(pd.to_datetime(df["Collection Date"]).dt.year.unique())
            #months = list(range(1,13))
            #custom_year = st.sidebar.selectbox("Select Year", years)
            #custom_month = st.sidebar.selectbox("Select Month", months, format_func=lambda x: pd.to_datetime(str(x), format='%m').strftime('%B'))
            custom_start_date = st.sidebar.date_input(
                "Select Start Date",
                value=date.today(),
                min_value=min_date,
                max_value=max_date,
                key="start_date_picker"
            )

            if custom_start_date<max_date:
                next_day = custom_start_date + timedelta(days=1)
                custom_end_date = st.sidebar.date_input(
                    "Select End Date",
                    value=next_day,
                    min_value=next_day,
                    max_value=max_date,
                    key="end_date_picker"
                )


        today = pd.Timestamp.today().normalize()
        # apply year-month filter
        if year_month_option == "Current Month":
            start_date = today.replace(day=1)
            filtered_df = filtered_df[filtered_df["Collection Date"] >= start_date]
        elif year_month_option == "Last 6 Months":
            start_date = today - pd.DateOffset(months=6)
            filtered_df = filtered_df[filtered_df["Collection Date"] >= start_date]
        elif year_month_option == "Current Year":
            start_date = today.replace(month=1, day=1)
            filtered_df = filtered_df[filtered_df["Collection Date"] >= start_date]
        elif (year_month_option == "Custom Date" and isinstance(custom_start_date, date) and isinstance(custom_end_date, date)):
            filtered_df = filtered_df[
                (filtered_df["Collection Date"].dt.date >= custom_start_date)&
                (filtered_df["Collection Date"].dt.date <= custom_end_date)
            ]
        

        
    ## edit by ayush ends
    
        st.markdown("### 📈 Collection Trend")
    
        # Line chart with time range filter
        chart_df = df.groupby(["Collection Date", "Vehicle No"])["Amount"].sum().reset_index()
        chart_df["Collection Date"] = pd.to_datetime(chart_df["Collection Date"])
        
        
        # === RADIO BUTTONS CENTERED BELOW CHART WITHOUT LABEL ===
        col1, col2, col3 = st.columns([1, 3, 1])
        with col2:
            range_option = st.radio(
                "",  # Remove label
                ["1 Week", "1 Month", "3 Months", "6 Months", "1 Year", "3 Years", "5 Years", "Max"],
                horizontal=True,
                index=2
            )
        
        # === FILTER BASED ON SELECTION ===
        today = pd.to_datetime("today")
        if range_option == "1 Week":
            start_date = today - pd.Timedelta(weeks=1)
        elif range_option == "1 Month":
            start_date = today - pd.DateOffset(months=1)
        elif range_option == "3 Months":
            start_date = today - pd.DateOffset(months=3)
        elif range_option == "6 Months":
            start_date = today - pd.DateOffset(months=6)
        elif range_option == "1 Year":
            start_date = today - pd.DateOffset(years=1)
        elif range_option == "3 Years":
            start_date = today - pd.DateOffset(years=3)
        elif range_option == "5 Years":
            start_date = today - pd.DateOffset(years=5)
        else:
            start_date = chart_df["Collection Date"].min()
        
        # Apply the filter
        filtered_chart_df = chart_df[chart_df["Collection Date"] >= start_date]
        filtered_pivot = filtered_chart_df.pivot(index="Collection Date", columns="Vehicle No", values="Amount").fillna(0)
        
        # Rerender chart with filtered data
        st.line_chart(filtered_pivot)
## edit by ayush starts

        
        collection_amount = filtered_df["Amount"].sum()
        selected_vehicle_display= selected_vehicle if selected_vehicle != "All" else "All Vehicles"

        monthly_totals = filtered_df.groupby(pd.to_datetime(filtered_df["Collection Date"]).dt.to_period("M"))["Amount"].sum()
        best_month = monthly_totals.idxmax().strftime('%B %Y') if not monthly_totals.empty else "N/A"
        worst_month = monthly_totals.idxmin().strftime('%B %Y') if not monthly_totals.empty else "N/A"

        col1, col2 = st.columns(2)
        col1.metric("🚐 Selected Vehicle", selected_vehicle_display)
        col2.metric("💰 Collection Amount", f"₹{collection_amount:,.0f}")
        

        st.markdown("---")
### edit by ayush ends
        
        st.markdown("### 📄 Collection Records")
    
        # Columns to show
        display_cols = ["Collection Date", "Vehicle No", "Amount", "Meter Reading", "Name", "Distance"]
    
        # Round distance
        df["Distance"] = df["Distance"].round(2)

        Daily_Collection = (
            filtered_df.copy()
            .assign(**{"Collection Date": lambda x: pd.to_datetime(x["Collection Date"])})
            .sort_values("Collection Date", ascending=False)
        )

        # Format for display
        Daily_Collection["Collection Date"] = Daily_Collection["Collection Date"].dt.strftime("%d %b %Y")

        for index, row in Daily_Collection.iterrows():
            bg_style = get_background_style(row['Amount'])
            
            html_content += f"""
            <div class="card" style="background: {bg_style}">
                <div class="vehicle-no">{row['Vehicle No']}</div>
                <hr style="border-top: 2px solid #000; margin-top: 5px; margin-bottom: 5px;">
                <div class="card-header">
                    <div class="date">{row['Collection Date']}</div>
                    <div class="meter-reading-header">{row['Meter Reading']} Km</div>
                </div>
                <div class="info-row">
                    <div class="info-left">
                        <div class="info-value">₹ {row['Amount']}</div>
                        <div class="info-value">{row['Distance']} km</div>
                    </div>
                    <div class="info-right">
                        <div class="info-value name">{row['Name']}</div>
                    </div>
                </div>
            </div>
            """
        html_content += "</div>"

        # Render HTML
        components.html(html_content, height=600, scrolling=True)


    elif page == "Bank Transaction":
        st.title("🏦 Bank Transactions")
    
        # Add Transaction Button (Top Right)
        col1, col2 = st.columns([6, 1])
        with col2:
            st.markdown(
                f'<a href="https://forms.gle/JwXMNkREnjeqAfNPA" target="_blank">'
                f'<button style="background-color:#4CAF50; color:white; padding:8px 16px; font-size:14px; border:none; border-radius:5px;">➕ Add Bank Transaction</button>'
                f'</a>',
                unsafe_allow_html=True
            )
    
        # Ensure 'Date' is datetime
        bank_df["Date"] = pd.to_datetime(bank_df["Date"], dayfirst=True, errors="coerce")
        bank_df["Transaction Type"] = bank_df["Transaction Type"].str.strip()
        bank_df["Month"] = bank_df["Date"].dt.strftime("%B")
        bank_df["Year"] = bank_df["Date"].dt.year
    
        # 🔒 Full data copy for current balance
        full_df = bank_df.copy()
    
        # Total balance from full data (not filtered)
        credit_mask_full = full_df["Transaction Type"].str.lower().str.contains("credit", na=False)
        debit_mask_full = full_df["Transaction Type"].str.lower().str.contains("debit", na=False)
    
        total_credit = full_df.loc[credit_mask_full, "Amount"].sum()
        total_debit = full_df.loc[debit_mask_full, "Amount"].sum()
        balance = total_credit - total_debit
    
        # 📌 Sidebar Filters
        st.sidebar.header("📅 Filter Transactions")
    
    ## edit by ayush
        filtered_df = bank_df.copy()
        filter_option = st.sidebar.selectbox("Choose filter type:", ["All", "Last 3 Months", "Select Date"],key="range_select",)

        start_date, end_date = None, None
        if filter_option == "Select Date":
            min_date= date(2025, 1, 1)
            max_date= date.today()
            start_date= st.sidebar.date_input(
                "Select Start Date",
                value = date.today(),
                min_value= min_date,
                max_value= max_date,
                key="start_date_picker"
            )
            if start_date < max_date:
                next_day= start_date + timedelta(days=1)
                end_date = st.sidebar.date_input(
                    "Select End Date",
                    value=next_day,
                    min_value=next_day,
                    max_value=max_date,
                    key="end_date_picker"
                )
        today = pd.Timestamp.today().normalize()


        if filter_option == "All":
            filtered_df = bank_df
        elif filter_option == "Last 3 Months":
            last_3_months = pd.Timestamp.today() - pd.DateOffset(months=3)
            filtered_df = bank_df[bank_df["Date"] >= last_3_months]
        elif filter_option == "Select Date" and isinstance(start_date, date) and isinstance(end_date, date):
            #selected_year = st.sidebar.selectbox("Year", sorted(bank_df["Year"].unique(), reverse=True))
            #selected_month = st.sidebar.selectbox("Month", sorted(bank_df["Month"].unique(), key=lambda x: pd.to_datetime(x, format="%B").month))
            date_filtered = bank_df[
                (bank_df["Date"].dt.date >= start_date) &
                (bank_df["Date"].dt.date <= end_date)
            ]
            filtered_df = date_filtered.copy()
    ## edit by ayush

        # 💰 Current Balance (Always from full data)
        st.subheader("💰 Current Bank Balance")
        st.metric(label="Available Balance", value=f"₹ {balance:,.0f}", delta=f"₹ {total_credit - total_debit:,.0f}")
    
        # 📌 Closing Balance of Filtered Data
        st.subheader("📉 Closing Balance for Selected Period")
        credit_mask = filtered_df["Transaction Type"].str.lower().str.contains("credit", na=False)
        debit_mask = filtered_df["Transaction Type"].str.lower().str.contains("debit", na=False)
        closing_credit = filtered_df.loc[credit_mask, "Amount"].sum()
        closing_debit = filtered_df.loc[debit_mask, "Amount"].sum()
        closing_balance = closing_credit - closing_debit
        st.metric(label="Closing Balance (Filtered)", value=f"₹ {closing_balance:,.0f}")
    
        # 📊 Monthly Summary (From filtered data)
        st.subheader("📊 Monthly Transaction Summary")
        monthly_summary = (
            filtered_df.groupby(["Month", "Transaction Type"])["Amount"]
            .sum()
            .unstack(fill_value=0)
            .reset_index()
        )
        st.dataframe(monthly_summary)
    
        # 📋 Full Transaction Log
        st.subheader("📋 Full Bank Transaction Log")
    
        display_df = filtered_df[["Date", "Transaction By", "Transaction Type", "Reason", "Amount", "Bill"]].copy()


        #def format_amount(row):
        #    amt = row["Amount"]
        #    if "credit" in row["Transaction Type"].lower():
        #        return f"+₹{amt:,.0f}"
        #    elif "debit" in row["Transaction Type"].lower():
        #        return f"-₹{amt:,.0f}"
        #    return f"₹{amt:,.0f}"
        #display_df["Amount"] = filtered_df.apply(format_amount, axis=1)

        def format_amount(row):
            amt = pd.to_numeric(row.get("Amount", 0), errors="coerce")
            if pd.isna(amt):
                amt = 0
            t = str(row.get("Transaction Type", "")).lower()
            if "credit" in t:
                return f"+₹{amt:,.0f}"
            elif "debit" in t:
                return f"-₹{amt:,.0f}"
            return f"₹{amt:,.0f}"
        
    

        if not display_df.empty:
            display_df["Amount"] = display_df.apply(format_amount, axis=1)
        else:
            display_df["Amount"] = pd.Series(dtype="object")
        
        if "Bill" in display_df.columns:
            display_df["Bill"] = display_df["Bill"].apply(
                lambda x: f'<a href="{x}" target="_blank">View Bill</a>' if pd.notna(x) and str(x).startswith("http") else ""
            )
    
        def color_amount(val):
            if isinstance(val, str):
                if val.startswith("+"):
                    return "color: green"
                elif val.startswith("-"):
                    return "color: red"
            return ""
    
        styled = display_df[["Date", "Transaction By", "Transaction Type", "Reason", "Amount", "Bill"]].sort_values(by="Date", ascending=False)
        styled_df = styled.style.applymap(color_amount, subset=["Amount"])

    
        # 💡 Full Width Styling for Table
        st.markdown(
            """
            <style>
                .full-width-table {
                    width: 100%;
                    overflow-x: auto;
                }
            </style>
            """,
            unsafe_allow_html=True
        )
    
        # ✅ Render styled DataFrame with clickable links and full width
        st.markdown(
            f'<div class="full-width-table">{styled_df.to_html(escape=False, index=False)}</div>',
            unsafe_allow_html=True
        )
    
        # ⬇️ Export Filtered Data
        st.download_button(
            label="📥 Download Filtered Transactions as CSV",
            data=filtered_df.to_csv(index=False),
            file_name="filtered_bank_transactions.csv",
            mime="text/csv"
        )

    

    elif page == "Performance":
        st.title("📉 Performance Analysis")

        if "Amount" not in perf_df_lm.columns:
            perf_df_lm["Amount"] = pd.Series(dtype=float)
        
        #filtered_df_lm = apply_loss_matrix_logic(filtered_df)
    # ---------- Vehicle , Driver Filter ----------
        st.sidebar.markdown("### 🚗 Filter by Vehicle")
        selected_vehicle = st.sidebar.selectbox(
            "",
            ["All"] + sorted(perf_df["Vehicle No"].dropna().astype(str).unique()),
            key="Vehicle_select"
        )

        st.sidebar.markdown("### 👨‍✈️ Filter by Driver")
        selected_driver = st.sidebar.selectbox(
            "",
            ["All"] + sorted(perf_df["Name"].dropna().astype(str).unique()),
            key="Driver_select"
        )

        filtered_df_lm = perf_df_lm.copy()
        if selected_vehicle != "All":
            filtered_df_lm = filtered_df_lm[filtered_df_lm["Vehicle No"] == selected_vehicle]
        if selected_driver != "All":
            filtered_df_lm = filtered_df_lm[filtered_df_lm["Name"] == selected_driver]

    # ----------  Date Filter ----------
        st.sidebar.markdown("### 📅 Filter by Date")
        year_month_option = st.sidebar.selectbox(
            "",
            ["All", "Current Month", "Last 6 Months", "Current Year", "Custom Date"],
            key="range_select",
        )
        
        start_date, end_date = None, None
        custom_start_date, custom_end_date = None, None

        if year_month_option == "All":
            pass
        elif year_month_option == "Current Month":
            start_date = today.replace(day=1)
            end_date = today
        elif year_month_option == "Last 6 Months":
            start_date = today - pd.DateOffset(months=6)
            end_date = today
        elif year_month_option == "Current Year":
            start_date = today.replace(month=1, day=1)
            end_date = today

        if year_month_option == "Custom Date":
            min_date = date(2024, 1, 1)
            max_date = date.today()
            custom_start_date = st.sidebar.date_input(
                "Select start Date",
                value=date.today(),
                min_value=min_date,
                max_value=max_date,
                key="start_date_picker"
            )
            default_end_date = custom_start_date
            if custom_start_date < max_date:
                default_end_date = min(custom_start_date + timedelta(days=1), max_date)
            custom_end_date = st.sidebar.date_input(
                "Select End Date",
                value=default_end_date,
                min_value=custom_start_date,
                max_value=max_date,
                key="end_date_picker"
            )
            start_date = pd.Timestamp(custom_start_date)
            end_date = pd.Timestamp(custom_end_date)

        if start_date is not None and end_date is not None:
            filtered_df_lm = filtered_df_lm[
                (filtered_df_lm["Collection Date"] >= start_date) &
                (filtered_df_lm["Collection Date"] <= end_date)
            ]

    # ---------- Calculate losses ----------
        all_total_loss = perf_df_lm["Amount"].sum()
        all_company_loss = perf_df_lm.loc[perf_df_lm["Name"] == "Zero Collection", "Amount"].sum()
        all_driver_loss = all_total_loss - all_company_loss

        f_total_loss = filtered_df_lm["Amount"].sum() if "Amount" in filtered_df_lm.columns else 0
        f_company_loss = filtered_df_lm.loc[filtered_df_lm.get("Name") == "Zero Collection", "Amount"].sum() if "Amount" in filtered_df_lm.columns else 0
        f_driver_loss = f_total_loss - f_company_loss



        #current_total_loss, current_driver_loss, current_company_loss = calculate_current_month_losses(perf_df_lm)


    # ---------- Metrics ----------
        col0, col1, col2 = st.columns(3)
        col0.metric("All-time Total Loss", f"{all_total_loss:,.0f}")
        col1.metric("All-time Driver Loss", f"{all_driver_loss:,.0f}")
        col2.metric("All-time Company Loss", f"{all_company_loss:,.0f}")

        st.markdown("---")
        col0, col1, col2 = st.columns(3)
        col0.metric("Filtered Total Loss", f"{f_total_loss:,.0f}")
        col1.metric("Filtered Driver Loss", f"{f_driver_loss:,.0f}")
        col2.metric("Filtered Company Loss", f"{f_company_loss:,.0f}")

    # ---------- Table ----------
        st.subheader("📉 Loss Matrix (Filtered)")
        if filtered_df_lm.empty:
            st.info("No records in this period.")
        else:
            st.dataframe(
                filtered_df_lm.sort_values(by="Collection Date", ascending=False),
                use_container_width=True
            )


    
    # 🔁 Refresh button
    if st.sidebar.button("🔁 Refresh"):
        st.cache_resource.clear()
        st.experimental_rerun()
