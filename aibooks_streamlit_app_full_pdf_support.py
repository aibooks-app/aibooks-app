
import streamlit as st
import pandas as pd
import pdfplumber
import re

st.set_page_config(page_title="AIBooks - QBO Reconciliation Assistant")

st.title("AIBooks – Reconciliation Assistant for QuickBooks Online")
st.markdown("Created by Aigerim Bekturganova")

st.write(
    "Upload your QuickBooks Bank Register and your Bank Statement (CSV or PDF). "
    "AIBooks will compare them and highlight unmatched or mismatched transactions."
)

def extract_pdf_text(pdf_file):
    with pdfplumber.open(pdf_file) as pdf:
        text = ""
        for page in pdf.pages:
            if page.extract_text():
                text += page.extract_text() + "\n"
    return text

def parse_pdf_transactions(text):
    transactions = []
    line_pattern = re.compile(r"(\d{2}/\d{2}/\d{2})\s+(.+?)\s+(-?\$?\d{1,3}(?:,\d{3})*(?:\.\d{2})?)$")
    for line in text.strip().split("\n"):
        match = line_pattern.search(line)
        if match:
            date = match.group(1)
            description = match.group(2).strip()
            amount_str = match.group(3).replace("$", "").replace(",", "")
            try:
                amount = float(amount_str)
                transactions.append({"Date": date, "Description": description, "Amount": amount})
            except ValueError:
                continue
    return pd.DataFrame(transactions)

# Upload section
qbo_file = st.file_uploader("Upload QuickBooks Bank Register (CSV or PDF)", type=["csv", "pdf"])
stmt_file = st.file_uploader("Upload Bank Statement (CSV or PDF)", type=["csv", "pdf"])

qbo_df, stmt_df = None, None

# Handle QBO file
if qbo_file:
    if qbo_file.name.endswith(".csv"):
        qbo_df = pd.read_csv(qbo_file)
    elif qbo_file.name.endswith(".pdf"):
        qbo_text = extract_pdf_text(qbo_file)
        qbo_df = parse_pdf_transactions(qbo_text)
else:
    st.info("No QBO file uploaded. Using sample data.")
    qbo_df = pd.DataFrame({
        "Date": ["2025-04-01", "2025-04-02", "2025-04-03", "2025-04-04"],
        "Description": ["Client Payment", "Office Supplies", "Software Subscription", "Client Payment"],
        "Amount": [500.00, -45.50, -100.00, 700.00]
    })

# Handle Bank Statement file
if stmt_file:
    if stmt_file.name.endswith(".csv"):
        stmt_df = pd.read_csv(stmt_file)
    elif stmt_file.name.endswith(".pdf"):
        stmt_text = extract_pdf_text(stmt_file)
        stmt_df = parse_pdf_transactions(stmt_text)
else:
    st.info("No bank statement uploaded. Using sample data.")
    stmt_df = pd.DataFrame({
        "Date": ["2025-04-01", "2025-04-02", "2025-04-03", "2025-04-05"],
        "Description": ["Client Payment", "Office Supplies", "Software Subscription", "Bank Fee"],
        "Amount": [500.00, -45.50, -90.00, -25.00]
    })

# Run reconciliation logic if both files are processed
if not {'Description', 'Amount'}.issubset(qbo_df.columns) or not {'Description', 'Amount'}.issubset(stmt_df.columns):
    st.error("One or both of the uploaded files are missing required columns ('Description', 'Amount').")
else:
    merged_df = pd.merge(qbo_df, stmt_df, on=["Description", "Amount"], how="outer", suffixes=('_qbo', '_stmt'), indicator=True)
    matched = merged_df[merged_df['_merge'] == 'both']
    missing_in_qbo = merged_df[merged_df['_merge'] == 'right_only']
    missing_in_stmt = merged_df[merged_df['_merge'] == 'left_only']

    amt_mismatch = pd.merge(qbo_df, stmt_df, on="Description", suffixes=('_qbo', '_stmt'))
    amt_mismatch = amt_mismatch[amt_mismatch['Amount_qbo'] != amt_mismatch['Amount_stmt']]

    st.subheader("Diagnostic Summary")
    st.write(f"✔️ {len(matched)} matched transactions")
    st.write(f"❌ {len(missing_in_qbo)} missing in QuickBooks")
    st.write(f"❌ {len(missing_in_stmt)} missing in Bank Statement")
    st.write(f"⚠️ {len(amt_mismatch)} amount mismatches for same description")

    st.subheader("AI Summary")
    st.text(f"""AIBooks Reconciliation Summary:
- {len(matched)} matched transactions found.
- {len(missing_in_qbo)} transactions are present in the bank statement but missing in QuickBooks.
- {len(missing_in_stmt)} transactions are in QuickBooks but not found in the bank statement.
- {len(amt_mismatch)} transactions have mismatched amounts for the same description.
""")

    if not matched.empty:
        st.subheader("Matched Transactions")
        st.dataframe(matched)
    if not missing_in_qbo.empty:
        st.subheader("Transactions Missing in QuickBooks")
        st.dataframe(missing_in_qbo)
    if not missing_in_stmt.empty:
        st.subheader("Transactions Missing in Bank Statement")
        st.dataframe(missing_in_stmt)
    if not amt_mismatch.empty:
        st.subheader("Amount Mismatches")
        st.dataframe(amt_mismatch)
