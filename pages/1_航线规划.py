import streamlit as st
import pydeck as pdk
import pandas as pd
from utils import gcj02_to_wgs84

st.set_page_config(page_title="航线规划 - 3D地图", layout="wide")
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
if 'obstacles' not in st.session_state:
    st.session_state.obstacles = [
        {"lat": 32.2330, "lng": 118.7495, "radius": 30, "height": 40},
        {"lat": 32.2338, "lng": 118.7488, "radius": 25, "height": 35}
    ]

# 侧边栏
with st.sidebar:
    st.header("🎮 控制面板")
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
    for i, obs in enumerate(st.session_state.obstacles):
        st.write(f"{i+1}. ({obs['lat']:.4f}, {obs['lng']:.4f}) 半径{obs['radius']}m 高{obs['height']}m")
    with st.expander("➕ 添加障碍物"):
        new_lat = st.number_input("纬度", value=32.2330, format="%.6f", key="new_lat")
        new_lng = st.number_input("经度", value=118.7490, format="%.6f", key="new_lng")
        new_radius = st.number_input("半径(米)", min_value=10, max_value=200, value=30, key="new_radius")
        new_height = st.number_input("高度(米)", min_value=10, max_value=100, value=40, key="new_height")
        if st.button("添加障碍物"):
            st.session_state.obstacles.append({"lat": new_lat, "lng": new_lng, "radius": new_radius, "height": new_height})
            st.success("障碍物已添加")
            st.rerun()
    if st.button("🗑️ 清空所有障碍物"):
        st.session_state.obstacles = []
        st.rerun()

# 坐标转换
def to_wgs84(lat, lng, input_type):
    if input_type == "GCJ-02":
        wgs_lng, wgs_lat = gcj02_to_wgs84(lng, lat)
        return wgs_lat, wgs_lng
    else:
        return lat, lng

latA_w, lngA_w = to_wgs84(st.session_state.pointA["lat"], st.session_state.pointA["lng"], st.session_state.coord_type)
latB_w, lngB_w = to_wgs84(st.session_state.pointB["lat"], st.session_state.pointB["lng"], st.session_state.coord_type)

# 航线路径数据
path_data = pd.DataFrame([{"path": [[lngA_w, latA_w], [lngB_w, latB_w]]}])
path_layer = pdk.Layer(
    "PathLayer",
    data=path_data,
    get_path="path",
    get_color="[0, 0, 255, 200]",
    get_width=8,
    width_min_pixels=2,
    pickable=True
)

# A/B 点标记
marker_data = pd.DataFrame({
    "lat": [latA_w, latB_w],
    "lng": [lngA_w, lngB_w],
    "name": ["起点 A", "终点 B"],
    "color": [[0, 255, 0, 255], [255, 0, 0, 255]]
})
marker_layer = pdk.Layer(
    "ScatterplotLayer",
    data=marker_data,
    get_position="[lng, lat]",
    get_fill_color="color",
    get_radius=20,
    pickable=True
)

# 障碍物圆柱体
column_data = []
for obs in st.session_state.obstacles:
    obs_lat, obs_lng = to_wgs84(obs["lat"], obs["lng"], st.session_state.coord_type)
    column_data.append({
        "lat": obs_lat, "lng": obs_lng,
        "radius": obs["radius"], "height": obs["height"]
    })
column_df = pd.DataFrame(column_data)
if not column_df.empty:
    column_layer = pdk.Layer(
        "ColumnLayer",
        data=column_df,
        get_position="[lng, lat]",
        get_elevation="height",
        get_radius="radius",
        get_fill_color="[255, 165, 0, 180]",
        elevation_scale=1,
        radius_min_pixels=3,
        extruded=True,
        pickable=True
    )
else:
    column_layer = None

# 地图视角
center_lat = (latA_w + latB_w) / 2
center_lng = (lngA_w + lngB_w) / 2
view_state = pdk.ViewState(
    latitude=center_lat, longitude=center_lng,
    zoom=16, pitch=50, bearing=0, height=600
)

# 合并图层
layers = [path_layer, marker_layer]
if column_layer:
    layers.append(column_layer)

# 工具提示
tooltip = {"html": "<b>{name}</b><br/>坐标: ({lat}, {lng})", "style": {"background": "white"}}

# 渲染地图 - 使用免费 Carto 底图，无需 token
r = pdk.Deck(
    layers=layers,
    initial_view_state=view_state,
    tooltip=tooltip,
    map_provider='carto',
    map_style='positron',
    height=600
)

st.pydeck_chart(r)

# 显示规划数据
st.subheader("当前规划数据")
colA, colB, colH = st.columns(3)
colA.metric("起点 A", f"({st.session_state.pointA['lat']:.6f}, {st.session_state.pointA['lng']:.6f})")
colB.metric("终点 B", f"({st.session_state.pointB['lat']:.6f}, {st.session_state.pointB['lng']:.6f})")
colH.metric("飞行高度", f"{st.session_state.flight_height} 米")
st.caption(f"输入坐标系: {st.session_state.coord_type}  →  地图显示已自动转换至WGS-84")
st.info("💡 鼠标按住右键拖拽可旋转视角，滚轮缩放。橙色圆柱体为障碍物。")
