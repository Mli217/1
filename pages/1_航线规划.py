import streamlit as st
import folium
from streamlit_folium import st_folium
from folium.plugins import Draw, MousePosition
import json
import datetime
from utils import gcj02_to_wgs84  # 保持你的工具函数

# 页面配置
st.set_page_config(page_title="航线规划 - 3D地图", layout="wide")

st.title("🗺️ 航线规划 (3D地图 + 多边形障碍物圈选)")

# ==================== 初始化状态 ====================
if 'coord_type' not in st.session_state:
    st.session_state.coord_type = "GCJ-02"
if 'pointA' not in st.session_state:
    st.session_state.pointA = {"lat": 32.2322, "lng": 118.749}
if 'pointB' not in st.session_state:
    st.session_state.pointB = {"lat": 32.2343, "lng": 118.749}
if 'flight_height' not in st.session_state:
    st.session_state.flight_height = 50
if 'polygon_obstacles' not in st.session_state:
    st.session_state.polygon_obstacles = []
if 'last_save_time' not in st.session_state:
    st.session_state.last_save_time = None
if 'pending_polygon' not in st.session_state:
    st.session_state.pending_polygon = None

# 坐标转换
def to_wgs84(lat, lng, input_type):
    if input_type == "GCJ-02":
        try:
            wgs_lng, wgs_lat = gcj02_to_wgs84(lng, lat)
            return wgs_lat, wgs_lng
        except:
            return lat, lng
    else:
        return lat, lng

# ==================== 布局定义（左地图，右控制面板） ====================
left_col, right_col = st.columns([3, 1.5])

# ==================== 右侧控制面板 ====================
with right_col:
    st.subheader("🎮 障碍物配置持久化")
    
    # 文件路径显示
    st.caption("配置文件：`C:\\Users\\77463\\obstacle_config.json` | 版本：v12.2 障碍物持久化版")
    st.caption("💡 文件保存在程序同目录下，绝对路径如上所示")
    
    st.divider()
    
    # 操作按钮行
    col_btn1, col_btn2 = st.columns(2)
    
    # 保存到文件
    with col_btn1:
        if st.button("💾 保存到文件", type="primary", use_container_width=True):
            config = {
                "version": "v12.2",
                "save_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "obstacles": st.session_state.polygon_obstacles
            }
            config_json = json.dumps(config, indent=2, ensure_ascii=False)
            st.download_button(
                label="📥 下载 obstacle_config.json",
                data=config_json,
                file_name="obstacle_config.json",
                mime="application/json",
                use_container_width=True
            )
            st.session_state.last_save_time = config["save_time"]
            st.success("配置文件已生成，请点击下载按钮保存")

    # 从文件加载
    with col_btn2:
        uploaded_file = st.file_uploader("📂 从文件加载", type=["json"], label_visibility="collapsed")
        if uploaded_file is not None:
            try:
                config = json.load(uploaded_file)
                st.session_state.polygon_obstacles = config.get("obstacles", [])
                st.session_state.last_save_time = config.get("save_time", None)
                st.success(f"已加载 {len(st.session_state.polygon_obstacles)} 个障碍物")
                st.rerun()
            except Exception as e:
                st.error(f"加载失败: {e}")
    
    # 清除与一键部署
    col_btn3, col_btn4 = st.columns([1, 1])
    with col_btn3:
        if st.button("🗑️ 清除全部", use_container_width=True):
            st.session_state.polygon_obstacles = []
            st.session_state.last_save_time = None
            st.success("已清除所有障碍物")
            st.rerun()
    with col_btn4:
        if st.button("⚡ 一键部署", type="primary", use_container_width=True):
            st.success("🚀 正在执行一键部署逻辑... (模拟)")
            # 在这里可以加入无人机实际发送指令的代码逻辑
    
    st.divider()
    
    # 下载区
    st.markdown("#### 📥 下载配置文件到本地")
    if st.session_state.polygon_obstacles:
        config_to_download = {
            "version": "v12.2",
            "save_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "obstacles": st.session_state.polygon_obstacles
        }
        st.download_button(
            label="⬇️ 下载 obstacle_config.json",
            data=json.dumps(config_to_download, indent=2, ensure_ascii=False),
            file_name="obstacle_config.json",
            mime="application/json",
            use_container_width=True
        )
    else:
        st.button("⬇️ 下载 obstacle_config.json (当前无障碍物)", disabled=True, use_container_width=True)
    
    st.markdown("点击下载即可将云端保存的障碍物配置保存到你的电脑")
    
    # 文件状态信息框（复刻截图样式）
    status_msg = f"📂 文件状态：共 {len(st.session_state.polygon_obstacles)} 个障碍物"
    if st.session_state.last_save_time:
        status_msg += f" | 保存时间：{st.session_state.last_save_time} | 版本：v12.2"
    else:
        status_msg += " | 暂未保存"
        
    st.info(status_msg)

    # 等待添加的新障碍物（绘制多边形后会在这里弹出来）
    if st.session_state.pending_polygon is not None:
        st.warning("✅ 在地图上检测到一个新绘制的多边形！请在下面确认配置：")
        with st.form(key="add_obs_form"):
            obs_name = st.text_input("障碍物名称", "障碍物")
            obs_height = st.number_input("高度 (m)", min_value=10, max_value=200, value=40, step=5)
            if st.form_submit_button("✅ 确认添加障碍物"):
                new_obs = {
                    "name": obs_name,
                    "coordinates": st.session_state.pending_polygon,
                    "height": obs_height
                }
                st.session_state.polygon_obstacles.append(new_obs)
                st.session_state.pending_polygon = None
                st.success("障碍物已添加！")
                st.rerun()

    # 当前列表总览
    with st.expander("📋 当前障碍物列表"):
        if st.session_state.polygon_obstacles:
            for i, obs in enumerate(st.session_state.polygon_obstacles):
                pts = len(obs["coordinates"])
                st.write(f"{i+1}. `{obs.get('name', f'障碍物{i+1}')}` (点数: {pts}) 高度: {obs.get('height', 40)}m")
        else:
            st.write("暂无障碍物，请在地图上绘制多边形")

# ==================== 左侧地图 ====================
with left_col:
    latA_w, lngA_w = to_wgs84(st.session_state.pointA["lat"], st.session_state.pointA["lng"], st.session_state.coord_type)
    latB_w, lngB_w = to_wgs84(st.session_state.pointB["lat"], st.session_state.pointB["lng"], st.session_state.coord_type)
    
    # 计算地图中心点
    center_lat = (latA_w + latB_w) / 2
    center_lng = (lngA_w + lngB_w) / 2
    
    # 初始化地图
    m = folium.Map(location=[center_lat, center_lng], zoom_start=16, control_scale=True)

    # 绘制 A/B 点和航线
    folium.Marker([latA_w, lngA_w], popup=f"起点 A<br>{latA_w:.6f}, {lngA_w:.6f}",
                  icon=folium.Icon(color="green", icon="play", prefix="fa")).add_to(m)
    folium.Marker([latB_w, lngB_w], popup=f"终点 B<br>{latB_w:.6f}, {lngB_w:.6f}",
                  icon=folium.Icon(color="red", icon="stop", prefix="fa")).add_to(m)
    
    folium.PolyLine([(latA_w, lngA_w), (latB_w, lngB_w)],
                    color="blue", weight=5, opacity=0.8, dash_array="5, 10").add_to(m)

    # 绘制已保存的障碍物
    for obs in st.session_state.polygon_obstacles:
        coords = obs["coordinates"]
        poly_coords = [[c[1], c[0]] for c in coords]  # [lng, lat] -> [lat, lng]
        height = obs.get("height", 40)
        folium.Polygon(locations=poly_coords, color="orange", fill=True,
                       fill_color="orange", fill_opacity=0.3, weight=3,
                       popup=f"高度: {height}m").add_to(m)
        # 中心高度标签
        cx = sum(c[0] for c in coords) / len(coords)
        cy = sum(c[1] for c in coords) / len(coords)
        folium.Marker([cy, cx], icon=folium.DivIcon(
            html=f'<div style="background:rgba(0,0,0,0.7); color:orange; padding:2px 6px; border-radius:12px;">{height}m</div>')).add_to(m)

    # 航线高度标注
    mid_lat = (latA_w + latB_w) / 2
    mid_lng = (lngA_w + lngB_w) / 2
    folium.Marker([mid_lat, mid_lng], icon=folium.DivIcon(
        html=f'<div style="background:rgba(0,0,0,0.6); color:white; padding:4px 12px; border-radius:20px; border:1px solid #3498db;">✈️ 飞行高度: {st.session_state.flight_height} m</div>')).add_to(m)

    # 绘图工具 (Draw)
    Draw(
        draw_options={
            "polygon": {"shapeOptions": {"color": "#f39c12"}, "allowIntersection": False},
            "polyline": False, "rectangle": False, "circle": False, "circlemarker": False, "marker": False
        },
        edit_options={"edit": True, "remove": True}
    ).add_to(m)
    MousePosition().add_to(m)

    # 自动调整视野（防崩溃处理）
    all_points = [[latA_w, lngA_w], [latB_w, lngB_w]]
    for obs in st.session_state.polygon_obstacles:
        for coord in obs["coordinates"]:
            all_points.append([coord[1], coord[0]])

    if all_points:
        try:
            m.fit_bounds([
                [min(p[0] for p in all_points), min(p[1] for p in all_points)],
                [max(p[0] for p in all_points), max(p[1] for p in all_points)]
            ])
        except:
            pass

    # 渲染地图
    output = st_folium(m, height=550, key="draw_map", returned_objects=["last_draw"])

    # 捕获新绘制的多边形（触发右侧表单显示）
    if output and output.get("last_draw") and output["last_draw"].get("geometry"):
        geom = output["last_draw"]["geometry"]
        if geom["type"] == "Polygon":
            coords = geom["coordinates"][0]
            st.session_state.pending_polygon = coords
            st.rerun()

# ==================== 底部信息栏 ====================
st.divider()
st.subheader("当前规划数据")
c1, c2, c3 = st.columns(3)
c1.metric("起点 A", f"({st.session_state.pointA['lat']:.6f}, {st.session_state.pointA['lng']:.6f})")
c2.metric("终点 B", f"({st.session_state.pointB['lat']:.6f}, {st.session_state.pointB['lng']:.6f})")
c3.metric("飞行高度", f"{st.session_state.flight_height} 米")
st.caption(f"输入坐标系: {st.session_state.coord_type}  →  地图显示已自动转换至WGS-84")
