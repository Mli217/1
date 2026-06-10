# pages/1_航线规划.py
import streamlit as st
import folium
from streamlit_folium import st_folium
from folium.plugins import Draw, MousePosition
import json
import datetime
import math
import time
from shapely.geometry import Polygon, Point, LineString

# ==================== 页面配置 ====================
st.set_page_config(page_title="航线规划 + 飞行监控", layout="wide")
st.title("🗺️ 航线规划 + 飞行监控 (智能避障)")

# ==================== 坐标转换（WGS-84 <-> GCJ-02）====================
def gcj02_to_wgs84(lng, lat):
    a = 6378245.0
    ee = 0.00669342162296594323
    if out_of_china(lng, lat):
        return lng, lat
    dlat = transform_lat(lng - 105.0, lat - 35.0)
    dlng = transform_lng(lng - 105.0, lat - 35.0)
    radlat = lat / 180.0 * math.pi
    magic = math.sin(radlat)
    magic = 1 - ee * magic * magic
    sqrtmagic = math.sqrt(magic)
    dlat = (dlat * 180.0) / ((a * (1 - ee)) / (magic * sqrtmagic) * math.pi)
    dlng = (dlng * 180.0) / (a / sqrtmagic * math.cos(radlat) * math.pi)
    return lng - dlng, lat - dlat

def wgs84_to_gcj02(lng, lat):
    a = 6378245.0
    ee = 0.00669342162296594323
    if out_of_china(lng, lat):
        return lng, lat
    dlat = transform_lat(lng - 105.0, lat - 35.0)
    dlng = transform_lng(lng - 105.0, lat - 35.0)
    radlat = lat / 180.0 * math.pi
    magic = math.sin(radlat)
    magic = 1 - ee * magic * magic
    sqrtmagic = math.sqrt(magic)
    dlat = (dlat * 180.0) / ((a * (1 - ee)) / (magic * sqrtmagic) * math.pi)
    dlng = (dlng * 180.0) / (a / sqrtmagic * math.cos(radlat) * math.pi)
    return lng + dlng, lat + dlat

def transform_lng(lng, lat):
    ret = 300.0 + lng + 2.0 * lat + 0.1 * lng * lng + 0.1 * lng * lat + 0.1 * math.sqrt(abs(lng))
    ret += (20.0 * math.sin(6.0 * lng * math.pi) + 20.0 * math.sin(2.0 * lng * math.pi)) * 2.0 / 3.0
    ret += (20.0 * math.sin(lng * math.pi) + 40.0 * math.sin(lng / 3.0 * math.pi)) * 2.0 / 3.0
    ret += (150.0 * math.sin(lng / 12.0 * math.pi) + 300.0 * math.sin(lng / 30.0 * math.pi)) * 2.0 / 3.0
    return ret

def transform_lat(lng, lat):
    ret = -100.0 + 2.0 * lng + 3.0 * lat + 0.2 * lat * lat + 0.1 * lng * lat + 0.2 * math.sqrt(abs(lng))
    ret += (20.0 * math.sin(6.0 * lng * math.pi) + 20.0 * math.sin(2.0 * lng * math.pi)) * 2.0 / 3.0
    ret += (20.0 * math.sin(lat * math.pi) + 40.0 * math.sin(lat / 3.0 * math.pi)) * 2.0 / 3.0
    ret += (160.0 * math.sin(lat / 12.0 * math.pi) + 320 * math.sin(lat * math.pi / 30.0)) * 2.0 / 3.0
    return ret

def out_of_china(lng, lat):
    return not (72.004 <= lng <= 137.8347 and 0.8293 <= lat <= 55.8271)

# 将用户输入的坐标（根据当前坐标系）转换为WGS-84（用于内部计算和存储）
def input_to_wgs84(lat, lng, coord_type):
    if coord_type == "GCJ-02":
        wgs_lng, wgs_lat = gcj02_to_wgs84(lng, lat)
        return wgs_lat, wgs_lng
    return lat, lng

# 将WGS-84坐标转换为当前坐标系（用于地图显示）
def wgs84_to_display(lat, lng, coord_type):
    if coord_type == "GCJ-02":
        gcj_lng, gcj_lat = wgs84_to_gcj02(lng, lat)
        return gcj_lat, gcj_lng
    return lat, lng

def calculate_distance(lat1, lng1, lat2, lng2):
    R = 6371000
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lng2 - lng1)
    a = math.sin(delta_phi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

def circle_to_polygon(center_lng, center_lat, radius_meters, num_points=24):
    points = []
    lat_rad = math.radians(center_lat)
    dlat = radius_meters / 110540
    dlng = radius_meters / (111320 * math.cos(lat_rad))
    for i in range(num_points):
        angle = math.radians(360 * i / num_points)
        offset_lng = dlng * math.cos(angle)
        offset_lat = dlat * math.sin(angle)
        points.append([center_lng + offset_lng, center_lat + offset_lat])
    return points

# ==================== 航线规划（避障）====================
def calculate_waypoints_with_safety(A, B, obstacles, flight_height, safe_radius=5):
    need_circumvent = []
    for obs in obstacles:
        if obs.get("height", 0) >= flight_height:
            need_circumvent.append(obs)
    
    straight_line = [A, B]
    
    if not need_circumvent:
        return straight_line, "直线飞行"
    
    line = LineString([A, B])
    intersect_obstacles = []
    
    for obs in need_circumvent:
        try:
            poly = Polygon(obs["coordinates"])
            if line.intersects(poly):
                intersection = line.intersection(poly)
                if not intersection.is_empty:
                    if intersection.geom_type == "LineString":
                        coords = list(intersection.coords)
                        if len(coords) >= 2:
                            intersect_obstacles.append({
                                "obs": obs,
                                "poly": poly,
                                "entry": coords[0],
                                "exit": coords[-1]
                            })
                    elif intersection.geom_type == "Point":
                        intersect_obstacles.append({
                            "obs": obs,
                            "poly": poly,
                            "entry": (intersection.x, intersection.y),
                            "exit": (intersection.x, intersection.y)
                        })
        except:
            continue
    
    if not intersect_obstacles:
        return straight_line, "直线飞行（无障碍物阻挡）"
    
    intersect_obstacles.sort(key=lambda x: line.project(Point(x["entry"])))
    
    waypoints_left = [A]
    waypoints_right = [A]
    waypoints_optimal = [A]
    
    for inter in intersect_obstacles:
        entry = inter["entry"]
        exit_pt = inter["exit"]
        poly = inter["poly"]
        center = poly.centroid
        
        dx = exit_pt[0] - entry[0]
        dy = exit_pt[1] - entry[1]
        length = math.sqrt(dx**2 + dy**2)
        if length > 0:
            dx /= length
            dy /= length
        else:
            dx, dy = 1, 0
        
        perp_x = -dy
        perp_y = dx
        
        lat_mid = (entry[1] + exit_pt[1]) / 2
        meter_per_deg = 111320 * math.cos(math.radians(lat_mid))
        offset_deg = (safe_radius * 2) / meter_per_deg if meter_per_deg > 0 else 0.0005
        
        left_avoid = (entry[0] + perp_x * offset_deg, entry[1] + perp_y * offset_deg)
        left_exit = (exit_pt[0] + perp_x * offset_deg, exit_pt[1] + perp_y * offset_deg)
        
        right_avoid = (entry[0] - perp_x * offset_deg, entry[1] - perp_y * offset_deg)
        right_exit = (exit_pt[0] - perp_x * offset_deg, exit_pt[1] - perp_y * offset_deg)
        
        dist_left = math.sqrt((left_avoid[0] - center.x)**2 + (left_avoid[1] - center.y)**2)
        dist_right = math.sqrt((right_avoid[0] - center.x)**2 + (right_avoid[1] - center.y)**2)
        
        if dist_left > dist_right:
            optimal_avoid = left_avoid
            optimal_exit = left_exit
        else:
            optimal_avoid = right_avoid
            optimal_exit = right_exit
        
        waypoints_left.append(left_avoid)
        waypoints_left.append(left_exit)
        
        waypoints_right.append(right_avoid)
        waypoints_right.append(right_exit)
        
        waypoints_optimal.append(optimal_avoid)
        waypoints_optimal.append(optimal_exit)
    
    waypoints_left.append(B)
    waypoints_right.append(B)
    waypoints_optimal.append(B)
    
    return {
        "left": waypoints_left,
        "right": waypoints_right,
        "optimal": waypoints_optimal
    }, "需要绕行"

# ==================== 飞行监控类 ====================
class FlightMonitor:
    def __init__(self, waypoints, speed=10):
        self.waypoints = waypoints
        self.speed = speed
        self.current_index = 0
        self.current_position = waypoints[0] if waypoints else None
        self.start_time = None
        self.is_flying = False
        self.total_distance = self._calculate_total_distance()
        
    def _calculate_total_distance(self):
        if not self.waypoints or len(self.waypoints) < 2:
            return 0
        total = 0
        for i in range(len(self.waypoints) - 1):
            p1 = self.waypoints[i]
            p2 = self.waypoints[i + 1]
            dist = calculate_distance(p1[1], p1[0], p2[1], p2[0])
            total += dist
        return total
    
    def get_remaining_distance(self):
        if self.current_index >= len(self.waypoints) - 1:
            return 0
        remaining = 0
        if self.current_position:
            current_target = self.waypoints[self.current_index + 1]
            remaining += calculate_distance(
                self.current_position[1], self.current_position[0],
                current_target[1], current_target[0]
            )
        for i in range(self.current_index + 1, len(self.waypoints) - 1):
            p1 = self.waypoints[i]
            p2 = self.waypoints[i + 1]
            remaining += calculate_distance(p1[1], p1[0], p2[1], p2[0])
        return remaining
    
    def get_elapsed_time(self):
        if self.start_time:
            return time.time() - self.start_time
        return 0
    
    def get_estimated_time(self):
        remaining_dist = self.get_remaining_distance()
        if self.speed > 0:
            return remaining_dist / self.speed
        return 0
    
    def update(self, dt):
        if not self.is_flying or self.current_index >= len(self.waypoints) - 1:
            return False
        
        current_target = self.waypoints[self.current_index + 1]
        dist_to_target = calculate_distance(
            self.current_position[1], self.current_position[0],
            current_target[1], current_target[0]
        )
        
        move_dist = self.speed * dt
        
        if move_dist >= dist_to_target:
            self.current_index += 1
            self.current_position = current_target
            if self.current_index >= len(self.waypoints) - 1:
                self.is_flying = False
                return False
        else:
            dx = current_target[0] - self.current_position[0]
            dy = current_target[1] - self.current_position[1]
            ratio = move_dist / dist_to_target
            self.current_position = (
                self.current_position[0] + dx * ratio,
                self.current_position[1] + dy * ratio
            )
        return True
    
    def start(self):
        self.is_flying = True
        self.start_time = time.time()
    
    def pause(self):
        self.is_flying = False
    
    def reset(self):
        self.current_index = 0
        self.current_position = self.waypoints[0] if self.waypoints else None
        self.start_time = None
        self.is_flying = False

# ==================== 初始化会话状态 ====================
if 'coord_type' not in st.session_state:
    st.session_state.coord_type = "WGS-84"
if 'pointA_input' not in st.session_state:
    st.session_state.pointA_input = {"lat": 32.2323, "lng": 118.749}
if 'pointB_input' not in st.session_state:
    st.session_state.pointB_input = {"lat": 32.2344, "lng": 118.749}
if 'flight_height' not in st.session_state:
    st.session_state.flight_height = 10
if 'safe_radius' not in st.session_state:
    st.session_state.safe_radius = 10
if 'flight_speed' not in st.session_state:
    st.session_state.flight_speed = 10
if 'selected_route' not in st.session_state:
    st.session_state.selected_route = "optimal"
if 'polygon_obstacles' not in st.session_state:
    st.session_state.polygon_obstacles = []
if 'temp_new_obstacle' not in st.session_state:
    st.session_state.temp_new_obstacle = None
if 'pending_obstacle_props' not in st.session_state:
    st.session_state.pending_obstacle_props = None
if 'waypoints' not in st.session_state:
    st.session_state.waypoints = None
if 'flight_monitor' not in st.session_state:
    st.session_state.flight_monitor = None
if 'simulation_running' not in st.session_state:
    st.session_state.simulation_running = False
if 'battery_level' not in st.session_state:
    st.session_state.battery_level = 100
if 'flight_log' not in st.session_state:
    st.session_state.flight_log = []
if 'route_message' not in st.session_state:
    st.session_state.route_message = ""

# 记忆管理
if 'memories' not in st.session_state:
    st.session_state.memories = {}
if 'active_memory' not in st.session_state:
    st.session_state.active_memory = None

# 辅助函数
def get_wgs84_A():
    return input_to_wgs84(st.session_state.pointA_input["lat"], st.session_state.pointA_input["lng"], st.session_state.coord_type)

def get_wgs84_B():
    return input_to_wgs84(st.session_state.pointB_input["lat"], st.session_state.pointB_input["lng"], st.session_state.coord_type)

def save_memories_to_file():
    data = {
        "memories": st.session_state.memories,
        "coord_type": st.session_state.coord_type,
        "last_save_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    with open("memories_config.json", "w") as f:
        json.dump(data, f, indent=2)

def load_memories_from_file():
    try:
        with open("memories_config.json", "r") as f:
            data = json.load(f)
        st.session_state.memories = data.get("memories", {})
    except:
        st.session_state.memories = {}

def load_memory_to_map(memory_name):
    if memory_name in st.session_state.memories:
        st.session_state.polygon_obstacles = st.session_state.memories[memory_name].copy()
        st.session_state.active_memory = memory_name
        generate_waypoints()
        return True
    return False

def clear_current_obstacles():
    st.session_state.polygon_obstacles = []
    st.session_state.active_memory = None
    generate_waypoints()

def save_current_obstacles_as_memory(memory_name):
    if not memory_name or memory_name.strip() == "":
        return False
    if not st.session_state.polygon_obstacles:
        return False
    st.session_state.memories[memory_name.strip()] = st.session_state.polygon_obstacles.copy()
    st.session_state.active_memory = memory_name.strip()
    save_memories_to_file()
    return True

def delete_memory(memory_name):
    if memory_name in st.session_state.memories:
        del st.session_state.memories[memory_name]
        save_memories_to_file()
        if st.session_state.active_memory == memory_name:
            st.session_state.active_memory = None
        return True
    return False

load_memories_from_file()

def generate_waypoints():
    latA_w, lngA_w = get_wgs84_A()
    latB_w, lngB_w = get_wgs84_B()
    A_geo = (lngA_w, latA_w)
    B_geo = (lngB_w, latB_w)
    
    obstacles_for_route = []
    for obs in st.session_state.polygon_obstacles:
        obstacles_for_route.append({
            "coordinates": obs["coordinates"],
            "height": obs.get("height", 40)
        })
    
    route_result = calculate_waypoints_with_safety(
        A_geo, B_geo, obstacles_for_route,
        st.session_state.flight_height,
        st.session_state.safe_radius
    )
    
    if isinstance(route_result, tuple) and len(route_result) == 2:
        waypoints_dict, message = route_result
        if isinstance(waypoints_dict, dict):
            if st.session_state.selected_route in waypoints_dict:
                selected_waypoints = waypoints_dict[st.session_state.selected_route]
            else:
                selected_waypoints = waypoints_dict.get("optimal", [A_geo, B_geo])
            st.session_state.waypoints = selected_waypoints
            st.session_state.route_message = message
        else:
            st.session_state.waypoints = waypoints_dict
            st.session_state.route_message = message
    else:
        st.session_state.waypoints = route_result
        st.session_state.route_message = "直线飞行"
    
    if st.session_state.waypoints and len(st.session_state.waypoints) >= 2:
        st.session_state.flight_monitor = FlightMonitor(st.session_state.waypoints, st.session_state.flight_speed)
        st.session_state.flight_log.append(
            f"{datetime.datetime.now().strftime('%H:%M:%S')} - 航线生成: {len(st.session_state.waypoints)}个航点, 总距离 {st.session_state.flight_monitor.total_distance:.1f}m"
        )
    else:
        st.session_state.flight_log.append(
            f"{datetime.datetime.now().strftime('%H:%M:%S')} - 航线生成失败，请检查起终点"
        )
    st.session_state.simulation_running = False

if st.session_state.waypoints is None:
    generate_waypoints()

# ==================== 布局 ====================
map_col, monitor_col, control_col = st.columns([2.5, 0.8, 1.2])

with map_col:
    st.subheader("卫星地图 + 障碍物")
    
    latA_disp, lngA_disp = wgs84_to_display(*get_wgs84_A(), st.session_state.coord_type)
    latB_disp, lngB_disp = wgs84_to_display(*get_wgs84_B(), st.session_state.coord_type)
    
    center_lat = (latA_disp + latB_disp) / 2
    center_lng = (lngA_disp + lngB_disp) / 2

    # ========== 修改：互换底图 ==========
    # 原逻辑：WGS-84 -> Esri，GCJ-02 -> 高德
    # 现逻辑：WGS-84 -> 高德，GCJ-02 -> Esri
    if st.session_state.coord_type == "WGS-84":
        # WGS-84 模式使用高德地图（注意：高德底图是GCJ-02坐标系，但显示时已做坐标转换）
        m = folium.Map(
            location=[center_lat, center_lng],
            zoom_start=17,
            tiles='http://webrd02.is.autonavi.com/appmaptile?lang=zh_cn&size=1&scale=1&style=8&x={x}&y={y}&z={z}',
            attr='高德地图'
        )
    else:  # GCJ-02 模式
        # GCJ-02 模式使用 Esri 卫星图（WGS-84 底图，显示时坐标已转换）
        m = folium.Map(
            location=[center_lat, center_lng],
            zoom_start=17,
            tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
            attr='Esri Satellite'
        )
    
    folium.Marker([latA_disp, lngA_disp], popup=f"起点 A", icon=folium.Icon(color="green")).add_to(m)
    folium.Marker([latB_disp, lngB_disp], popup=f"终点 B", icon=folium.Icon(color="red")).add_to(m)
    
    if st.session_state.waypoints:
        display_waypoints = []
        for lng_w, lat_w in st.session_state.waypoints:
            lat_disp, lng_disp = wgs84_to_display(lat_w, lng_w, st.session_state.coord_type)
            display_waypoints.append([lat_disp, lng_disp])
        folium.PolyLine(display_waypoints, color="blue", weight=4, opacity=0.8, 
                       popup=f"航线: {st.session_state.selected_route}").add_to(m)
        
        for i, (lng_w, lat_w) in enumerate(st.session_state.waypoints):
            lat_disp, lng_disp = wgs84_to_display(lat_w, lng_w, st.session_state.coord_type)
            folium.CircleMarker([lat_disp, lng_disp], radius=3, color="blue", fill=True,
                               popup=f"航点{i}").add_to(m)
        
        if st.session_state.flight_monitor and st.session_state.flight_monitor.current_position:
            pos = st.session_state.flight_monitor.current_position
            lat_disp, lng_disp = wgs84_to_display(pos[1], pos[0], st.session_state.coord_type)
            folium.Marker([lat_disp, lng_disp], icon=folium.Icon(color="purple", icon="plane", prefix="fa"),
                         popup="无人机").add_to(m)
    
    for i, obs in enumerate(st.session_state.polygon_obstacles):
        raw_coords = obs["coordinates"]
        disp_coords = []
        for lng_w, lat_w in raw_coords:
            lat_disp, lng_disp = wgs84_to_display(lat_w, lng_w, st.session_state.coord_type)
            disp_coords.append([lat_disp, lng_disp])
        color = "red" if obs.get("height", 0) >= st.session_state.flight_height else "orange"
        folium.Polygon(locations=disp_coords, color=color, fill=True, fill_opacity=0.3,
                       popup=f"{obs.get('name', f'障碍物{i+1}')}<br>高度: {obs['height']}m").add_to(m)
    
    Draw(draw_options={
        "polygon": {"shapeOptions": {"color": "#ffdd00"}},
        "rectangle": {"shapeOptions": {"color": "#ffdd00"}},
        "circle": {"shapeOptions": {"color": "#ffdd00"}},
        "polyline": False, "marker": False, "circlemarker": False
    }).add_to(m)
    MousePosition().add_to(m)
    
    output = st_folium(m, height=650, width="100%", key="map")
    
    if output and output.get("last_active_drawing"):
        drawing = output["last_active_drawing"]
        if drawing and drawing.get("geometry"):
            geom = drawing["geometry"]
            coords = []
            if geom["type"] == "Polygon":
                raw = geom["coordinates"][0]
                for lng, lat in raw:
                    coords.append([lng, lat])
            elif geom["type"] == "Rectangle":
                raw = geom["coordinates"][0]
                for lng, lat in raw:
                    coords.append([lng, lat])
            elif geom["type"] == "Circle":
                center = geom["coordinates"][0]
                radius = geom["coordinates"][1]
                coords = circle_to_polygon(center[0], center[1], radius)
            
            if coords and st.session_state.temp_new_obstacle is None:
                st.session_state.temp_new_obstacle = coords
                st.session_state.pending_obstacle_props = {"name": f"障碍物{len(st.session_state.polygon_obstacles)+1}", "height": 40}
                st.rerun()

with monitor_col:
    st.subheader("飞行监控")
    
    if st.session_state.waypoints:
        st.info(f"航线: {st.session_state.selected_route} | {st.session_state.route_message}")
        st.metric("总航点数", f"{len(st.session_state.waypoints)}")
        if st.session_state.flight_monitor:
            st.metric("总航程", f"{st.session_state.flight_monitor.total_distance:.1f}m")
    else:
        st.warning("请先生成航线")
    
    st.divider()
    st.markdown("### 飞行状态")
    
    if st.session_state.flight_monitor and st.session_state.flight_monitor.total_distance > 0:
        col_a, col_b = st.columns(2)
        with col_a:
            st.metric("当前航点", f"{st.session_state.flight_monitor.current_index + 1}/{len(st.session_state.flight_monitor.waypoints)}")
        with col_b:
            st.metric("飞行速度", f"{st.session_state.flight_speed} m/s")
        
        elapsed = st.session_state.flight_monitor.get_elapsed_time()
        remaining_dist = st.session_state.flight_monitor.get_remaining_distance()
        est_time = st.session_state.flight_monitor.get_estimated_time()
        
        st.metric("已用时间", f"{elapsed:.1f}s")
        st.metric("剩余距离", f"{remaining_dist:.1f}m")
        st.metric("预计到达", f"{est_time:.1f}s")
        
        if st.session_state.simulation_running and st.session_state.flight_monitor.total_distance > 0:
            progress = 1 - (remaining_dist / st.session_state.flight_monitor.total_distance)
            battery_used = progress * 100
            st.session_state.battery_level = max(0, 100 - battery_used)
        
        st.progress(st.session_state.battery_level / 100)
        st.metric("电量", f"{st.session_state.battery_level:.1f}%")
        
        st.divider()
        
        col_start, col_pause, col_reset = st.columns(3)
        with col_start:
            if st.button("▶️ 开始", use_container_width=True):
                if st.session_state.flight_monitor and not st.session_state.simulation_running:
                    st.session_state.flight_monitor.start()
                    st.session_state.simulation_running = True
                    st.rerun()
        with col_pause:
            if st.button("⏸️ 暂停", use_container_width=True):
                if st.session_state.flight_monitor and st.session_state.simulation_running:
                    st.session_state.flight_monitor.pause()
                    st.session_state.simulation_running = False
                    st.rerun()
        with col_reset:
            if st.button("🔄 重置", use_container_width=True):
                if st.session_state.flight_monitor:
                    st.session_state.flight_monitor.reset()
                    st.session_state.simulation_running = False
                    st.session_state.battery_level = 100
                    st.rerun()
    else:
        st.warning("请先生成有效航线")
    
    st.divider()
    st.markdown("### 飞行日志")
    log_container = st.container(height=150)
    with log_container:
        if st.session_state.flight_log:
            for log in st.session_state.flight_log[-10:]:
                st.caption(log)
        else:
            st.caption("等待飞行...")

with control_col:
    st.subheader("控制面板")
    
    coord_opt = st.radio("坐标系", ["WGS-84", "GCJ-02"], index=0 if st.session_state.coord_type == "WGS-84" else 1)
    if coord_opt != st.session_state.coord_type:
        st.session_state.coord_type = coord_opt
        generate_waypoints()
        st.rerun()
    
    st.divider()
    st.markdown("### 起终点")
    
    st.markdown("**起点 A**")
    latA = st.number_input("纬度", value=st.session_state.pointA_input["lat"], format="%.6f", key="latA")
    lngA = st.number_input("经度", value=st.session_state.pointA_input["lng"], format="%.6f", key="lngA")
    if st.button("📍 设置A点"):
        st.session_state.pointA_input = {"lat": latA, "lng": lngA}
        generate_waypoints()
        st.rerun()
    
    st.markdown("**终点 B**")
    latB = st.number_input("纬度", value=st.session_state.pointB_input["lat"], format="%.6f", key="latB")
    lngB = st.number_input("经度", value=st.session_state.pointB_input["lng"], format="%.6f", key="lngB")
    if st.button("📍 设置B点"):
        st.session_state.pointB_input = {"lat": latB, "lng": lngB}
        generate_waypoints()
        st.rerun()
    
    st.divider()
    st.markdown("### 飞行参数")
    
    new_height = st.number_input("飞行高度(m)", value=st.session_state.flight_height, step=5)
    if new_height != st.session_state.flight_height:
        st.session_state.flight_height = new_height
        generate_waypoints()
        st.rerun()
    
    new_radius = st.number_input("安全半径(m)", value=st.session_state.safe_radius, step=1)
    if new_radius != st.session_state.safe_radius:
        st.session_state.safe_radius = new_radius
        generate_waypoints()
        st.rerun()
    
    new_speed = st.number_input("飞行速度(m/s)", value=st.session_state.flight_speed, step=1)
    if new_speed != st.session_state.flight_speed:
        st.session_state.flight_speed = new_speed
        if st.session_state.flight_monitor:
            st.session_state.flight_monitor.speed = new_speed
        st.rerun()
    
    st.divider()
    st.markdown("### 航线选择")
    route_option = st.radio("绕行策略", ["optimal", "left", "right"],
                           format_func=lambda x: {"optimal": "⭐ 最佳航线", "left": "⬅️ 向左绕行", "right": "➡️ 向右绕行"}[x])
    if route_option != st.session_state.selected_route:
        st.session_state.selected_route = route_option
        generate_waypoints()
        st.rerun()
    
    if st.button("🚁 重新生成航线", type="primary", use_container_width=True):
        generate_waypoints()
        st.success("航线已重新生成！")
        st.rerun()
    
    st.divider()
    st.markdown("### 障碍物与记忆管理")
    
    if st.session_state.temp_new_obstacle is not None:
        st.warning("📌 检测到新绘制的区域，请设置该障碍物属性")
        default_name = f"障碍物{len(st.session_state.polygon_obstacles)+1}"
        if st.session_state.pending_obstacle_props:
            default_name = st.session_state.pending_obstacle_props.get("name", default_name)
        
        new_obs_name = st.text_input("障碍物名称", value=default_name, key="new_obs_name")
        new_obs_height = st.number_input("障碍物高度(米)", min_value=0, max_value=500, value=40, step=5, key="new_obs_height")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ 确认添加", type="primary", use_container_width=True):
                st.session_state.polygon_obstacles.append({
                    "name": new_obs_name,
                    "coordinates": st.session_state.temp_new_obstacle,
                    "height": new_obs_height
                })
                st.session_state.temp_new_obstacle = None
                st.session_state.pending_obstacle_props = None
                st.session_state.active_memory = None
                generate_waypoints()
                st.success(f"已添加 {new_obs_name} (高度{new_obs_height}m)")
                st.rerun()
        with col2:
            if st.button("❌ 取消", use_container_width=True):
                st.session_state.temp_new_obstacle = None
                st.session_state.pending_obstacle_props = None
                st.rerun()
    else:
        st.info("💡 在地图上绘制多边形/矩形/圆形，将自动弹出属性设置窗口")
    
    st.divider()
    st.markdown("#### 📦 记忆管理")
    
    memory_name_input = st.text_input("记忆名称", value=f"记忆{len(st.session_state.memories)+1}", key="memory_save_name")
    col_save_mem, col_clear = st.columns(2)
    with col_save_mem:
        if st.button("💾 保存为记忆", use_container_width=True):
            if st.session_state.polygon_obstacles:
                if save_current_obstacles_as_memory(memory_name_input):
                    st.success(f"已保存为 {memory_name_input}")
                    st.rerun()
                else:
                    st.error("保存失败")
            else:
                st.warning("当前没有障碍物可以保存")
    with col_clear:
        if st.button("🗑️ 清空地图", use_container_width=True):
            clear_current_obstacles()
            st.success("已清空地图上所有障碍物")
            st.rerun()
    
    if st.session_state.memories:
        memory_options = list(st.session_state.memories.keys())
        selected_memory = st.selectbox("选择要加载的记忆", memory_options, index=0 if memory_options else None)
        
        col_load, col_del = st.columns(2)
        with col_load:
            if st.button("📂 加载记忆", use_container_width=True):
                if selected_memory:
                    if load_memory_to_map(selected_memory):
                        st.success(f"已加载 {selected_memory}")
                        st.rerun()
                    else:
                        st.error("加载失败")
        with col_del:
            if st.button("❌ 删除记忆", use_container_width=True):
                if selected_memory:
                    if delete_memory(selected_memory):
                        st.success(f"已删除 {selected_memory}")
                        st.rerun()
                    else:
                        st.error("删除失败")
    else:
        st.info("暂无保存的记忆")
    
    st.divider()
    st.info(f"📂 当前障碍物数量: {len(st.session_state.polygon_obstacles)}")
    if st.session_state.active_memory:
        st.success(f"当前加载的记忆: {st.session_state.active_memory}")
    
    with st.expander("📋 障碍物列表"):
        if st.session_state.polygon_obstacles:
            for i, obs in enumerate(st.session_state.polygon_obstacles):
                st.write(f"{i+1}. {obs.get('name', f'障碍物{i+1}')} - {obs.get('height', 40)}m")
        else:
            st.write("暂无")

# ==================== 模拟飞行更新 ====================
if st.session_state.simulation_running and st.session_state.flight_monitor:
    dt = 0.5
    completed = st.session_state.flight_monitor.update(dt)
    if completed:
        st.session_state.simulation_running = False
        st.session_state.flight_log.append(f"{datetime.datetime.now().strftime('%H:%M:%S')} - ✅ 飞行完成!")
        st.rerun()
    else:
        if int(time.time() * 2) % 4 == 0:
            st.session_state.flight_log.append(
                f"{datetime.datetime.now().strftime('%H:%M:%S')} - 航点 {st.session_state.flight_monitor.current_index + 1}/{len(st.session_state.flight_monitor.waypoints)}, 剩余 {st.session_state.flight_monitor.get_remaining_distance():.1f}m"
            )
    time.sleep(0.1)
    st.rerun()

st.divider()
st.caption(f"📍 A点: {st.session_state.pointA_input['lat']}, {st.session_state.pointA_input['lng']} | B点: {st.session_state.pointB_input['lat']}, {st.session_state.pointB_input['lng']} | 障碍物: {len(st.session_state.polygon_obstacles)}个 | 坐标系: {st.session_state.coord_type}")
