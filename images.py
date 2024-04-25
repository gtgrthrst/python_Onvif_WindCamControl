import cv2
import time
import os
import imageio

# 設定 RTSP URL
rtsp_url = 'rtsp://ahb0222:b10231040@192.168.0.103:554/stream1'

# 設定縮時攝影的參數
capture_interval = 60  # 每隔 60 秒擷取一張影像
image_save_path = os.path.expanduser('~/python/Tapo/images')  # 儲存影像的資料夾路徑

frame_count = 0  # 影像計數器

# 設定時間戳記的格式
font = cv2.FONT_HERSHEY_SIMPLEX
font_size = 0.5
font_color = (255, 255, 255)  # 白色
thickness = 1

# 開始讀取 RTSP 串流
cap = cv2.VideoCapture(rtsp_url)

start_time = time.time()
duration = 10  # 例如持續1小時
while (time.time() - start_time) < duration:

    ret, frame = cap.read()
    if ret:
        # 每隔一定時間保存一張影像
        if frame_count % (capture_interval * int(cap.get(cv2.CAP_PROP_FPS))) == 0:
            # 自動增加資料夾
            if not os.path.exists(image_save_path):
                os.makedirs(image_save_path)

            filename = f'{image_save_path}/frame_{frame_count:04d}.jpg'  # 使用四位數填充
            print(filename)
            # 在影像上加入時間戳記
            current_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
            text_size, _ = cv2.getTextSize(current_time, font, font_size, thickness)
            cv2.putText(frame, current_time, (frame.shape[1] - text_size[0] - 10, frame.shape[0] - 10), font, font_size, font_color, thickness)

            cv2.imwrite(filename, frame)
            print(f'Saved {filename}')
        frame_count += 1
    else:
        print('Error capturing frame')
        break

    # 根據設定的間隔時間等待，而不是依據原始幀率
    time.sleep(capture_interval)

cap.release()
print('Timelapse capture completed.')
