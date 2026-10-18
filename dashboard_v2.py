"""
Streamlit Analyst Dashboard v2 (Human-in-the-Loop Workbench)
Reads from predictions_log.csv and allows analysts to label cases for retraining.
"""
import streamlit as st
import pandas as pd
import os
from datetime import datetime

st.set_page_config(page_title="Fraud Analyst Workbench", layout="wide")

PREDICTIONS_LOG = "predictions_log.csv"
FEEDBACK_LOG = "feedback_log.csv"
DRIFT_REPORT = "reports/drift_report.html"

# Ensure feedback log exists
if not os.path.exists(FEEDBACK_LOG):
    pd.DataFrame(columns=["transaction_id", "timestamp", "amount", "risk_level", "ml_score", "analyst_label", "reviewed_at"]).to_csv(FEEDBACK_LOG, index=False)

st.title("🛡️ Fraud Analyst Workbench (Human-in-the-Loop)")
st.markdown("Review high-risk alerts and provide feedback. Your labels will be saved to retrain the model.")

# --- Sidebar: System Health & Drift ---
st.sidebar.header("📊 System Status")
if os.path.exists(PREDICTIONS_LOG):
    df = pd.read_csv(PREDICTIONS_LOG)
    df = df.sort_values(by='timestamp', ascending=False)
    st.sidebar.metric("Total Transactions Logged", len(df))
    high_risk_count = len(df[df['risk_level'] == 'HIGH'])
    st.sidebar.metric("🚨 High Risk Alerts", high_risk_count)
else:
    st.sidebar.warning("No predictions log found. Run the Kafka consumer first.")
    df = pd.DataFrame()

# Link to the drift report
if os.path.exists(DRIFT_REPORT):
    with open(DRIFT_REPORT, "rb") as f:
        st.sidebar.download_button("📥 Download Latest Drift Report (HTML)", f, file_name="drift_report.html")
else:
    st.sidebar.info("Run drift_monitor.py to generate a report.")

# --- Main Area: Alerts Queue ---
st.header("🚨 High-Risk Alerts Queue")
if not df.empty:
    high_risk_df = df[df['risk_level'] == 'HIGH']
    if high_risk_df.empty:
        st.success("✅ No high-risk alerts at the moment. All clear!")
    else:
        st.dataframe(high_risk_df[['timestamp', 'transaction_id', 'amount', 'ml_score', 'risk_level']], use_container_width=True)
else:
    st.info("Waiting for transactions...")

# --- Human-in-the-Loop: Case Review ---
st.markdown("---")
st.header("👨‍⚖️ Case Review & Feedback")
st.markdown("Select a transaction to review. Your labels will be saved to `feedback_log.csv` for future model retraining.")

if not df.empty:
    txn_options = df['transaction_id'].tolist()
    selected_txn = st.selectbox("Select Transaction ID to Review:", txn_options)
    
    if selected_txn:
        case = df[df['transaction_id'] == selected_txn].iloc[0]
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Amount", f"${case['amount']}")
        col2.metric("ML Score", f"{case.get('ml_score', 'N/A')}")
        col3.metric("System Risk", case['risk_level'])
        
        st.markdown("### Analyst Decision")
        label = st.radio("What is your final verdict?", ["CONFIRMED_FRAUD", "FALSE_POSITIVE", "PENDING_REVIEW"])
        
        if st.button("💾 Submit Feedback"):
            feedback_df = pd.read_csv(FEEDBACK_LOG)
            new_row = {
                "transaction_id": case['transaction_id'],
                "timestamp": case['timestamp'],
                "amount": case['amount'],
                "risk_level": case['risk_level'],
                "ml_score": case.get('ml_score', 0),
                "analyst_label": label,
                "reviewed_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            feedback_df = pd.concat([feedback_df, pd.DataFrame([new_row])], ignore_index=True)
            feedback_df.to_csv(FEEDBACK_LOG, index=False)
            
            st.success(f"✅ Feedback saved! Transaction {selected_txn} marked as {label}. This data is now queued for the next retraining cycle.")
            
            st.markdown("### 📈 Recent Analyst Feedback")
            st.dataframe(feedback_df.tail(5), use_container_width=True)