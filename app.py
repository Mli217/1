import streamlit as st

st.set_page_config(page_title="无人机智能规划系统", layout="wide")

# 侧边栏：导航标题
with st.sidebar:
    st.title("🗺️ 导航")
    st.markdown("📌 功能页面")
    page = st.radio(
        "选择功能",
        ["航线规划", "飞行监控"],
        label_visibility="collapsed",  # 隐藏默认标签
        index=0
    )

# 根据选择显示不同内容
if page == "航线规划":
    # ---------- 航线规划页面 ----------
    st.title("🗺️ 航线规划 (3D地图 + 障碍物)")
    # 这里粘贴之前可用的地图代码（下面给出精简版）
    st.info("地图代码请从之前正常工作的版本中复制，此处用占位符")
    # 为避免错误，放一个简单地图示例
    st.map({"lat": [32.2322, 32.2343], "lon": [118.749, 118.749]})
else:
    # ---------- 飞行监控页面 ----------
    st.title("📡 飞行监控 - 无人机心跳监测")
    # 心跳代码（精简版）
    if 'heartbeat_data' not in st.session_state:
        st.session_state.heartbeat_data = []
    # ... 省略完整心跳代码，您可以复制之前可用的
    st.write("心跳监测将在这里显示")
