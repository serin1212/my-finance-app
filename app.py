import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from st_supabase_connection import SupabaseConnection

# 1. 網頁標題與介紹
st.set_page_config(page_title="金融總經數據看板", layout="wide")
st.title("📊 金融總經數據與股權風險溢酬 (ERP) 看板")
st.markdown("本網頁即時從雲端 **Supabase PostgreSQL** 讀取數據，並動態繪製美股大盤與 ERP 趨勢圖。")

# 2. 直連到 Supabase 資料庫 (直接帶入金鑰，免除 secrets.toml 找不到的問題)
@st.cache_resource
def init_connection():
    url = "https://lbebigddshwkvjskrela.supabase.co"
    # 💡 請把下面這行引號裡面的文字，換成你那串以 eyJ 開頭的超長 anon public 金鑰
    key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImxiZWJpZ2Rkc2h3a3Zqc2tyZWxhIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODA2MzU1OTMsImV4cCI6MjA5NjIxMTU5M30.VA90l1D7qvrpmz4W5Uxkqm7ONmZ-961qVoQhpr8LYrQ"
    
    return st.connection("supabase", type=SupabaseConnection, url=url, key=key)

supabase = init_connection()

# 3. 從資料庫撈取資料
@st.cache_data(ttl=600) # 快取 10 分鐘
def load_data():
    # 透過 API 讀取 macro_market_data 資料表，並依照日期排序
    response = supabase.table("macro_market_data").select("*").order("date", desc=False).execute()
    df = pd.DataFrame(response.data)
    # 轉換資料型態
    df['date'] = pd.to_datetime(df['date'])
    df['sp500_close'] = pd.to_numeric(df['sp500_close'])
    df['equity_risk_premium'] = pd.to_numeric(df['equity_risk_premium']) * 100 # 轉為百分比 %
    return df

try:
    df = load_data()
    
    # 4. 網頁最上方放置重點數據指標 (Metrics)
    latest = df.iloc[-1]
    prev = df.iloc[-2]
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(label="最新交易日期", value=latest['date'].strftime('%Y-%m-%d'))
    with col2:
        sp_change = latest['sp500_close'] - prev['sp500_close']
        st.metric(label="S&P 500 收盤價", value=f"{latest['sp500_close']:.2f}", delta=f"{sp_change:+.2f}")
    with col3:
        erp_change = latest['equity_risk_premium'] - prev['equity_risk_premium']
        st.metric(label="股權風險溢酬 (ERP)", value=f"{latest['equity_risk_premium']:.3f}%", delta=f"{erp_change:+.3f}%")

    st.markdown("---")

    # 5. 繪製雙軸互動式圖表 (使用 Plotly)
    st.subheader("📈 S&P 500 走勢與 ERP 變化趨勢對比")
    
    # 建立雙 Y 軸圖表
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    
    # 軌跡 1：S&P 500 (左軸，藍線)
    fig.add_trace(
        go.Scatter(x=df['date'], y=df['sp500_close'], name="S&P 500 Close", line=dict(color="#1f77b4", width=3)),
        secondary_y=False,
    )
    
    # 軌跡 2：ERP (右軸，橘色區域線)
    fig.add_trace(
        go.Scatter(x=df['date'], y=df['equity_risk_premium'], name="Equity Risk Premium (ERP)", line=dict(color="#ff7f0e", width=2), fill='tozeroy'),
        secondary_y=True,
    )
    
    # 設定圖表樣式與標題
    fig.update_layout(
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=20, r=20, t=20, b=20),
        height=500
    )
    
    fig.update_yaxes(title_text="<b>S&P 500 指數</b>", secondary_y=False, gridcolor="rgba(200,200,200,0.3)")
    fig.update_yaxes(title_text="<b>股權風險溢酬 ERP (%)</b>", secondary_y=True)
    
    # 將圖表渲染至 Streamlit 網頁上
    st.plotly_chart(fig, use_container_width=True)
    
    # 6. 顯示歷史數據明細
    with st.expander("🔍 點擊查看歷史數據明細"):
        st.dataframe(df.sort_values(by="date", ascending=False), use_container_width=True)

except Exception as e:
    st.error(f"資料讀取失敗，請檢查 Supabase 設定。錯誤訊息: {e}")