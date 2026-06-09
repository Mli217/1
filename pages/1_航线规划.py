# pages/1_航线规划.py
import streamlit as st
import json
from utils import gcj02_to_wgs84

st.set_page_config(page_title="航线规划 - 高德3D地图", layout="wide")
st.title("🗺️ 航线规划 (高德3D地图 + 障碍物)")

# 高德地图 API Key（替换成你自己的）
AMAP_KEY = "9bc3e8486433e66906e4112f9b69223b"

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

# 坐标转换：用户输入的坐标系 -> 高德API使用的GCJ-02
def to_gcj02(lat, lng, input_type):
    if input_type == "WGS-84":
        from utils import wgs84_to_gcj02
        lng_gcj, lat_gcj = wgs84_to_gcj02(lng, lat)
        return lat_gcj, lng_gcj
    else:
        return lat, lng

latA_gcj, lngA_gcj = to_gcj02(st.session_state.pointA["lat"], st.session_state.pointA["lng"], st.session_state.coord_type)
latB_gcj, lngB_gcj = to_gcj02(st.session_state.pointB["lat"], st.session_state.pointB["lng"], st.session_state.coord_type)

# 障碍物坐标也统一转为GCJ-02
obstacles_gcj = []
for obs in st.session_state.obstacles:
    lat_obs, lng_obs = to_gcj02(obs["lat"], obs["lng"], st.session_state.coord_type)
    obstacles_gcj.append({
        "lat": lat_obs, "lng": lng_obs,
        "radius": obs["radius"], "height": obs["height"]
    })

# 计算地图中心点
center_lat = (latA_gcj + latB_gcj) / 2
center_lng = (lngA_gcj + lngB_gcj) / 2

# 生成嵌入高德地图的 HTML（支持3D视角、倾斜、旋转）
map_html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta http-equiv="Content-Type" content="text/html; charset=utf-8">
    <meta name="viewport" content="initial-scale=1.0, user-scalable=no">
    <style>
        body, html {{ margin: 0; padding: 0; height: 100%; width: 100%; }}
        #container {{ height: 100%; width: 100%; }}
    </style>
</head>
<body>
    <div id="container"></div>
    <script type="text/javascript"
        src="https://webapi.amap.com/maps?v=2.0&key={AMAP_KEY}"></script>
    <script>
        // 创建地图
        var map = new AMap.Map('container', {{
            center: [{center_lng}, {center_lat}],
            zoom: 17,
            pitch: 60,          // 俯仰角（3D效果）
            viewMode: '3D',     // 3D模式
            rotation: 0,
            resizeEnable: true
        }});
        
        // 添加A点标记（绿色）
        var markerA = new AMap.Marker({{
            position: [{lngA_gcj}, {latA_gcj}],
            title: '起点 A',
            label: {{
                content: '<div style="background: #2ecc71; color: white; padding: 4px 8px; border-radius: 4px;">A</div>',
                offset: new AMap.Pixel(0, -25)
            }},
            icon: 'https://webapi.amap.com/theme/v1.3/markers/n/mark_b.png'
        }});
        map.add(markerA);
        
        // 添加B点标记（红色）
        var markerB = new AMap.Marker({{
            position: [{lngB_gcj}, {latB_gcj}],
            title: '终点 B',
            label: {{
                content: '<div style="background: #e74c3c; color: white; padding: 4px 8px; border-radius: 4px;">B</div>',
                offset: new AMap.Pixel(0, -25)
            }},
            icon: 'https://webapi.amap.com/theme/v1.3/markers/n/mark_r.png'
        }});
        map.add(markerB);
        
        // 绘制航线（蓝色折线）
        var line = new AMap.Polyline({{
            path: [[{lngA_gcj}, {latA_gcj}], [{lngB_gcj}, {latB_gcj}]],
            strokeColor: '#3498db',
            strokeWeight: 6,
            strokeOpacity: 0.8,
            strokeStyle: 'solid'
        }});
        map.add(line);
        
        // 添加障碍物（圆柱体效果：使用圆+多边形模拟，无法在3D中直接画圆柱，使用圆圈+半透明填充）
        var obstacles = {json.dumps(obstacles_gcj)};
        for (var i = 0; i < obstacles.length; i++) {{
            var obs = obstacles[i];
            var circle = new AMap.Circle({{
                center: [obs.lng, obs.lat],
                radius: obs.radius,
                fillColor: '#f39c12',
                fillOpacity: 0.4,
                strokeColor: '#e67e22',
                strokeOpacity: 0.8,
                strokeWeight: 2
            }});
            circle.setMap(map);
            // 添加文字标注显示高度
            var text = new AMap.Text({{
                text: '⚠️ 障碍物\\n高' + obs.height + 'm',
                anchor: 'center',
                position: [obs.lng, obs.lat],
                style: {{
                    'background-color': 'rgba(0,0,0,0.6)',
                    'border': 'none',
                    'color': 'white',
                    'padding': '4px 8px',
                    'font-size': '12px',
                    'border-radius': '4px'
                }}
            }});
            text.setMap(map);
        }}
        
        // 可选：添加测距工具或缩放控件
        map.addControl(new AMap.ToolBar());
        map.addControl(new AMap.Scale());
    </script>
</body>
</html>
"""

# 嵌入HTML地图（宽度100%，高度600px）
st.components.v1.html(map_html, height=600, scrolling=False)

# 显示规划数据
st.subheader("当前规划数据")
colA, colB, colH = st.columns(3)
colA.metric("起点 A", f"({st.session_state.pointA['lat']:.6f}, {st.session_state.pointA['lng']:.6f})")
colB.metric("终点 B", f"({st.session_state.pointB['lat']:.6f}, {st.session_state.pointB['lng']:.6f})")
colH.metric("飞行高度", f"{st.session_state.flight_height} 米")
st.caption(f"输入坐标系: {st.session_state.coord_type}  →  地图显示已自动转换至GCJ-02（高德）")
st.info("💡 提示：地图支持鼠标拖拽旋转视角（按住右键拖动）、滚轮缩放。橙色圆形区域为障碍物。")
