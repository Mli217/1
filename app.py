# app.py
import streamlit as st

st.set_page_config(page_title="无人机智能规划系统", layout="wide")

# 定义页面（直接引用 pages/ 下的文件）
pg1 = st.Page("pages/1_航线规划.py", title="航线规划", icon="📍")
pg2 = st.Page("pages/2_飞行监控.py", title="飞行监控", icon="📡")

# 使用 st.navigation 创建自定义导航（会覆盖默认的 pages 菜单）
# expanded=True 可以让导航默认展开显示所有页面
pg = st.navigation([pg1, pg2], expanded=True)

# 在侧边栏顶部添加自定义标题（会显示在导航列表上方）
with st.sidebar:
    st.title("🗺️ 导航")
    st.markdown("📌 功能页面")
    # 注：st.navigation 已经自动生成页面列表，这里不需要再添加 page_link

# 运行选中的页面（当前激活的页面）
pg.run()
