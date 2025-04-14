
import streamlit as st
import pandas as pd
import pdfplumber
import re

st.set_page_config(page_title="AIBooks – Universal Reconciliation Assistant")

st.title("AIBooks – Universal Reconciliation Assistant")
st.markdown("Created by Aigerim Bekturganova")

st.write("Upload your QuickBooks Bank Register and Bank Statement (CSV or PDF). AIBooks will extract date, description, debit, credit, and calculate net amounts to detect mismatches.")

def extract_transactions_from_pdf(file, label):
    transactions = []
    patterns = [
        re.compile(r"(\d{2}/\d{2}/\d{2})\s+(.+?)\s+(-?\$?[\d,]+\.\d{2})?\s+(-?\$?[\d,]+\.\d{2})?")
    ]
    with pdfplumber.open(file) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if not text:
                continue
            lines = text.split("\n")
            for line in lines:
                for pattern in patterns:
                    match = pattern.search(line)
                    if match:
                        date = match.group(1)
                        description = match.group(2).strip()
                        debit = match.group(3)
                        credit = match.group(4)
                        try:
                            debit_val = float(debit.replace("$", "").replace(",", "")) if debit else 0.0
                            credit_val = float(credit.replace("$", "").replace(",", "")) if credit else 0.0
                            amount = credit_val - debit_val
                            transactions.append({
                                "Source": label,
                                "Date": date,
                                "Description": description,
                                "Debit": debit_val,
                                "Credit": credit_val,
                                "Amount": amount
                            })
                        except ValueError:
                            continue
    return pd.DataFrame(transactions)

def load_file(file, label):
    if file.name.endswith(".csv"):
        df = pd.read_csv(file)
        df["Source"] = label
        if "Amount" not in df.columns:
            df["Amount"] = df.get("Credit", 0) - df.get("Debit", 0)
        return df
    elif file.name.endswith(".pdf"):
        return extract_transactions_from_pdf(file, label)
    else:
        return pd.DataFrame()

register_file = st.file_uploader("Upload Bank Register (CSV or PDF)", type=["csv", "pdf"])
statement_file = st.file_uploader("Upload Bank Statement (CSV or PDF)", type=["csv", "pdf"])

if register_file and statement_file:
    reg_df = load_file(register_file, "Register")
    stmt_df = load_file(statement_file, "Statement")

    if reg_df.empty or stmt_df.empty:
        st.error("One of the files could not be read or does not contain recognizable transactions.")
    else:
        # Merge on Description and Amount
        merged_df = pd.merge(reg_df, stmt_df, on=["Description", "Amount"], how="outer", suffixes=("_reg", "_stmt"), indicator=True)
        matched = merged_df[merged_df["_merge"] == "both"]
        only_in_register = merged_df[merged_df["_merge"] == "left_only"]
        only_in_statement = merged_df[merged_df["_merge"] == "right_only"]

        st.subheader("Reconciliation Summary")
        st.write(f"✔️ Matched transactions: {len(matched)}")
        st.write(f"❌ Missing in Statement: {len(only_in_register)}")
        st.write(f"❌ Missing in Register: {len(only_in_statement)}")

        st.subheader("AI Summary")
        st.text(f"""AIBooks Reconciliation Summary:
- {len(matched)} matched transactions found.
- {len(only_in_statement)} entries are in the bank statement but missing in the register.
- {len(only_in_register)} entries are in the register but missing from the statement.
""")

        if not only_in_register.empty:
            st.subheader("Transactions Only in Register")
            st.dataframe(only_in_register)

        if not only_in_statement.empty:
            st.subheader("Transactions Only in Statement")
            st.dataframe(only_in_statement)
else:
    st.info("Please upload both files to begin reconciliation.")
