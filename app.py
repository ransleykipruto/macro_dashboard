
import streamlit as st

st.set_page_config(page_title="Macro Dashboard", page_icon="📊", layout="wide")

st.title("Macro Dashboard")
st.write("This is a simple version that should run without indentation errors.")

st.subheader("What it does")
st.markdown("""
- Shows a clean dashboard layout.
- Gives you a safe starting point.
- You can add your own data later.
""")

st.subheader("Status")
st.success("App is running.")
