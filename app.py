import streamlit as st

st.set_page_config(page_title="无人机智能规划系统", layout="wide")

# 手动侧边栏（指向 pages 文件夹内的两个页面）
with st.sidebar:
    st.title("🗺️ 导航")
    st.markdown("📌 功能页面")
    st.page_link("pages/1_航线规划.py", label="航线规划", icon="📍")
    st.page_link("pages/2_飞行监控.py", label="飞行监控", icon="📡")

st.title("无人机智能化应用系统")
st.markdown("## 功能模块")
st.markdown("- 📍 **航线规划**：设置A/B点，坐标系，飞行高度，3D地图+障碍物")
st.markdown("- 📡 **飞行监控**：实时心跳包，掉线报警，序号折线图")
st.info("👈 点击左侧菜单开始")
