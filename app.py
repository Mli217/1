import streamlit as st

st.set_page_config(page_title="无人机智能规划系统", layout="wide")

# 定义页面，自定义标题和图标
pg1 = st.Page("pages/1_航线规划.py", title="航线规划", icon="📍")
pg2 = st.Page("pages/2_飞行监控.py", title="飞行监控", icon="📡")

# 创建导航，expanded=True 保证菜单展开
nav = st.navigation([pg1, pg2], expanded=True)

# 在侧边栏最顶部添加自定义内容（会显示在导航菜单上方）
with st.sidebar:
    st.title("🗺️ 导航")
    st.markdown("📌 功能页面")

# 运行导航
nav.run()
