import cv2
import time
import os

def capture_frame(rtsp_url, image_save_path, capture_interval):
    # 設定時間戳記的格式
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_size = 0.5
    font_color = (255, 255, 255)  # 白色
    thickness = 1

    # 開始讀取 RTSP 串流
    cap = cv2.VideoCapture(rtsp_url)

    ret, frame = cap.read()
    if ret:
        # 自動增加資料夾
        if not os.path.exists(image_save_path):
            os.makedirs(image_save_path)

        # 在影像上加入時間戳記
        current_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
        text_size, _ = cv2.getTextSize(current_time, font, font_size, thickness)
        cv2.putText(frame, current_time, (frame.shape[1] - text_size[0] - 10, frame.shape[0] - 10), font, font_size, font_color, thickness)

        filename = f'{image_save_path}/frame_{int(time.time())}.jpg'  # 使用時間戳作為檔名
        cv2.imwrite(filename, frame)
        print(f'Saved {filename}')
    else:
        print('Error capturing frame')

    cap.release()

# 使用範例
rtsp_url = 'rtsp://ahb0222:b10231040@192.168.0.103:554/stream1'
image_save_path = os.path.expanduser('~/python/Tapo/images')
capture_interval = 60
capture_frame(rtsp_url, image_save_path, capture_interval)