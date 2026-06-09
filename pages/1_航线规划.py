# pages/1_航线规划.py (修改版：地图左侧，控制面板右侧)
import streamlit as st
import json

# 注意：如果主入口 app.py 已设置 set_page_config，这里应删除或注释掉下面一行，避免冲突
# st.set_page_config(page_title="航线规划 - 3D地图", layout="wide")

# 动态标题
coord_type_display = st.session_state.get('coord_type', 'GCJ-02')
if coord_type_display == "GCJ-02":
    st.title("🗺️ 航线规划 (GCJ-02 卫星3D地图 + 障碍物)")
else:
    st.title("🗺️ 航线规划 (WGS-84 街道3D地图 + 障碍物)")

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

# 使用左右两列布局：左边地图，右边控制面板
left_col, right_col = st.columns([2, 1], gap="large")

# ==================== 右侧控制面板 ====================
with right_col:
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

# ==================== 左侧地图 ====================
with left_col:
    # 坐标转换函数
    def to_wgs84(lat, lng, input_type):
        if input_type == "GCJ-02":
            try:
                from utils import gcj02_to_wgs84
                wgs_lng, wgs_lat = gcj02_to_wgs84(lng, lat)
                return wgs_lat, wgs_lng
            except ImportError:
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

    # 根据坐标系选择底图样式
    if st.session_state.coord_type == "GCJ-02":
        map_style = {
            "version": 8,
            "sources": {
                "satellite": {
                    "type": "raster",
                    "tiles": [
                        "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
                        "https://services.arcgisonline.com/arcgis/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
                    ],
                    "tileSize": 256,
                    "attribution": "Esri & Contributors"
                }
            },
            "layers": [{"id": "satellite", "type": "raster", "source": "satellite"}]
        }
        map_info = "3D 卫星影像地图"
    else:
        map_style = {
            "version": 8,
            "sources": {
                "street": {
                    "type": "raster",
                    "tiles": [
                        "https://a.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png",
                        "https://b.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png",
                        "https://c.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png",
                        "https://d.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png"
                    ],
                    "tileSize": 256,
                    "attribution": "CartoDB"
                }
            },
            "layers": [{"id": "street", "type": "raster", "source": "street"}]
        }
        map_info = "3D 街道地图"

    # 收集所有坐标点用于自动适配边界
    all_points = [[lngA_w, latA_w], [lngB_w, latB_w]]
    for obs in obstacles_wgs:
        all_points.append([obs["lng"], obs["lat"]])

    lngs = [p[0] for p in all_points]
    lats = [p[1] for p in all_points]
    min_lng, max_lng = min(lngs), max(lngs)
    min_lat, max_lat = min(lats), max(lats)
    padding = 0.002
    bounds = [[min_lng - padding, min_lat - padding], [max_lng + padding, max_lat + padding]]

    # 生成地图 HTML
    map_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="initial-scale=1, user-scalable=no">
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
        <link href="https://unpkg.com/maplibre-gl@3.6.2/dist/maplibre-gl.css" rel="stylesheet" />
        <script src="https://unpkg.com/maplibre-gl@3.6.2/dist/maplibre-gl.js"></script>
    </head>
    <body>
        <div id="map"></div>
        <div class="controls-note">
            🖱️ 鼠标拖拽旋转视角 | 右键拖拽平移 | 滚轮缩放 (3D 效果) | 当前底图: {map_info}
        </div>
        <script>
            const map = new maplibregl.Map({{
                container: 'map',
                style: {json.dumps(map_style)},
                center: [{(lngA_w + lngB_w)/2}, {(latA_w + latB_w)/2}],
                zoom: 16,
                pitch: 60,
                bearing: 0
            }});

            map.on('load', () => {{
                // 自动适配视图到所有要素（A、B、障碍物）
                const bounds = {json.dumps(bounds)};
                map.fitBounds(bounds, {{ padding: 50, duration: 0 }});
                
                // 起点 A
                new maplibregl.Marker({{ color: '#2ecc71', scale: 1.2 }})
                    .setLngLat([{lngA_w}, {latA_w}])
                    .setPopup(new maplibregl.Popup().setHTML('<b>起点 A</b><br/>' + {latA_w:.6f} + ', ' + {lngA_w:.6f}))
                    .addTo(map);
                
                // 终点 B
                new maplibregl.Marker({{ color: '#e74c3c', scale: 1.2 }})
                    .setLngLat([{lngB_w}, {latB_w}])
                    .setPopup(new maplibregl.Popup().setHTML('<b>终点 B</b><br/>' + {latB_w:.6f} + ', ' + {lngB_w:.6f}))
                    .addTo(map);
                
                // 航线 (虚线)
                map.addSource('route', {{
                    type: 'geojson',
                    data: {{
                        type: 'Feature',
                        geometry: {{
                            type: 'LineString',
                            coordinates: [[{lngA_w}, {latA_w}], [{lngB_w}, {latB_w}]]
                        }}
                    }}
                }});
                map.addLayer({{
                    id: 'route-line',
                    type: 'line',
                    source: 'route',
                    layout: {{ 'line-join': 'round', 'line-cap': 'round' }},
                    paint: {{
                        'line-color': '#3498db',
                        'line-width': 5,
                        'line-opacity': 0.9,
                        'line-dasharray': [2, 2]
                    }}
                }});
                
                // 障碍物 (圆形)
                const obstacles = {json.dumps(obstacles_wgs)};
                obstacles.forEach(obs => {{
                    map.addSource(`obs-${{obs.lng}}-${{obs.lat}}`, {{
                        type: 'geojson',
                        data: {{
                            type: 'Feature',
                            geometry: {{
                                type: 'Point',
                                coordinates: [obs.lng, obs.lat]
                            }}
                        }}
                    }});
                    map.addLayer({{
                        id: `obs-circle-${{obs.lng}}-${{obs.lat}}`,
                        type: 'circle',
                        source: `obs-${{obs.lng}}-${{obs.lat}}`,
                        paint: {{
                            'circle-radius': obs.radius / 2,
                            'circle-color': '#f39c12',
                            'circle-opacity': 0.5,
                            'circle-stroke-width': 2,
                            'circle-stroke-color': '#e67e22'
                        }}
                    }});
                    
                    const popup = new maplibregl.Popup({{ offset: 25 }})
                        .setHTML(`<div style="background:#000;color:#ffaa44;padding:4px;">⚠️ 障碍物<br/>高 ${{obs.height}} m</div>`);
                    new maplibregl.Marker({{ element: document.createElement('div') }})
                        .setLngLat([obs.lng, obs.lat])
                        .setPopup(popup)
                        .addTo(map);
                }});
                
                // 飞行高度标注
                const midLng = ({lngA_w} + {lngB_w}) / 2;
                const midLat = ({latA_w} + {latB_w}) / 2;
                const div = document.createElement('div');
                div.innerHTML = `✈️ 飞行高度: {st.session_state.flight_height} m`;
                div.style.backgroundColor = 'rgba(0,0,0,0.7)';
                div.style.color = '#fff';
                div.style.padding = '4px 12px';
                div.style.borderRadius = '20px';
                div.style.fontSize = '14px';
                div.style.border = '1px solid #3498db';
                new maplibregl.Marker({{ element: div }})
                    .setLngLat([midLng, midLat])
                    .addTo(map);
            }});
        </script>
    </body>
    </html>
    """
    st.components.v1.html(map_html, height=700, scrolling=False)

# 下方显示当前规划数据
st.subheader("当前规划数据")
colA, colB, colH = st.columns(3)
colA.metric("起点 A", f"({st.session_state.pointA['lat']:.6f}, {st.session_state.pointA['lng']:.6f})")
colB.metric("终点 B", f"({st.session_state.pointB['lat']:.6f}, {st.session_state.pointB['lng']:.6f})")
colH.metric("飞行高度", f"{st.session_state.flight_height} 米")
st.caption(f"输入坐标系: {st.session_state.coord_type}  →  地图显示已自动转换至WGS-84")
st.info("💡 提示：地图打开时会自动缩放至包含所有航点和障碍物的区域。选择 WGS-84 显示街道地图，选择 GCJ-02 显示卫星影像地图。")
