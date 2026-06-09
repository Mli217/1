import streamlit as st
import json
from utils import gcj02_to_wgs84

st.title("🗺️ 航线规划 (3D卫星地图 + 障碍物)")

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
        lng_w, lat_w = gcj02_to_wgs84(lng, lat)
        return lat_w, lng_w
    return lat, lng

latA_w, lngA_w = to_wgs84(st.session_state.pointA["lat"], st.session_state.pointA["lng"], st.session_state.coord_type)
latB_w, lngB_w = to_wgs84(st.session_state.pointB["lat"], st.session_state.pointB["lng"], st.session_state.coord_type)

obstacles_wgs = []
for obs in st.session_state.obstacles:
    lat_o, lng_o = to_wgs84(obs["lat"], obs["lng"], st.session_state.coord_type)
    obstacles_wgs.append({"lat": lat_o, "lng": lng_o, "radius": obs["radius"], "height": obs["height"]})

# 生成地图 HTML（使用 CartoDB 底图，稳定）
map_html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="initial-scale=1, user-scalable=no">
    <style> body {{ margin: 0; padding: 0; }} #map {{ position: absolute; top: 0; bottom: 0; width: 100%; height: 100%; }} </style>
    <link href="https://unpkg.com/maplibre-gl@3.6.2/dist/maplibre-gl.css" rel="stylesheet" />
    <script src="https://unpkg.com/maplibre-gl@3.6.2/dist/maplibre-gl.js"></script>
</head>
<body>
    <div id="map"></div>
    <script>
        const map = new maplibregl.Map({{
            container: 'map',
            style: {{
                version: 8,
                sources: {{
                    'cartodb': {{
                        type: 'raster',
                        tiles: ['https://a.basemaps.cartocdn.com/light_all/{{z}}/{{x}}/{{y}}.png'],
                        tileSize: 256,
                        attribution: 'CartoDB'
                    }}
                }},
                layers: [{{ 'id': 'cartodb', 'type': 'raster', 'source': 'cartodb' }}]
            }},
            center: [{(lngA_w + lngB_w)/2}, {(latA_w + latB_w)/2}],
            zoom: 16,
            pitch: 60
        }});
        map.on('load', () => {{
            new maplibregl.Marker({{ color: '#2ecc71' }}).setLngLat([{lngA_w}, {latA_w}]).setPopup(new maplibregl.Popup().setHTML('起点 A')).addTo(map);
            new maplibregl.Marker({{ color: '#e74c3c' }}).setLngLat([{lngB_w}, {latB_w}]).setPopup(new maplibregl.Popup().setHTML('终点 B')).addTo(map);
            map.addSource('route', {{ type: 'geojson', data: {{ type: 'Feature', geometry: {{ type: 'LineString', coordinates: [[{lngA_w}, {latA_w}], [{lngB_w}, {latB_w}]] }} }} }});
            map.addLayer({{ id: 'route', type: 'line', source: 'route', paint: {{ 'line-color': '#3498db', 'line-width': 5, 'line-dasharray': [2,2] }} }});
            const obs = {json.dumps(obstacles_wgs)};
            obs.forEach(o => {{
                map.addSource(`obs-${{o.lng}}`, {{ type: 'geojson', data: {{ type: 'Feature', geometry: {{ type: 'Point', coordinates: [o.lng, o.lat] }} }} }});
                map.addLayer({{ id: `obs-${{o.lng}}`, type: 'circle', source: `obs-${{o.lng}}`, paint: {{ 'circle-radius': o.radius/2, 'circle-color': '#f39c12', 'circle-opacity': 0.5 }} }});
            }});
        }});
    </script>
</body>
</html>
"""
st.components.v1.html(map_html, height=600)
