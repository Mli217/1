# pages/1_航线规划.py
import streamlit as st
import json

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

# 坐标转换
def to_wgs84(lat, lng, input_type):
    if input_type == "GCJ-02":
        try:
            from utils import gcj02_to_wgs84
            wgs_lng, wgs_lat = gcj02_to_wgs84(lng, lat)
            return wgs_lat, wgs_lng
        except ImportError:
            st.warning("utils.py 未找到，使用原始坐标 (假设为 WGS-84)")
            return lat, lng
    else:
        return lat, lng

latA_w, lngA_w = to_wgs84(st.session_state.pointA["lat"], st.session_state.pointA["lng"], st.session_state.coord_type)
latB_w, lngB_w = to_wgs84(st.session_state.pointB["lat"], st.session_state.pointB["lng"], st.session_state.coord_type)

obstacles_wgs = []
for obs in st.session_state.obstacles:
    lat_o, lng_o = to_wgs84(obs["lat"], obs["lng"], st.session_state.coord_type)
    obstacles_wgs.append({
        "lat": lat_o, "lng": lng_o,
        "radius": obs["radius"], "height": obs["height"]
    })

# 生成 HTML (Leaflet + 3D 倾斜 + OSM)
map_html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="initial-scale=1, user-scalable=no">
    <title>3D 航线规划</title>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <link rel="stylesheet" href="https://unpkg.com/leaflet-control-3d@1.0.0/dist/leaflet-control-3d.css" />
    <style>
        body {{ margin: 0; padding: 0; }}
        #map {{ position: absolute; top: 0; bottom: 0; width: 100%; height: 100%; }}
        .controls-note {{
            position: absolute;
            bottom: 20px;
            left: 20px;
            background: rgba(0,0,0,0.6);
            color: #ccc;
            padding: 6px 12px;
            border-radius: 6px;
            font-family: sans-serif;
            font-size: 12px;
            z-index: 100;
            pointer-events: none;
        }}
    </style>
</head>
<body>
    <div id="map"></div>
    <div class="controls-note">
        🖱️ 鼠标拖拽旋转视角 | 滚轮缩放 (3D 效果)
    </div>

    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script src="https://unpkg.com/leaflet-control-3d@1.0.0/dist/leaflet-control-3d.min.js"></script>
    
    <script>
        // 地图初始化
        var map = L.map('map').setView([{(latA_w + latB_w)/2}, {(lngA_w + lngB_w)/2}], 16);
        
        // 添加 OpenStreetMap 瓦片 (稳定)
        L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a> contributors',
            maxZoom: 19
        }}).addTo(map);
        
        // 启用 3D 倾斜控制 (提供视角倾斜)
        map.control3D = new L.Control3D().addTo(map);
        map.control3D.setPitch(60);  // 设置倾斜角度
        
        // 起点 A 标记
        var markerA = L.marker([{latA_w}, {lngA_w}], {{ 
            icon: L.divIcon({{
                html: '<div style="background-color:#2ecc71; width:20px; height:20px; border-radius:50%; border:2px solid white;"></div>',
                iconSize: [20,20],
                className: 'marker-a'
            }})
        }}).addTo(map);
        markerA.bindPopup("<b>起点 A</b><br>" + {latA_w:.6f} + ", " + {lngA_w:.6f});
        
        // 终点 B 标记
        var markerB = L.marker([{latB_w}, {lngB_w}], {{
            icon: L.divIcon({{
                html: '<div style="background-color:#e74c3c; width:20px; height:20px; border-radius:50%; border:2px solid white;"></div>',
                iconSize: [20,20],
                className: 'marker-b'
            }})
        }}).addTo(map);
        markerB.bindPopup("<b>终点 B</b><br>" + {latB_w:.6f} + ", " + {lngB_w:.6f});
        
        // 航线 (虚线)
        var routeLine = L.polyline([[{latA_w}, {lngA_w}], [{latB_w}, {lngB_w}]], {{
            color: '#3498db',
            weight: 5,
            opacity: 0.8,
            dashArray: '8, 8'
        }}).addTo(map);
        
        // 障碍物 (圆形)
        var obstacles = {json.dumps(obstacles_wgs)};
        for (var i = 0; i < obstacles.length; i++) {{
            var obs = obstacles[i];
            var circle = L.circle([obs.lat, obs.lng], {{
                radius: obs.radius,
                color: '#f39c12',
                fillColor: '#f39c12',
                fillOpacity: 0.4,
                weight: 2
            }}).addTo(map);
            circle.bindPopup(`<b>障碍物</b><br>高度: ${{obs.height}} m`);
        }}
        
        // 飞行高度标注 (中点)
        var midLat = ({latA_w} + {latB_w}) / 2;
        var midLng = ({lngA_w} + {lngB_w}) / 2;
        var heightLabel = L.marker([midLat, midLng], {{
            icon: L.divIcon({{
                html: `<div style="background:rgba(0,0,0,0.7); color:white; padding:4px 12px; border-radius:20px; border:1px solid #3498db;">✈️ 飞行高度: {st.session_state.flight_height} m</div>`,
                iconSize: [150, 30],
                className: 'height-label'
            }})
        }}).addTo(map);
        
        // 重新调整地图视角以适应所有点
        var bounds = L.latLngBounds([[{latA_w}, {lngA_w}], [{latB_w}, {lngB_w}]]);
        for (var j = 0; j < obstacles.length; j++) {{
            bounds.extend([obstacles[j].lat, obstacles[j].lng]);
        }}
        map.fitBounds(bounds, {{ padding: [50, 50] }});
        
        // 保持倾斜角度
        setTimeout(function() {{
            if (map.control3D) map.control3D.setPitch(60);
        }}, 500);
    </script>
</body>
</html>
"""

st.components.v1.html(map_html, height=700, scrolling=False)

st.subheader("当前规划数据")
colA, colB, colH = st.columns(3)
colA.metric("起点 A", f"({st.session_state.pointA['lat']:.6f}, {st.session_state.pointA['lng']:.6f})")
colB.metric("终点 B", f"({st.session_state.pointB['lat']:.6f}, {st.session_state.pointB['lng']:.6f})")
colH.metric("飞行高度", f"{st.session_state.flight_height} 米")
st.caption(f"输入坐标系: {st.session_state.coord_type}  →  地图显示已自动转换至WGS-84")
st.info("💡 提示：使用 Leaflet 地图 + 3D 倾斜视角。橙色圆形为障碍物，蓝色虚线为航线。")
