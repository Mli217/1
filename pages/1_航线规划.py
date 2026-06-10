# pages/1_航线规划.py
import streamlit as st
import folium
from streamlit_folium import st_folium
from folium.plugins import Draw, MousePosition
import json
import datetime
import math
import os
import time
import uuid
from shapely.geometry import Polygon, Point, LineString
from utils import (
    convert_coord_for_display, convert_coord_for_storage,
    save_memories_to_file, load_memories_from_file,
    wgs84_to_gcj02, gcj02_to_wgs84
)

# ... (其他函数定义与之前一致，保持不动)

# ==================== 初始化 ====================
# ... (初始化代码与之前保持一致)

# 加载记忆
if 'memories' not in st.session_state:
    st.session_state.memories = load_memories_from_file()

if 'polygon_obstacles' not in st.session_state:
    st.session_state.polygon_obstacles = []

# 核心修改：绘制障碍物时进行坐标转换
# 在生成地图时，遍历 polygon_obstacles，先转换坐标再绘制
# 例如（如果你使用 folium 绘制）：
for obs in st.session_state.polygon_obstacles:
    raw_coords = obs["coordinates"]
    # 转换为显示坐标
    display_coords = []
    for lng, lat in raw_coords:
        disp_lng, disp_lat = convert_coord_for_display(lng, lat, st.session_state.coord_type)
        display_coords.append([disp_lat, disp_lng])  # folium 需要 [lat, lng]
    # 绘制多边形
    # ...

# 核心修改：捕获绘图后，存储为 WGS-84
if output and output.get("last_active_drawing"):
    drawing = output["last_active_drawing"]
    if drawing and drawing.get("geometry"):
        geom = drawing["geometry"]
        raw_coords = []
        # 获取原始坐标
        if geom["type"] == "Polygon":
            raw_coords = geom["coordinates"][0]
        elif geom["type"] == "Circle":
            center = geom["coordinates"][0]
            radius = geom["coordinates"][1]
            raw_coords = circle_to_polygon(center[0], center[1], radius)
        # 转换为存储坐标（WGS-84）
        storage_coords = []
        for lng, lat in raw_coords:
            store_lng, store_lat = convert_coord_for_storage(lng, lat, st.session_state.coord_type)
            storage_coords.append([store_lng, store_lat])
        if storage_coords:
            st.session_state.temp_new_obstacle = storage_coords
            st.rerun()

# ... (后续代码与之前保持一致，但保存记忆时直接用 storage_coords)
