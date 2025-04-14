
import streamlit as st
import pandas as pd
import pdfplumber
from io import StringIO

st.set_page_config(page_title="AIBooks - QBO Reconciliation Assistant")

st.title("AIBooks – Reconciliation Assistant for QuickBooks Online")
st.markdown("Created by Aigerim Bekturganova")

st.write(
    "Upload your QuickBooks Bank Register (CSV) and your Bank Statement (CSV or PDF). "
    "AIBooks will compare them and highlight unmatched or mismatched transactions."
)

def extract_pdf_text(pdf_file):
    with pdfplumber.open(pdf_file) as pdf:
        text = ""
        for page in pdf.pages:
            text += page.extract_text() + "\n"
    return text

def parse_pdf_statement(text):
    lines = text.strip().split("\n")
    data = []
    for line in lines:
        parts = line.strip().split()
        if len(parts) >= 3:
            try:
                date = parts[0]
                amount = float(parts[-1].replace(',', '').replace('$', ''))
                description = ' '.join(parts[1:-1])
                data.append({"Date": date, "Description": description, "Amount": amount})
            except ValueError:
                continue
    return pd.DataFrame(data)

# File upload section
qbo_file = st.file_uploader("Upload QuickBooks Bank Register (CSV)", type="csv")
stmt_file = st.file_uploader("Upload Bank Statement (CSV or PDF)", type=["csv", "pdf"])

qbo_df, stmt_df = None, None

if qbo_file:
    qbo_df = pd.read_csv(qbo_file)
else:
    st.info("No QBO file uploaded. Using sample data.")
    qbo_df = pd.DataFrame({
        "Date": ["2025-04-01", "2025-04-02", "2025-04-03", "2025-04-04"],
        "Description": ["Client Payment", "Office Supplies", "Software Subscription", "Client Payment"],
        "Amount": [500.00, -45.50, -100.00, 700.00]
    })

if stmt_file:
    if stmt_file.name.endswith(".csv"):
        stmt_df = pd.read_csv(stmt_file)
    elif stmt_file.name.endswith(".pdf"):
        text = extract_pdf_text(stmt_file)
        stmt_df = parse_pdf_statement(text)
else:
    st.info("No bank statement uploaded. Using sample data.")
    stmt_df = pd.DataFrame({
        "Date": ["2025-04-01", "2025-04-02", "2025-04-03", "2025-04-05"],
        "Description": ["Client Payment", "Office Supplies", "Software Subscription", "Bank Fee"],
        "Amount": [500.00, -45.50, -90.00, -25.00]
    })

# Merge to find perfect matches
merged_df = pd.merge(qbo_df, stmt_df, on=["Description", "Amount"], how="outer", suffixes=('_qbo', '_stmt'), indicator=True)
matched = merged_df[merged_df['_merge'] == 'both']
missing_in_qbo = merged_df[merged_df['_merge'] == 'right_only']
missing_in_stmt = merged_df[merged_df['_merge'] == 'left_only']

# Check for amount mismatches (same description)
amt_mismatch = pd.merge(qbo_df, stmt_df, on="Description", suffixes=('_qbo', '_stmt'))
amt_mismatch = amt_mismatch[amt_mismatch['Amount_qbo'] != amt_mismatch['Amount_stmt']]

# Display results
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
