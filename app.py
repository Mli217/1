# app.py
import streamlit as st

st.set_page_config(page_title="无人机智能规划系统", layout="wide")

# 定义页面（指向 pages/ 下的文件）
page1 = st.Page("pages/1_航线规划.py", title="航线规划", icon="📍")
page2 = st.Page("pages/2_飞行监控.py", title="飞行监控", icon="📡")

# 创建导航（自动生成侧边栏菜单）
nav = st.navigation([page1, page2])

# 在侧边栏顶部添加自定义内容（位于导航菜单上方）
with st.sidebar:
    st.title("🗺️ 导航")
    st.markdown("📌 功能页面")

# 运行导航（页面菜单会显示在自定义内容下方）
nav.run()
