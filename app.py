# app.py
import streamlit as st

st.set_page_config(page_title="无人机智能规划系统", layout="wide")

# 手动定义页面，自定义标题
pg1 = st.Page("pages/1_航线规划.py", title="航线规划", icon="📍")
pg2 = st.Page("pages/2_飞行监控.py", title="飞行监控", icon="📡")
nav = st.navigation([pg1, pg2])

# 在侧边栏顶部添加自定义内容（在导航菜单上方）
with st.sidebar:
    st.title("🗺️ 导航")
    st.markdown("📌 功能页面")

nav.run()
