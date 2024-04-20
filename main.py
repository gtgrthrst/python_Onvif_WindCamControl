#cd C:\R\Python\nicegui\myenv

#cd C:\Users\huanyu145\Documents\python\Project\Onvif
#python -m venv onvif
#.\Scripts\activate

#library(reticulate)
#use_python("C:/Users/huanyu145/Documents/python/Project/onvif/Scripts/python.exe", required = TRUE)
#py_config()

from nicegui import ui
import json
import paho.mqtt.client as mqtt
import plotly.graph_objects as go
import datetime
from onvif import ONVIFCamera  #pip install --upgrade onvif_zeep
import sqlite3
import os.path
from threading import Lock
import time
import schedule
import os
import csv


# 全局變量
client = None
wind_history = []
global camera, profile_token   # 宣告全域變量
profile_token = 1


# 全局變量，用於存儲相機和PTZ服務
camera = None
ptz_service = None
profile_token = 1#
profile_token = None

def initialize_camera():
    global camera, ptz_service, profile_token
    try:
        camera = ONVIFCamera(camera_ip.value, int(camera_port.value), camera_user.value, camera_password.value)
        media_service = camera.create_media_service()
        profile_token = media_service.GetProfiles()[0].token
        ptz_service = camera.create_ptz_service()
        if not ptz_service:
            raise Exception("Failed to create PTZ service")
        print("Camera and PTZ service initialized successfully")
    except Exception as e:
        ui.notify(f"Failed to initialize camera: {str(e)}", type='negative')
        print(f"Failed to initialize camera: {str(e)}")

def go_to_preset(preset_number):
    global camera, ptz_service, profile_token
    initialize_camera()
    try:
        camera = ONVIFCamera(camera_ip.value, int(camera_port.value), camera_user.value, camera_password.value)
        if camera is None or ptz_service is None or profile_token is None:
            initialize_camera()
            if camera is None or ptz_service is None or profile_token is None:
                raise Exception("Camera not initialized or PTZ service/profile token not obtained")

        request = ptz_service.create_type('GotoPreset')
        request.ProfileToken = profile_token
        request.PresetToken = str(preset_number)
        ptz_service.GotoPreset(request)
        ui.notify(f'Moved to Preset {preset_number}', type='positive')
    except Exception as e:
        ui.notify(f'Error moving to preset {preset_number}: {str(e)}', type='negative')
        print(f'Error moving to preset {preset_number}: {str(e)}')  # Log to console for debugging



# 創建鎖對象以確保線程安全
lock = Lock()

# 檢查資料庫檔案是否存在
db_file = 'C:/Users/AHB0222_R7-7840HS/OneDrive/00重要文件/成大碩士/06部落格/000創客/23-專案/04-風向攝影機/NiceGUI/wind_data.db'
if os.path.isfile(db_file):
    # 連接到現有的資料庫檔案
    conn = sqlite3.connect(db_file, check_same_thread=False)
else:
    # 建立新的資料庫檔案
    conn = sqlite3.connect(db_file, check_same_thread=False)

# 建立一個新的資料表來儲存風向資料
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS wind_data
             (timestamp TEXT, raw_direction INTEGER, direction_text TEXT)''')
conn.commit()

# 保存設定並重啟MQTT客戶端
def save_settings():
    stop_mqtt_client()  # 停止MQTT客戶端
    settings = {
        #'camera_ip': camera_ip.value,
        'mqtt_server': mqtt_server.value,
        'mqtt_topic': mqtt_topic.value
    }
    with open('settings.json', 'w') as f:
        json.dump(settings, f)
    setup_mqtt_client()  # 使用新設定重啟MQTT客戶端


# 建立 UI
with ui.tabs().classes('w-full') as tabs:
    
    camera_tab = ui.tab('Camera Setup')
    mqtt_tab = ui.tab('MQTT Setup')
    plot_tab = ui.tab('Wind Direction Plot')

with ui.tab_panels(tabs).classes('w-full'):
    with ui.tab_panel(camera_tab):
        with ui.stepper().props('vertical').classes('w-full') as stepper:
            with ui.step('Camera IP'):
                camera_ip = ui.input(label='Camera IP', value='192.168.0.112')
                with ui.stepper_navigation():
                    ui.button('Next', on_click=stepper.next)

            with ui.step('Camera Port'):
                camera_port = ui.input(label='Camera Port', value='2020')  # 使用字符串形式
                with ui.stepper_navigation():
                    ui.button('Next', on_click=stepper.next)
                    ui.button('Back', on_click=stepper.previous).props('flat')

            with ui.step('Camera User'):
                camera_user = ui.input(label='Camera User', value='ahb0222')
                with ui.stepper_navigation():
                    ui.button('Next', on_click=stepper.next)
                    ui.button('Back', on_click=stepper.previous).props('flat')

            with ui.step('Camera Password'):
                camera_password = ui.input(label='Camera Password', value='b10231040')
                with ui.stepper_navigation():
                    # 使用新定義的函數作為回調
                    ui.button('Set camera', on_click=stepper.next)
                    ui.button('Back', on_click=stepper.previous).props('flat')

            with ui.step('Test ONVIF'):
                with ui.stepper_navigation():
                    # 添加標籤來描述滑塊
                    ui.label('Preset Position')
                    
                    # 創建滑塊，移除不支持的 'label' 參數
                    slider =  preset_position = ui.slider(min=1, max=8, step=1, value=1)
                    ui.label().bind_text_from(slider, 'value')
                    # 創建按鈕來觸發轉到預設位置的操作
                    ui.button('Go to Preset Position', on_click=lambda: go_to_preset(preset_position.value))

                    # 新增ONVIF測試按鈕
                    ui.button('Test ONVIF Connection', on_click=lambda: test_onvif_connection())
                    ui.button('Back', on_click=stepper.previous).props('flat')


    with ui.tab_panel(mqtt_tab):
        with ui.stepper().props('vertical').classes('w-full') as stepper:
            with ui.step('MQTT Server'):
                mqtt_server = ui.input(label='MQTT Server', value='broker.emqx.io')
                with ui.stepper_navigation():
                    ui.button('Next', on_click=stepper.next)

            with ui.step('MQTT Topic'):
                mqtt_topic = ui.input(label='MQTT Topic', value='nicegui/WD')
                with ui.stepper_navigation():
                    ui.button('Next', on_click=stepper.next)
                    ui.button('Back', on_click=stepper.previous).props('flat')

            with ui.step('Monitor Setup'):
                wind_direction = ui.label('Wind Direction: 0')
                with ui.stepper_navigation():
                    ui.notify('MQTT Configuration Complete!', type='positive')  # Move this line before the ui.button() function call
                    ui.button('Save Settings', on_click=save_settings)
                    ui.button('Back', on_click=stepper.previous).props('flat')
    with ui.tab_panel(plot_tab):
        with ui.row():
            # 起始日期選擇器
            with ui.input('Start Date', value=datetime.datetime.now().strftime('%Y-%m-%d')) as start_date:
                with start_date.add_slot('append'):
                    ui.icon('edit_calendar').on('click', lambda: start_menu.open()).classes('cursor-pointer')
                with ui.menu() as start_menu:
                    ui.date().bind_value(start_date)

            # 結束日期選擇器
            with ui.input('End Date', value=datetime.datetime.now().strftime('%Y-%m-%d')) as end_date:
                with end_date.add_slot('append'):
                    ui.icon('edit_calendar').on('click', lambda: end_menu.open()).classes('cursor-pointer')
                with ui.menu() as end_menu:
                    ui.date().bind_value(end_date)

            # 下載按鈕
            ui.button('Download CSV', on_click=lambda: download_csv(start_date.value, end_date.value, ''))
    
        # 初始化圖表
fig = go.Figure()
fig.update_layout(margin=dict(l=0, r=0, t=0, b=0))
plot = ui.plotly(fig).classes('w-3/4 h-64')
table = ui.table(
    columns=[
        {'field': 'timestamp', 'label': 'Timestamp'},
        {'field': 'raw_direction', 'label': 'Wind Direction'},
        {'field': 'direction_text', 'label': 'Wind Direction'}
    ],
    rows=wind_history,
    pagination=10  # 每頁顯示10條數據
)

# 設定MQTT客戶端
def setup_mqtt_client():
    global client
    client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(mqtt_server.value, 1883, 60)
    client.loop_start()

# 停止MQTT客戶端
def stop_mqtt_client():
    global client
    if client is not None:
        client.loop_stop()
        client.disconnect()



# 載入設定
def load_settings():
    try:
        with open('settings.json', 'r') as f:
            settings = json.load(f)
        #camera_ip.value = settings.get('camera_ip', '192.168.0.112')
        mqtt_server.value = settings.get('mqtt_server', 'broker.emqx.io')
        mqtt_topic.value = settings.get('mqtt_topic', 'nicegui/WD')
    except FileNotFoundError:
        print('Settings file not found, using default values.')

# MQTT事件處理
def on_connect(client, userdata, flags, reason_code, properties):
    print("Connected with result code " + str(reason_code))
    client.subscribe(mqtt_topic.value)

def save_data(timestamp, raw_direction, direction_text):
    with lock:
        c = conn.cursor()
        c.execute("INSERT INTO wind_data VALUES (?, ?, ?)", (timestamp, raw_direction, direction_text))
        conn.commit()
        update_table()

def on_message(client, userdata, msg):
    try:
        raw_direction = int(msg.payload.decode())
        direction_text = direction_to_text(raw_direction)
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        new_data = {'timestamp': timestamp, 'raw_direction': raw_direction, 'direction_text': direction_text}
        
        # 使用線程安全的函數保存數據
        save_data(timestamp, raw_direction, direction_text)
        
        # 更新風向顯示
        wind_direction.set_text(str(raw_direction) + '° ' + direction_text)
        
        # 更新表格數據
        wind_history.append(new_data)
        if len(wind_history) > 20:  # 檢查列表長度是否超過1000
            wind_history.pop(0)  # 移除列表中的第一個元素，即最舊的數據

        table.update_rows(reversed(wind_history))  # 更新表格以顯示最新的數據

    except ValueError:
        print("Received non-integer value from MQTT.")
    except Exception as e:
        print(f"Error processing message: {e}")




def direction_to_text(direction):
    directions = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW']
    index = int((direction + 22.5) // 45) % 8
    return directions[index]

def update_table():
    c = conn.cursor()
    # 拉取所有數據而不是只有最新的5條
    c.execute("SELECT * FROM wind_data ORDER BY timestamp DESC")
    displayed_data = c.fetchall()
    conn.commit()
    # 要確保數據是按時間戳排序的，因此這裡使用 reversed 函數
    #table.update_rows(list(reversed(displayed_data)))
    update_plot()


def update_plot():
    c = conn.cursor()
    c.execute("SELECT * FROM wind_data ORDER BY timestamp DESC LIMIT 50")
    displayed_data = c.fetchall()
    conn.commit()
    # 提取時間戳和原始方向數據
    timestamps = [row[0] for row in displayed_data]  
    raw_directions = [row[1] for row in displayed_data] 

    # 清除現有數據
    fig.data = []

    # 添加新的數據跟蹤至折線圖
    fig.add_trace(go.Scatter(
        x=timestamps,
        y=raw_directions,
        mode='lines+markers',
        name='Wind Direction',
        marker=dict(color='blue', size=5),
        line=dict(width=2)))

    # 更新圖表的佈局設置
    fig.update_layout(
        xaxis=dict(title='Time', showgrid=True, gridcolor='lightgray'),
        yaxis=dict(title='Wind Direction (°)', range=[0, 360], showgrid=True, gridcolor='lightgray'),
        margin=dict(l=0, r=0, t=0, b=0),
        showlegend=False
    )

   # 更新 plotly 元件
    plot.update()



def ensure_directory_exists(path):
    os.makedirs(path, exist_ok=True)

def download_csv(start_date, end_date, custom_filename):
    directory = './data'
    ensure_directory_exists(directory)

    filename = custom_filename + '.csv' if custom_filename else 'wind_data.csv'
    file_path = os.path.join(directory, filename)
    absolute_file_path = os.path.abspath(file_path)

    print("Full path of the file:", absolute_file_path)

    c = conn.cursor()
    query = "SELECT * FROM wind_data WHERE timestamp BETWEEN ? AND ? ORDER BY timestamp DESC"
    c.execute(query, (f"{start_date} 00:00:00", f"{end_date} 23:59:59"))
    data = c.fetchall()

    if not data:
        ui.notify('No data found for the selected date range.', type='error')
        return

    with open(absolute_file_path, 'w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(['Timestamp', 'Raw Direction', 'Direction Text'])
        for row in data:
            writer.writerow(row)

    print("CSV file created successfully at:", absolute_file_path)
    with open(absolute_file_path, 'r', encoding='utf-8') as file:
        csv_file = file.read().encode()
    ui.download(src=csv_file, filename=f"WS.csv")
ui.html('<style>.multi-line-notification { white-space: pre-line; }</style>')

def test_onvif_connection():
    try:
        # 用當前輸入值初始化相機
        camera = ONVIFCamera(camera_ip.value, int(camera_port.value), camera_user.value, camera_password.value)
        device_info = camera.devicemgmt.GetDeviceInformation()
        
        # 將響應格式化為包含有用信息的多行字符串
        info_message = (
            f"IP: {camera_ip.value}\n"
            f"ONVIF Connection Successful!\n"
            f"Manufacturer: {device_info.Manufacturer}\n"
            f"Model: {device_info.Model}\n"
            f"Firmware Version: {device_info.FirmwareVersion}"
        )
        
        # 顯示具有多行支持的通知
        ui.notify(info_message, multi_line=True, classes='multi-line-notification')
        print(f"Device Information: {info_message}")
    except Exception as e:
        error_message = f'ONVIF Connection Failed: {str(e)}'
        ui.notify(error_message, multi_line=True, classes='multi-line-notification')
        print(f'ONVIF Connection Exception: {str(e)}')

# 示例按鈕來測試連接
ui.button('Test Connection', on_click=test_onvif_connection)

def on_camera_ip_change(event):
    # 重新初始化相機連接
    initialize_camera()
    ui.notify('Camera IP updated and reinitialized', type='positive')

def adjust_camera_based_on_wind():
    # 模拟获取最新风向数据，这里需要实现获取逻辑
    # 假设获取到的风向数据可以转换为预设位的 token
    initialize_camera()
    latest_wind_direction = get_latest_wind_direction()
    preset_token = wind_direction_to_preset_token(latest_wind_direction)
    ptz_control.goto_preset(preset_token)
    print(f"Camera adjusted to preset based on wind direction {latest_wind_direction}")


# 每分钟执行一次调整相机位置的操作
schedule.every().minute.do(adjust_camera_based_on_wind)

#while True:
#    schedule.run_pending()
#    time.sleep(1)

# 初始化設定
load_settings()

# 啟動MQTT客戶端
setup_mqtt_client()

# 啟動NiceGUI界面
ui.run(title='Wind Direction Monitoring System') 
