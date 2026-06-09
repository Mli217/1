# pages/2_飞行监控.py
import streamlit as st
import pandas as pd
import datetime
from streamlit_autorefresh import st_autorefresh

st.set_page_config(page_title="飞行监控", layout="wide")
st.title("📡 飞行监控 - 无人机心跳监测")

if 'heartbeat_data' not in st.session_state:
    st.session_state.heartbeat_data = []
if 'last_heartbeat_time' not in st.session_state:
    st.session_state.last_heartbeat_time = None
if 'next_seq' not in st.session_state:
    st.session_state.next_seq = 1
if 'offline_alert' not in st.session_state:
    st.session_state.offline_alert = False

st_autorefresh(interval=1000, key="heartbeat_refresh")

now = datetime.datetime.now()
last_time = st.session_state.last_heartbeat_time

if last_time is None:
    st.session_state.heartbeat_data.append({"seq": st.session_state.next_seq, "time": now})
    st.session_state.next_seq += 1
    st.session_state.last_heartbeat_time = now
    st.session_state.offline_alert = False
else:
    time_diff = (now - last_time).total_seconds()
    if time_diff >= 1.0:
        packets = min(int(time_diff // 1.0), 5)
        cur = last_time
        for _ in range(packets):
            cur += datetime.timedelta(seconds=1)
            if cur > now:
                cur = now
            st.session_state.heartbeat_data.append({"seq": st.session_state.next_seq, "time": cur})
            st.session_state.next_seq += 1
            st.session_state.last_heartbeat_time = cur

if st.session_state.last_heartbeat_time:
    elapsed = (now - st.session_state.last_heartbeat_time).total_seconds()
    st.session_state.offline_alert = elapsed > 3.0
else:
    elapsed = 0.0

if len(st.session_state.heartbeat_data) > 200:
    st.session_state.heartbeat_data = st.session_state.heartbeat_data[-200:]

col1, col2, col3 = st.columns(3)
col1.metric("最新心跳序号", st.session_state.heartbeat_data[-1]["seq"] if st.session_state.heartbeat_data else "—")
col2.metric("最后心跳时间", st.session_state.last_heartbeat_time.strftime("%H:%M:%S") if st.session_state.last_heartbeat_time else "—")
col3.metric("距上次心跳", f"{elapsed:.1f} 秒")

if st.session_state.offline_alert:
    st.error("🚨 连接超时！超过3秒未收到心跳")
else:
    st.success("✅ 连接正常 | 心跳监测运行中")

if len(st.session_state.heartbeat_data) >= 2:
    df = pd.DataFrame(st.session_state.heartbeat_data)
    df["time"] = pd.to_datetime(df["time"])
    st.line_chart(df, x="time", y="seq")

with st.expander("📋 最近心跳记录"):
    if st.session_state.heartbeat_data:
        df_show = pd.DataFrame(st.session_state.heartbeat_data[-20:])
        df_show["time"] = df_show["time"].dt.strftime("%H:%M:%S")
        st.dataframe(df_show.rename(columns={"seq":"序号","time":"时间"}), hide_index=True)
