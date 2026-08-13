import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, time

st.set_page_config(page_title="Company Attendance System", layout="centered")

# Google Sheet URL
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1GFPHFaY4YtXjOXVA4d5pEmgw-jPzJx-A885jroOPNqI/edit?usp=sharing"

# Connection Setup
conn = st.connection("gsheets", type=GSheetsConnection)

def load_employees():
    try:
        df = conn.read(spreadsheet=SPREADSHEET_URL, worksheet="employees", ttl=0)
        return df.dropna(how="all").astype(str)
    except Exception:
        return pd.DataFrame(columns=["emp_id", "name"])

def load_attendance():
    try:
        df = conn.read(spreadsheet=SPREADSHEET_URL, worksheet="attendance", ttl=0)
        return df.dropna(how="all").astype(str)
    except Exception:
        return pd.DataFrame(columns=["Date", "ID", "Name", "IN Time", "OUT Time", "Total Hours", "Status"])

LATE_CUTOFF = time(9, 30)

st.title("🏢 Company Attendance System")

tab1, tab2 = st.tabs(["🕒 Mark Attendance", "🔒 Admin Panel"])

# --- 1. ATTENDANCE SECTION ---
with tab1:
    st.subheader("Employee Attendance Log")
    emp_id = st.text_input("Enter Employee ID:", key="emp_input", placeholder="Type ID here...")
    
    if st.button("SUBMIT", type="primary", use_container_width=True):
        if not emp_id.strip():
            st.error("⚠️ Please enter Employee ID!")
        else:
            emp_df = load_employees()
            att_df = load_attendance()
            
            user = emp_df[emp_df['emp_id'].str.strip() == emp_id.strip()] if not emp_df.empty else pd.DataFrame()
            
            if user.empty:
                st.error("❌ Employee ID Not Found! Contact Admin.")
            else:
                emp_name = user.iloc[0]['name']
                today = datetime.now().strftime("%Y-%m-%d")
                now_dt = datetime.now()
                now_time_str = now_dt.strftime("%I:%M:%S %p")
                
                mask = (att_df['ID'].str.strip() == emp_id.strip()) & (att_df['Date'] == today) if not att_df.empty else []
                match = att_df[mask] if len(mask) > 0 else pd.DataFrame()
                
                if match.empty:
                    # 1st Submit: IN Time
                    status = "On Time" if now_dt.time() <= LATE_CUTOFF else "Late"
                    new_row = pd.DataFrame([{
                        "Date": today,
                        "ID": emp_id.strip(),
                        "Name": emp_name,
                        "IN Time": now_time_str,
                        "OUT Time": "",
                        "Total Hours": "",
                        "Status": status
                    }])
                    updated_att = pd.concat([att_df, new_row], ignore_index=True)
                    conn.update(spreadsheet=SPREADSHEET_URL, worksheet="attendance", data=updated_att)
                    st.success(f"✅ IN Time Recorded Successfully! Welcome {emp_name} ({status})")
                
                else:
                    idx = match.index[0]
                    current_out = str(att_df.at[idx, 'OUT Time'])
                    
                    if current_out in ["", "nan", "None", "<NA>"]:
                        # 2nd Submit: OUT Time
                        att_df.at[idx, 'OUT Time'] = now_time_str
                        
                        in_time_str = str(att_df.at[idx, 'IN Time'])
                        try:
                            in_dt = datetime.strptime(f"{today} {in_time_str}", "%Y-%m-%d %I:%M:%S %p")
                            diff = now_dt - in_dt
                            hrs = round(diff.total_seconds() / 3600, 2)
                            att_df.at[idx, 'Total Hours'] = f"{hrs} hrs"
                        except Exception:
                            att_df.at[idx, 'Total Hours'] = "-"
                            
                        conn.update(spreadsheet=SPREADSHEET_URL, worksheet="attendance", data=att_df)
                        st.success(f"👋 Out Time Recorded Successfully! Goodbye {emp_name}")
                    else:
                        # 3rd Submit: Already Completed
                        st.warning(f"⚠️ Today's Attendance Already Completed for {emp_name}!")

# --- 2. ADMIN PANEL SECTION ---
with tab2:
    st.subheader("Admin Login")
    admin_pass = st.text_input("Enter Admin Password:", type="password")
    
    if admin_pass == "admin123":
        st.success("🔓 Admin Access Granted!")
        
        st.markdown("---")
        st.subheader("➕ Add New Employee")
        new_id = st.text_input("New Employee ID:")
        new_name = st.text_input("New Employee Name:")
        
        if st.button("Add Employee"):
            if new_id.strip() and new_name.strip():
                emp_df = load_employees()
                if not emp_df.empty and new_id.strip() in emp_df['emp_id'].str.strip().values:
                    st.error("❌ Duplicate Employee ID! This ID already exists.")
                else:
                    new_emp = pd.DataFrame([{"emp_id": new_id.strip(), "name": new_name.strip()}])
                    updated_emp = pd.concat([emp_df, new_emp], ignore_index=True)
                    conn.update(spreadsheet=SPREADSHEET_URL, worksheet="employees", data=updated_emp)
                    st.success(f"✅ Employee '{new_name}' added successfully!")
            else:
                st.error("⚠️ Please fill both ID and Name!")
                
        st.markdown("---")
        st.subheader("🗑️ Delete Employee")
        emp_df = load_employees()
        if not emp_df.empty:
            emp_list = (emp_df['emp_id'] + " - " + emp_df['name']).tolist()
            del_item = st.selectbox("Select Employee to Delete:", emp_list)
            
            if st.button("Delete Employee"):
                selected_id = del_item.split(" - ")[0].strip()
                updated_emp = emp_df[emp_df['emp_id'].str.strip() != selected_id]
                conn.update(spreadsheet=SPREADSHEET_URL, worksheet="employees", data=updated_emp)
                st.success("✅ Employee deleted successfully!")
        else:
            st.info("No employees found in system.")
            
    elif admin_pass:
        st.error("❌ Incorrect Password!")
