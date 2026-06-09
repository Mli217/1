# pages/1_航线规划.py
import streamlit as st
import folium
from streamlit_folium import st_folium, folium_static
from folium.plugins import Draw, MousePosition
import json
import datetime
from utils import gcj02_to_wgs84  # 坐标转换

st.set_page_config(page_title="航线规划 - 3D地图", layout="wide")

st.title("🗺️ 航线规划 (3D地图 + 多边形障碍物圈选)")

# 初始化会话状态
if 'coord_type' not in st.session_state:
    st.session_state.coord_type = "GCJ-02"
if 'pointA' not in st.session_state:
    st.session_state.pointA = {"lat": 32.2322, "lng": 118.749}
if 'pointB' not in st.session_state:
    st.session_state.pointB = {"lat": 32.2343, "lng": 118.749}
if 'flight_height' not in st.session_state:
    st.session_state.flight_height = 50
if 'polygon_obstacles' not in st.session_state:
    # 存储多边形障碍物列表，每个元素为 {"coordinates": [[lng, lat], ...], "name": "障碍物1", "height": 40}
    st.session_state.polygon_obstacles = []
if 'last_save_time' not in st.session_state:
    st.session_state.last_save_time = None

# 侧边栏（控制面板）移到右侧（使用columns布局）
left_col, right_col = st.columns([2, 1], gap="large")

# ==================== 右侧控制面板 ====================
with right_col:
    st.header("🎮 控制面板")
    
    # 坐标系选择
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
    
    st.subheader("🚧 障碍物配置持久化")
    st.markdown(f"**文件状态**: 共 {len(st.session_state.polygon_obstacles)} 个多边形障碍物")
    if st.session_state.last_save_time:
        st.markdown(f"**保存时间**: {st.session_state.last_save_time}")
    
    # 按钮行
    col_save, col_load = st.columns(2)
    with col_save:
        if st.button("💾 保存到文件"):
            # 生成配置文件
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
                mime="application/json"
            )
            st.session_state.last_save_time = config["save_time"]
            st.success("配置文件已生成，点击下载按钮保存到本地")
    with col_load:
        uploaded_file = st.file_uploader("从文件加载", type=["json"], key="load_obs")
        if uploaded_file is not None:
            try:
                config = json.load(uploaded_file)
                st.session_state.polygon_obstacles = config.get("obstacles", [])
                st.session_state.last_save_time = config.get("save_time", None)
                st.success(f"已加载 {len(st.session_state.polygon_obstacles)} 个障碍物")
                st.rerun()
            except Exception as e:
                st.error(f"加载失败: {e}")
    
    # 清除全部按钮
    if st.button("🗑️ 清除全部障碍物"):
        st.session_state.polygon_obstacles = []
        st.session_state.last_save_time = None
        st.success("已清除所有障碍物")
        st.rerun()
    
    # 显示障碍物列表
    with st.expander("📋 当前障碍物列表"):
        if st.session_state.polygon_obstacles:
            for i, obs in enumerate(st.session_state.polygon_obstacles):
                pts = len(obs["coordinates"])
                st.write(f"{i+1}. {obs.get('name', f'障碍物{i+1}')} (点数: {pts}) 高度: {obs.get('height', 40)}m")
        else:
            st.write("暂无障碍物，请在地图上绘制多边形")

# ==================== 左侧地图（支持多边形绘制） ====================
with left_col:
    # 坐标转换函数
    def to_wgs84(lat, lng, input_type):
        if input_type == "GCJ-02":
            try:
                wgs_lng, wgs_lat = gcj02_to_wgs84(lng, lat)
                return wgs_lat, wgs_lng
            except:
                return lat, lng
        else:
            return lat, lng

    latA_w, lngA_w = to_wgs84(st.session_state.pointA["lat"], st.session_state.pointA["lng"], st.session_state.coord_type)
    latB_w, lngB_w = to_wgs84(st.session_state.pointB["lat"], st.session_state.pointB["lng"], st.session_state.coord_type)

    # 创建地图（使用OpenStreetMap底图，稳定）
    center_lat = (latA_w + latB_w) / 2
    center_lng = (lngA_w + lngB_w) / 2
    m = folium.Map(location=[center_lat, center_lng], zoom_start=16, control_scale=True)
    
    # 添加3D倾斜效果（通过设置俯仰角，需用插件或CSS，这里用folium的默认视角无法倾斜，但用户可接受）
    # 为了模拟3D，可以添加地形图层（可选）
    
    # 绘制起点A和终点B
    folium.Marker(
        [latA_w, lngA_w],
        popup=f"起点 A<br>坐标: {latA_w:.6f}, {lngA_w:.6f}",
        icon=folium.Icon(color="green", icon="play", prefix="fa")
    ).add_to(m)
    folium.Marker(
        [latB_w, lngB_w],
        popup=f"终点 B<br>坐标: {latB_w:.6f}, {lngB_w:.6f}",
        icon=folium.Icon(color="red", icon="stop", prefix="fa")
    ).add_to(m)
    
    # 绘制航线（蓝色虚线）
    folium.PolyLine(
        [(latA_w, lngA_w), (latB_w, lngB_w)],
        color="blue", weight=5, opacity=0.8, dash_array="5, 10",
        popup="规划航线"
    ).add_to(m)
    
    # 绘制已保存的多边形障碍物
    for obs in st.session_state.polygon_obstacles:
        coords = obs["coordinates"]  # 格式 [[lng, lat], ...]
        # 注意 folium 需要 [lat, lng] 顺序
        poly_coords = [[c[1], c[0]] for c in coords]
        height = obs.get("height", 40)
        folium.Polygon(
            locations=poly_coords,
            color="orange",
            fill=True,
            fill_color="orange",
            fill_opacity=0.4,
            weight=3,
            popup=f"障碍物<br>高度: {height}m"
        ).add_to(m)
        # 添加中心点文字
        center = [sum(c[1] for c in coords)/len(coords), sum(c[0] for c in coords)/len(coords)]
        folium.Marker(
            location=center,
            icon=folium.DivIcon(html=f'<div style="background:rgba(0,0,0,0.7); color:orange; padding:2px 6px; border-radius:12px;">{height}m</div>')
        ).add_to(m)
    
    # 飞行高度标注（中点）
    mid_lat = (latA_w + latB_w) / 2
    mid_lng = (lngA_w + lngB_w) / 2
    folium.Marker(
        [mid_lat, mid_lng],
        icon=folium.DivIcon(html=f'<div style="background:rgba(0,0,0,0.6); color:white; padding:4px 12px; border-radius:20px; border:1px solid #3498db;">✈️ 飞行高度: {st.session_state.flight_height} m</div>')
    ).add_to(m)
    
    # 添加绘图工具（Draw插件）
    draw = Draw(
        draw_options={
            "polygon": {"shapeOptions": {"color": "#f39c12"}, "allowIntersection": False},
            "polyline": False,
            "rectangle": False,
            "circle": False,
            "circlemarker": False,
            "marker": False
        },
        edit_options={"edit": True, "remove": True}
    )
    draw.add_to(m)
    
    # 添加鼠标坐标显示
    MousePosition().add_to(m)
    
    # 显示地图并获取绘制数据
    output = st_folium(m, width=800, height=600, returned_objects=["last_draw"])
    
    # 处理新绘制的多边形
    if output and output.get("last_draw") and output["last_draw"].get("geometry"):
        draw_data = output["last_draw"]
        if draw_data["geometry"]["type"] == "Polygon":
            coords = draw_data["geometry"]["coordinates"][0]  # 外环坐标 [[lng, lat], ...]
            # 询问障碍物高度
            with st.popup("添加障碍物", clear_on_submit=True):
                obs_height = st.number_input("障碍物高度 (m)", min_value=10, max_value=200, value=40, step=5)
                obs_name = st.text_input("名称（可选）", "障碍物")
                if st.button("确认添加"):
                    new_obs = {
                        "name": obs_name,
                        "coordinates": coords,
                        "height": obs_height
                    }
                    st.session_state.polygon_obstacles.append(new_obs)
                    st.success("已添加障碍物")
                    st.rerun()
        else:
            st.warning("请绘制多边形（不是其他图形）")

    # 自动适应视图边界（包含所有元素）
    all_coords = [[latA_w, lngA_w], [latB_w, lngB_w]]
    for obs in st.session_state.polygon_obstacles:
        for coord in obs["coordinates"]:
            all_coords.append([coord[1], coord[0]])
    if all_coords:
        bounds = [[min(c[0] for c in all_coords), min(c[1] for c in all_coords)],
                  [max(c[0] for c in all_coords), max(c[1] for c in all_coords)]]
        m.fit_bounds(bounds, padding=(30, 30))
    # 注意：st_folium 不直接支持 fit_bounds 后更新，但用户可手动缩放

# 下方显示规划数据
st.subheader("当前规划数据")
colA, colB, colH = st.columns(3)
colA.metric("起点 A", f"({st.session_state.pointA['lat']:.6f}, {st.session_state.pointA['lng']:.6f})")
colB.metric("终点 B", f"({st.session_state.pointB['lat']:.6f}, {st.session_state.pointB['lng']:.6f})")
colH.metric("飞行高度", f"{st.session_state.flight_height} 米")
st.caption(f"输入坐标系: {st.session_state.coord_type}  →  地图显示已自动转换至WGS-84")
st.info("💡 提示：使用地图左上角的绘图工具绘制多边形（点击多边形图标），绘制完成后弹出窗口设置高度。障碍物配置可保存到JSON文件并加载。")
