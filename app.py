import os
import requests
import pandas as pd
import streamlit as st
from datetime import datetime
import plotly.graph_objects as go

st.set_page_config(page_title="Macro News Dashboard", layout="wide")

st.title("Macro News Dashboard")
st.caption("News + macro regime filter for Gold, Silver, AUDUSD, and AUDJPY")

GDELT_URL = "https://api.gdeltproject.org/api/v2/doc/doc"
FRED_BASE = "https://api.stlouisfed.org/fred/series/observations"

def fetch_news(query, maxrecords=10):
params = {
"query": query,
"mode": "ArtList",
"format": "json",
"maxrecords": maxrecords,
"sourcelang": "english",
"sort": "HybridRel",
}
try:
r = requests.get(GDELT_URL, params=params, timeout=20)
r.raise_for_status()
data = r.json()
return data.get("articles", [])
except Exception:
return []

def fetch_fred(series_id, api_key=None, limit=60):
params = {
"series_id": series_id,
"file_type": "json",
"sort_order": "desc",
"limit": limit,
}
if api_key:
params["api_key"] = api_key
try:
r = requests.get(FRED_BASE, params=params, timeout=20)
r.raise_for_status()
data = r.json().get("observations", [])
df = pd.DataFrame(data)
if df.empty:
return df
df["date"] = pd.to_datetime(df["date"])
df["value"] = pd.to_numeric(df["value"], errors="coerce")
return df.dropna(subset=["value"]).sort_values("date")
except Exception:
return pd.DataFrame()

@st.cache_data(ttl=900)
def pull_news():
queries = {
"Macro": "DXY OR dollar index OR VIX OR US500 OR S&P 500 OR real yields OR DFII5 OR Fed OR CPI OR NFP OR FOMC",
"Gold": "gold OR XAUUSD OR real yields OR DXY OR VIX OR geopolitics",
"Silver": "silver OR XAGUSD OR gold OR industrial demand OR real yields OR DXY",
"AUDUSD": "AUDUSD OR Australia OR RBA OR China OR risk sentiment OR DXY",
"AUDJPY": "AUDJPY OR Australia OR Japan OR BOJ OR Nikkei OR risk sentiment",
}
rows = []
for asset, q in queries.items():
for a in fetch_news(q, 8):
rows.append({
"asset": asset,
"title": a.get("title", ""),
"source": a.get("sourceCountry", ""),
"url": a.get("url", ""),
"seendate": a.get("seendate", "")
})
return pd.DataFrame(rows)

def score_text(text):
t = text.lower()
s = {"dxy":0, "real":0, "risk":0, "gold":0, "silver":0, "aud":0, "jpy":0, "impact":0}

for k in ["dollar stronger", "dxy up", "usd firm", "greenback rises", "dollar gains"]:
s["dxy"] += 1 if k in t else 0
for k in ["dollar weaker", "dxy down", "usd falls", "greenback slips", "dollar slides"]:
s["dxy"] -= 1 if k in t else 0

for k in ["real yields rise", "tips yield higher", "inflation-indexed yield higher", "real yields higher"]:
s["real"] += 1 if k in t else 0
for k in ["real yields fall", "tips yield lower", "inflation-indexed yield lower", "real yields lower"]:
s["real"] -= 1 if k in t else 0

for k in ["risk off", "fear gauge", "vix jumps", "stocks slide", "equity selloff", "flight to safety"]:
s["risk"] -= 1 if k in t else 0
for k in ["risk on", "vix slips", "stocks rally", "equities rally", "bullish sentiment"]:
s["risk"] += 1 if k in t else 0

for k in ["gold rises", "gold higher", "xauusd up", "safe haven demand"]:
s["gold"] += 1 if k in t else 0
for k in ["gold falls", "gold lower", "xauusd down"]:
s["gold"] -= 1 if k in t else 0

for k in ["silver rises", "silver higher", "xagusd up"]:
s["silver"] += 1 if k in t else 0
for k in ["silver falls", "silver lower", "xagusd down"]:
s["silver"] -= 1 if k in t else 0

for k in ["audusd rises", "aud stronger", "commodity currencies higher"]:
s["aud"] += 1 if k in t else 0
for k in ["audusd falls", "aud weaker", "commodity currencies weaker"]:
s["aud"] -= 1 if k in t else 0

for k in ["jpy stronger", "yen gains", "audjpy falls"]:
s["jpy"] += 1 if k in t else 0
for k in ["jpy weaker", "yen falls", "audjpy rises"]:
s["jpy"] -= 1 if k in t else 0

for k in ["cpi", "inflation", "nfp", "non-farm", "fomc", "fed meeting", "interest rate", "rate decision", "powell", "boj", "rba", "pce", "gdp", "jobs report"]:
s["impact"] += 1 if k in t else 0

return s

def interpret(asset, df):
if df.empty:
return "No headlines found."

combined = " ".join((df["title"].fillna("") + " ").tolist()).lower()
s = score_text(combined)
conflict = False

if asset == "Gold":
raw = s["gold"] + (-s["real"]) + (-s["dxy"]) + (-s["risk"])
conflict = (s["real"] > 0 and s["risk"] < 0) or (s["real"] < 0 and s["risk"] > 0) or (s["dxy"] > 0 and s["risk"] > 0)
bias = "Bullish" if raw > 0 else "Bearish" if raw < 0 else "Neutral"
elif asset == "Silver":
raw = s["silver"] + (-s["real"]) + (-s["dxy"]) + (-s["risk"])
conflict = abs(s["real"]) > 0 and abs(s["risk"]) > 0 and (s["real"] * s["risk"] < 0)
bias = "Bullish" if raw > 0 else "Bearish" if raw < 0 else "Neutral"
elif asset == "AUDUSD":
raw = s["aud"] + s["risk"] + (-s["dxy"])
conflict = (s["aud"] > 0 and s["dxy"] > 0) or (s["aud"] < 0 and s["risk"] > 0)
bias = "Bullish" if raw > 0 else "Bearish" if raw < 0 else "Neutral"
else:
raw = s["aud"] + (-s["jpy"]) + s["risk"]
conflict = (s["risk"] > 0 and s["jpy"] > 0) or (s["risk"] < 0 and s["jpy"] < 0)
bias = "Bullish" if raw > 0 else "Bearish" if raw < 0 else "Neutral"

if s["impact"] >= 2 and conflict:
bias = "Conflicted"

conf = "High" if abs(raw) >= 4 and not conflict else "Medium" if abs(raw) >= 2 else "Low"

drivers = []
if s["dxy"] != 0:
drivers.append("DXY")
if s["real"] != 0:
drivers.append("real yields")
if s["risk"] != 0:
drivers.append("risk sentiment")
if asset in ("AUDUSD", "AUDJPY") and s["aud"] != 0:
drivers.append("AUD / Australia")
if asset == "AUDJPY" and s["jpy"] != 0:
drivers.append("JPY / BoJ")
if s["impact"] > 0:
drivers.append("high-impact news")

return f"{bias} | Confidence: {conf} | Drivers: {', '.join(drivers) if drivers else 'mixed headlines'}"

def mini_chart(df, title):
if df.empty:
st.info("No data.")
return
fig = go.Figure()
fig.add_trace(go.Scatter(x=df["date"], y=df["value"], mode="lines", line=dict(width=2)))
fig.update_layout(title=title, height=260, margin=dict(l=10, r=10, t=40, b=10))
fig.update_xaxes(title_text="Date")
fig.update_yaxes(title_text="Value")
st.plotly_chart(fig, use_container_width=True)

api_key = st.secrets.get("FRED_API_KEY", None) if hasattr(st, "secrets") else None

news_df = pull_news()

col1, col2 = st.columns([1.15, 0.85])

with col1:
st.subheader("Latest headlines")
asset = st.selectbox("Asset", ["Gold", "Silver", "AUDUSD", "AUDJPY"])
subset = news_df[news_df["asset"].isin(["Macro", asset])].head(20)
st.dataframe(subset[["asset", "title", "seendate"]], use_container_width=True, hide_index=True)

with col2:
st.subheader("Interpretation")
st.write(interpret(asset, subset))
st.caption("Conflicted appears when high-impact news disagrees with the macro backdrop.")

st.divider()
st.subheader("Macro panel")

m1, m2, m3 = st.columns(3)
with m1:
dfii5 = fetch_fred("DFII5", api_key)
st.metric("DFII5", f"{dfii5['value'].iloc[-1]:.2f}%" if not dfii5.empty else "n/a")
mini_chart(dfii5.tail(90), "DFII5 trend")
with m2:
vix = fetch_fred("VIXCLS", api_key)
st.metric("VIX", f"{vix['value'].iloc[-1]:.2f}" if not vix.empty else "n/a")
mini_chart(vix.tail(90), "VIX trend")
with m3:
sp500 = fetch_fred("SP500", api_key)
st.metric("US500", f"{sp500['value'].iloc[-1]:.0f}" if not sp500.empty else "n/a")
mini_chart(sp500.tail(90), "US500 trend")

st.divider()
st.subheader("Setup")

st.code("pip install streamlit requests pandas plotly")
st.code("streamlit run app.py")