# pages/1_航线规划.py
import streamlit as st
import json

st.set_page_config(page_title="航线规划 - 3D卫星地图", layout="wide")
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

# 坐标转换（WGS-84 ↔ GCJ-02）
def to_wgs84(lat, lng, input_type):
    if input_type == "GCJ-02":
        try:
            from utils import gcj02_to_wgs84
            wgs_lng, wgs_lat = gcj02_to_wgs84(lng, lat)
            return wgs_lat, wgs_lng
        except ImportError:
            st.warning("utils.py 未找到，坐标不转换")
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

# 生成 HTML（ArcGIS 卫星底图 + 3D 倾斜）
map_html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="initial-scale=1, user-scalable=no">
    <title>3D 卫星航线规划</title>
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
        🖱️ 鼠标拖拽旋转视角 | 右键拖拽平移 | 滚轮缩放 (3D 卫星地图)
    </div>
    <script>
        // 卫星影像源 (ArcGIS World Imagery)
        const satelliteSource = {{
            type: 'raster',
            tiles: [
                'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{{z}}/{{y}}/{{x}}',
                'https://services.arcgisonline.com/arcgis/rest/services/World_Imagery/MapServer/tile/{{z}}/{{y}}/{{x}}'
            ],
            tileSize: 256,
            attribution: 'Esri & Contributors'
        }};
        
        // 备用街道底图 (当卫星图加载失败时回退)
        const streetSource = {{
            type: 'raster',
            tiles: [
                'https://a.basemaps.cartocdn.com/light_all/{{z}}/{{x}}/{{y}}.png',
                'https://b.basemaps.cartocdn.com/light_all/{{z}}/{{x}}/{{y}}.png'
            ],
            tileSize: 256,
            attribution: 'CartoDB'
        }};

        const map = new maplibregl.Map({{
            container: 'map',
            style: {{
                version: 8,
                sources: {{
                    'satellite': satelliteSource
                }},
                layers: [{{
                    id: 'satellite',
                    type: 'raster',
                    source: 'satellite',
                    minzoom: 0,
                    maxzoom: 18
                }}]
            }},
            center: [{(lngA_w + lngB_w)/2}, {(latA_w + latB_w)/2}],
            zoom: 16,
            pitch: 60,
            bearing: 0
        }});

        // 监听卫星图加载错误，自动切换到街道底图
        map.on('sourcedata', (e) => {{
            if (e.sourceId === 'satellite' && e.sourceDataType === 'metadata') {{
                // 尝试加载第一个瓦片，如果失败则切换
                setTimeout(() => {{
                    const style = map.getStyle();
                    if (style && style.sources && style.sources.satellite) {{
                        // 不做额外处理，依靠 tiles 多URL自动重试
                    }}
                }}, 2000);
            }}
        }});
        
        // 如果卫星图瓦片加载错误（网络问题），回退到街道图
        map.on('error', (e) => {{
            if (e.error && e.error.status === 404) {{
                console.warn('卫星图加载失败，切换到街道底图');
                map.getStyle().sources.satellite = streetSource;
                map.setStyle({{
                    version: 8,
                    sources: {{ 'street': streetSource }},
                    layers: [{{ id: 'street', type: 'raster', source: 'street' }}]
                }});
            }}
        }});

        map.on('load', () => {{
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

st.subheader("当前规划数据")
colA, colB, colH = st.columns(3)
colA.metric("起点 A", f"({st.session_state.pointA['lat']:.6f}, {st.session_state.pointA['lng']:.6f})")
colB.metric("终点 B", f"({st.session_state.pointB['lat']:.6f}, {st.session_state.pointB['lng']:.6f})")
colH.metric("飞行高度", f"{st.session_state.flight_height} 米")
st.caption(f"输入坐标系: {st.session_state.coord_type}  →  地图显示已自动转换至WGS-84")
st.info("💡 提示：地图为 ArcGIS 卫星影像，支持 3D 倾斜视角。橙色圆点为障碍物，蓝色虚线为航线。若卫星图加载失败，会自动切换至街道底图。")
