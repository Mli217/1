# pages/1_航线规划.py
import streamlit as st
from streamlit_folium import folium_static
import folium
from folium.plugins import MousePosition, Draw
from utils import gcj02_to_wgs84

st.set_page_config(page_title="航线规划", layout="wide")
st.title("🗺️ 航线规划 (可缩放2D地图 + 障碍物)")

# 初始化会话状态
if 'coord_type' not in st.session_state:
    st.session_state.coord_type = "GCJ-02"
if 'pointA' not in st.session_state:
    st.session_state.pointA = {"lat": 32.2322, "lng": 118.749}   # 校园内示例A点
if 'pointB' not in st.session_state:
    st.session_state.pointB = {"lat": 32.2343, "lng": 118.749}   # 校园内示例B点
if 'flight_height' not in st.session_state:
    st.session_state.flight_height = 50
if 'obstacles' not in st.session_state:
    # 预置两个障碍物（示例）
    st.session_state.obstacles = [
        {"lat": 32.2330, "lng": 118.7495, "radius": 30},
        {"lat": 32.2338, "lng": 118.7488, "radius": 25}
    ]

# 侧边栏控制面板
with st.sidebar:
    st.header("🎮 控制面板")
    
    # 坐标系选择
    coord_type = st.radio("输入坐标系", ["WGS-84", "GCJ-02 (高德/百度)"], 
                          index=0 if st.session_state.coord_type == "WGS-84" else 1)
    st.session_state.coord_type = coord_type.split()[0]
    
    st.subheader("起点 A")
    col1, col2 = st.columns(2)
    latA = col1.number_input("纬度", value=st.session_state.pointA["lat"], format="%.6f", key="latA")
    lngA = col2.number_input("经度", value=st.session_state.pointA["lng"], format="%.6f", key="lngA")
    if st.button("📍 设置A点"):
        st.session_state.pointA = {"lat": latA, "lng": lngA}
        st.success(f"A点已设: ({latA}, {lngA})")
    
    st.subheader("终点 B")
    col3, col4 = st.columns(2)
    latB = col3.number_input("纬度", value=st.session_state.pointB["lat"], format="%.6f", key="latB")
    lngB = col4.number_input("经度", value=st.session_state.pointB["lng"], format="%.6f", key="lngB")
    if st.button("📍 设置B点"):
        st.session_state.pointB = {"lat": latB, "lng": lngB}
        st.success(f"B点已设: ({latB}, {lngB})")
    
    st.subheader("✈️ 飞行参数")
    height = st.number_input("设定飞行高度 (m)", min_value=10, max_value=500, 
                             value=st.session_state.flight_height, step=5)
    st.session_state.flight_height = height
    st.info(f"高度: {height} 米")
    
    st.subheader("🚧 障碍物管理")
    st.markdown("当前障碍物列表：")
    for i, obs in enumerate(st.session_state.obstacles):
        st.write(f"{i+1}.  ({obs['lat']:.4f}, {obs['lng']:.4f}) 半径 {obs['radius']}m")
    
    # 添加新障碍物（简易方式）
    with st.expander("➕ 添加障碍物"):
        new_lat = st.number_input("纬度", value=32.2330, format="%.6f", key="new_lat")
        new_lng = st.number_input("经度", value=118.7490, format="%.6f", key="new_lng")
        new_radius = st.number_input("半径(米)", min_value=10, max_value=200, value=30, key="new_radius")
        if st.button("添加障碍物"):
            st.session_state.obstacles.append({"lat": new_lat, "lng": new_lng, "radius": new_radius})
            st.success("障碍物已添加，请刷新地图查看")
            st.rerun()
    
    if st.button("🗑️ 清空所有障碍物"):
        st.session_state.obstacles = []
        st.rerun()

# 坐标转换函数（用于地图显示）
def get_map_coords(lat, lng, input_type):
    if input_type == "GCJ-02":
        wgs_lng, wgs_lat = gcj02_to_wgs84(lng, lat)
        return wgs_lat, wgs_lng
    else:
        return lat, lng

# 转换A/B点为WGS84（folium底图坐标）
map_latA, map_lngA = get_map_coords(st.session_state.pointA["lat"], st.session_state.pointA["lng"], st.session_state.coord_type)
map_latB, map_lngB = get_map_coords(st.session_state.pointB["lat"], st.session_state.pointB["lng"], st.session_state.coord_type)

# 地图中心点
center_lat = (map_latA + map_latB) / 2
center_lng = (map_lngA + map_lngB) / 2

# 创建地图（标准2D，支持缩放）
m = folium.Map(location=[center_lat, center_lng], zoom_start=17, control_scale=True)

# 添加A点标记
folium.Marker(
    [map_latA, map_lngA],
    popup=f"起点 A (输入坐标: {st.session_state.coord_type})",
    icon=folium.Icon(color="green", icon="play", prefix="fa")
).add_to(m)

# 添加B点标记
folium.Marker(
    [map_latB, map_lngB],
    popup=f"终点 B (输入坐标: {st.session_state.coord_type})",
    icon=folium.Icon(color="red", icon="stop", prefix="fa")
).add_to(m)

# 绘制航线（直线，演示用）
folium.PolyLine(
    [(map_latA, map_lngA), (map_latB, map_lngB)],
    color="blue", weight=5, opacity=0.8, tooltip="规划航线"
).add_to(m)

# 添加所有障碍物（圆形）
for obs in st.session_state.obstacles:
    # 注意：障碍物的坐标也需要转换（用户输入的障碍物可能是什么坐标系？这里假设用户添加时使用的是当前选择的输入坐标系）
    # 为了统一，障碍物存储的坐标是用户输入的原始坐标，需要转换成WGS84显示
    obs_lat, obs_lng = get_map_coords(obs["lat"], obs["lng"], st.session_state.coord_type)
    folium.Circle(
        radius=obs["radius"],
        location=[obs_lat, obs_lng],
        color="orange",
        fill=True,
        fill_opacity=0.3,
        popup=f"障碍物 (半径{obs['radius']}m)"
    ).add_to(m)

# 添加鼠标坐标显示（方便圈选）
MousePosition().add_to(m)

# 可选：添加绘图工具栏（Draw）允许用户在地图上圈画障碍物（高级功能）
# 如果不需要可以注释掉下一行
Draw(export=True).add_to(m)

# 显示地图
folium_static(m, width=1000, height=600)

# 显示当前设置信息
st.subheader("当前航线数据")
colA, colB, colH = st.columns(3)
colA.metric("起点 A", f"({st.session_state.pointA['lat']:.6f}, {st.session_state.pointA['lng']:.6f})")
colB.metric("终点 B", f"({st.session_state.pointB['lat']:.6f}, {st.session_state.pointB['lng']:.6f})")
colH.metric("飞行高度", f"{st.session_state.flight_height} 米")
st.caption(f"输入坐标系: {st.session_state.coord_type}  →  地图显示已自动转换至WGS-84")
st.info("💡 提示：地图支持缩放和拖动，右侧工具栏可绘制多边形/圆形来添加障碍物（需手动记录坐标）")
