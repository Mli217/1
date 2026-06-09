# app.py
import streamlit as st

st.set_page_config(page_title="无人机智能规划系统", layout="wide")

st.sidebar.title("🗺️ 导航")
st.sidebar.markdown("请从侧边栏选择功能页面")

st.title("无人机智能化应用系统")
st.markdown("## 功能模块")
st.markdown("- 📍 **航线规划**：设置A/B点（校园内），选择坐标系，设定飞行高度，显示3D地图及障碍物")
st.markdown("- 📡 **飞行监控**：实时心跳包监测，掉线报警，序号折线图")

st.info("👈 请点击左侧侧边栏的「航线规划」或「飞行监控」开始使用")
