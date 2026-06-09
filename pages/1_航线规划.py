# pages/1_航线规划.py
import streamlit as st
from streamlit_folium import folium_static
import folium
from folium.plugins import MousePosition
from utils import gcj02_to_wgs84

st.set_page_config(page_title="航线规划", layout="wide")
st.title("🗺️ 航线规划 (3D地图 + 障碍物)")

# 初始化会话状态
if 'coord_type' not in st.session_state:
    st.session_state.coord_type = "GCJ-02"
if 'pointA' not in st.session_state:
    st.session_state.pointA = {"lat": 32.2322, "lng": 118.749}
if 'pointB' not in st.session_state:
    st.session_state.pointB = {"lat": 32.2343, "lng": 118.749}
if 'flight_height' not in st.session_state:
    st.session_state.flight_height = 50

# 侧边栏控制面板
with st.sidebar:
    st.header("🎮 控制面板")
    coord_type = st.radio("输入坐标系", ["WGS-84", "GCJ-02 (高德/百度)"], index=0 if st.session_state.coord_type=="WGS-84" else 1)
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
    height = st.number_input("设定飞行高度 (m)", min_value=10, max_value=500, value=st.session_state.flight_height, step=5)
    st.session_state.flight_height = height
    st.info(f"高度: {height} 米")

# 坐标转换（用于地图显示）
def get_map_coords(lat, lng, input_type):
    if input_type == "GCJ-02":
        wgs_lng, wgs_lat = gcj02_to_wgs84(lng, lat)
        return wgs_lat, wgs_lng
    else:
        return lat, lng

map_latA, map_lngA = get_map_coords(st.session_state.pointA["lat"], st.session_state.pointA["lng"], st.session_state.coord_type)
map_latB, map_lngB = get_map_coords(st.session_state.pointB["lat"], st.session_state.pointB["lng"], st.session_state.coord_type)

center_lat = (map_latA + map_latB) / 2
center_lng = (map_lngA + map_lngB) / 2

m = folium.Map(location=[center_lat, center_lng], zoom_start=17, control_scale=True)

folium.Marker([map_latA, map_lngA], popup=f"起点 A", icon=folium.Icon(color="green", icon="play", prefix="fa")).add_to(m)
folium.Marker([map_latB, map_lngB], popup=f"终点 B", icon=folium.Icon(color="red", icon="stop", prefix="fa")).add_to(m)
folium.PolyLine([(map_latA, map_lngA), (map_latB, map_lngB)], color="blue", weight=5, opacity=0.8).add_to(m)

# 障碍物示例（校园内可自行调整坐标）
obstacles = [
    {"center": [32.2330, 118.7495], "radius": 30, "color": "orange"},
    {"center": [32.2338, 118.7488], "radius": 25, "color": "orange"},
]
for obs in obstacles:
    folium.Circle(radius=obs["radius"], location=obs["center"], color=obs["color"], fill=True, fill_opacity=0.3, popup="障碍物").add_to(m)

MousePosition().add_to(m)
folium_static(m, width=900, height=600)

st.subheader("当前航线数据")
colA, colB = st.columns(2)
colA.metric("起点 A", f"({st.session_state.pointA['lat']:.6f}, {st.session_state.pointA['lng']:.6f})")
colB.metric("终点 B", f"({st.session_state.pointB['lat']:.6f}, {st.session_state.pointB['lng']:.6f})")
st.caption(f"飞行高度: {st.session_state.flight_height} 米 | 坐标系: {st.session_state.coord_type} (输入) → 地图显示已转换")
