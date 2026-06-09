# pages/1_航线规划.py
import streamlit as st
import pydeck as pdk
import pandas as pd
import numpy as np
from utils import gcj02_to_wgs84

st.set_page_config(page_title="航线规划 - 3D地图", layout="wide")
st.title("🗺️ 航线规划 (3D地图 + 障碍物)")

# 初始化会话状态
if 'coord_type' not in st.session_state:
    st.session_state.coord_type = "GCJ-02"
if 'pointA' not in st.session_state:
    st.session_state.pointA = {"lat": 32.2322, "lng": 118.749}   # 校园内A点
if 'pointB' not in st.session_state:
    st.session_state.pointB = {"lat": 32.2343, "lng": 118.749}   # 校园内B点
if 'flight_height' not in st.session_state:
    st.session_state.flight_height = 50
if 'obstacles' not in st.session_state:
    # 障碍物列表: 每个障碍物包含中心坐标(lat, lng)、半径(米)、高度(米)
    st.session_state.obstacles = [
        {"lat": 32.2330, "lng": 118.7495, "radius": 30, "height": 40},
        {"lat": 32.2338, "lng": 118.7488, "radius": 25, "height": 35}
    ]

# 侧边栏控制面板
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

# 坐标转换 (输入坐标系 -> WGS84，pydeck使用WGS84)
def to_wgs84(lat, lng, input_type):
    if input_type == "GCJ-02":
        wgs_lng, wgs_lat = gcj02_to_wgs84(lng, lat)
        return wgs_lat, wgs_lng
    else:
        return lat, lng

# 转换 A, B 点
latA_wgs, lngA_wgs = to_wgs84(st.session_state.pointA["lat"], st.session_state.pointA["lng"], st.session_state.coord_type)
latB_wgs, lngB_wgs = to_wgs84(st.session_state.pointB["lat"], st.session_state.pointB["lng"], st.session_state.coord_type)

# 准备航线数据 (Line layer)
line_data = pd.DataFrame({
    "lat": [latA_wgs, latB_wgs],
    "lng": [lngA_wgs, lngB_wgs]
})

# 准备A/B点标记 (Scatterplot layer)
marker_data = pd.DataFrame({
    "lat": [latA_wgs, latB_wgs],
    "lng": [lngA_wgs, lngB_wgs],
    "name": ["起点 A", "终点 B"],
    "color": [[0, 255, 0, 255], [255, 0, 0, 255]]  # RGBA
})

# 准备障碍物 (圆柱体: 每个圆柱用多个点构成，简化起见使用 ColumnLayer 绘制圆柱)
# 为简化，使用 ScatterplotLayer 配合圆形？但3D圆柱需要 ColumnLayer
# 使用 pdk.ColumnLayer 来画圆柱体
column_data = []
for obs in st.session_state.obstacles:
    obs_lat, obs_lng = to_wgs84(obs["lat"], obs["lng"], st.session_state.coord_type)
    column_data.append({
        "lat": obs_lat,
        "lng": obs_lng,
        "radius": obs["radius"],
        "height": obs["height"]
    })
column_df = pd.DataFrame(column_data)

# 计算地图中心点和缩放级别
center_lat = (latA_wgs + latB_wgs) / 2
center_lng = (lngA_wgs + lngB_wgs) / 2
# 计算两点距离来确定合适的缩放级别
from math import radians, sin, cos, sqrt, atan2
def haversine(lat1, lng1, lat2, lng2):
    R = 6371000
    phi1, phi2 = radians(lat1), radians(lat2)
    dphi = radians(lat2 - lat1)
    dlam = radians(lng2 - lng1)
    a = sin(dphi/2)**2 + cos(phi1)*cos(phi2)*sin(dlam/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    return R * c
dist = haversine(latA_wgs, lngA_wgs, latB_wgs, lngB_wgs)
zoom = max(14, 18 - int(dist / 100))  # 粗略调整

# 创建 pydeck 视图 (3D 视角)
view_state = pdk.ViewState(
    latitude=center_lat,
    longitude=center_lng,
    zoom=zoom,
    pitch=50,        # 倾斜角，产生3D效果
    bearing=0,
    height=600
)

# 图层1: 航线 (LineLayer)
line_layer = pdk.Layer(
    "LineLayer",
    data=line_data,
    get_source_position="[lng, lat]",
    get_target_position="[lng, lat]",
    get_color="[0, 0, 255, 200]",
    get_width=5,
    pickable=True,
    auto_highlight=True
)
# 注意：LineLayer 需要源和目标位置，这里我们只有一条线段，需要两条记录？正确用法是起点和终点分开列。
# 更简单：使用 PathLayer
path_data = pd.DataFrame([{"path": [[lngA_wgs, latA_wgs], [lngB_wgs, latB_wgs]]}])
path_layer = pdk.Layer(
    "PathLayer",
    data=path_data,
    get_path="path",
    get_color="[0, 0, 255, 200]",
    get_width=5,
    width_min_pixels=2,
    pickable=True
)

# 图层2: A/B 点标记 (ScatterplotLayer)
marker_layer = pdk.Layer(
    "ScatterplotLayer",
    data=marker_data,
    get_position="[lng, lat]",
    get_fill_color="color",
    get_radius=20,
    pickable=True,
    auto_highlight=True
)

# 图层3: 障碍物 (ColumnLayer 绘制圆柱体)
if not column_df.empty:
    column_layer = pdk.Layer(
        "ColumnLayer",
        data=column_df,
        get_position="[lng, lat]",
        get_elevation="height",
        get_radius="radius",
        get_fill_color="[255, 165, 0, 180]",  # 橙色半透明
        elevation_scale=1,
        radius_min_pixels=5,
        extruded=True,
        pickable=True
    )
else:
    column_layer = None

# 组合图层
layers = [path_layer, marker_layer]
if column_layer:
    layers.append(column_layer)

# 3D 地图工具提示
tooltip = {
    "html": "<b>名称:</b> {name} <br/> <b>坐标:</b> ({lat}, {lng})",
    "style": {"background": "white", "color": "black"}
}
# 对于障碍物单独提示
tooltip_obs = {
    "html": "<b>障碍物</b><br/>半径: {radius} m<br/>高度: {height} m",
    "style": {"background": "orange", "color": "black"}
}

# 渲染地图
r = pdk.Deck(
    layers=layers,
    initial_view_state=view_state,
    tooltip=tooltip,
    map_style="mapbox://styles/mapbox/satellite-streets-v11"  # 卫星混合地图，更有3D感
    # 也可以使用 "light" 或 "dark"
)

st.pydeck_chart(r)

# 显示坐标信息和障碍物列表
st.subheader("当前规划数据")
colA, colB, colH = st.columns(3)
colA.metric("起点 A", f"({st.session_state.pointA['lat']:.6f}, {st.session_state.pointA['lng']:.6f})")
colB.metric("终点 B", f"({st.session_state.pointB['lat']:.6f}, {st.session_state.pointB['lng']:.6f})")
colH.metric("飞行高度", f"{st.session_state.flight_height} 米")
st.caption(f"输入坐标系: {st.session_state.coord_type}  →  地图显示已自动转换至WGS-84")
st.info("💡 提示：地图支持鼠标拖拽旋转视角（按住右键拖动），滚轮缩放。橙色圆柱体为障碍物。")
