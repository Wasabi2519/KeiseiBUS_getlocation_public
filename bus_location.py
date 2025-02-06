import json
import os
import time
import datetime
import concurrent.futures
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# 取得する系統
# https://transfer.navitime.biz/keiseibus/pc/location/BusOperationResult?courseId="XXXXXXX"
COURSE_IDS = {
    "系統01": "XXXXXXX"
}

BUS_STOP_FILE = "bus_stop.json"

def create_webdriver():
    """新しい WebDriver セッションを作成する"""
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")

    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=chrome_options)

def fetch_running_buses(course_id, line_name, bus_stop_data):
    """運行中のバスを取得し、JSONとして返す"""
    driver = create_webdriver()
    url = f"https://transfer.navitime.biz/keiseibus/pc/location/BusOperationResult?courseId={course_id}"
    print(f"\n🚀 {line_name} の運行中のバスを検索中... ({url})")
    driver.get(url)

    try:
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, "busArea")))
    except:
        print(f"⚠ {line_name} のバスエリアが見つかりませんでした。")
        driver.quit()
        return []

    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(2)

    bus_areas = driver.find_elements(By.CLASS_NAME, "busArea")
    point_areas = driver.find_elements(By.CLASS_NAME, "pointArea")

    print(f"🔎 {line_name}: バスエリア {len(bus_areas)} 個をチェック中...")

    running_buses = []

    for index, bus_area in enumerate(bus_areas):
        try:
            bus_y = bus_area.location["y"]  # バスエリアのY座標

            image_elements = bus_area.find_elements(By.XPATH, ".//div[@class='image']/img")

            bus_detected = False
            for img in image_elements:
                src = img.get_attribute("src")
                if "busOperation.png" in src:
                    bus_detected = True
                    break

            # 最も近い `pointArea` を探す
            closest_stop = None
            closest_distance = float("inf")

            for point_area in point_areas:
                stop_y = point_area.location["y"]
                distance = abs(bus_y - stop_y)  # バスエリアとのY座標の距離

                if distance < closest_distance:
                    closest_distance = distance
                    stop_name_element = point_area.find_element(By.CLASS_NAME, "busstopName")
                    stop_name = stop_name_element.text.strip()

                    # bus_stop.json からバス停情報を取得
                    for stop in bus_stop_data:
                        if stop["バス停名"] == stop_name and stop["系統"] == line_name:
                            closest_stop = stop
                            break

            # ログ詳細化
            print(f"\n🔍 {line_name} - バスエリア [{index+1}/{len(bus_areas)}] をチェック")
            print(f"  🗺️  Y座標: {bus_y}, 最寄りのバス停: {closest_stop['バス停名'] if closest_stop else '未検出'} (Y座標: {stop_y})")
            print(f"  🚌 バス画像検出: {'✅' if bus_detected else '❌'}")

            if bus_detected and closest_stop:
                running_buses.append({
                    "系統": line_name,
                    "バス停名": closest_stop["バス停名"],
                    "緯度": closest_stop["緯度"],
                    "経度": closest_stop["経度"]
                })
                print(f"  🚍 {line_name}: 運行中のバスを発見 - {closest_stop['バス停名']} (緯度: {closest_stop['緯度']}, 経度: {closest_stop['経度']})")
            elif bus_detected:
                print(f"  ⚠ {line_name} - バスエリア [{index+1}] で運行中のバスを検出したが、対応するバス停が見つかりませんでした。")

        except Exception as e:
            print(f"⚠ {line_name} - バスエリア [{index+1}] でエラー発生: {e}")
            continue

    driver.quit()
    return running_buses

def load_bus_stops():
    """保存済みのバス停情報を読み込む"""
    if os.path.exists(BUS_STOP_FILE):
        with open(BUS_STOP_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def main():
    """運行中のバスの取得を行う"""
    driver = create_webdriver()

    # 既存のバス停情報をロード or 新規取得
    bus_stop_data = load_bus_stops()
    if not bus_stop_data:
        print("\n🕒 バス停情報が見つかりません。新規取得してください。")
        driver.quit()
        return

    driver.quit()

    while True:
        print("\n🕒 運行中のバス情報の取得を開始します...")

        with concurrent.futures.ThreadPoolExecutor() as executor:
            future_to_line = {executor.submit(fetch_running_buses, course_id, line_name, bus_stop_data): line_name
                              for line_name, course_id in COURSE_IDS.items()}

            all_running_buses = []
            for future in concurrent.futures.as_completed(future_to_line):
                all_running_buses.extend(future.result())

        bus_data = {
            "取得時刻": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "運行中のバス": all_running_buses
        }

        print("\n🚍 現在の運行状況:")
        print(json.dumps(bus_data, indent=4, ensure_ascii=False))

        with open("bus_location.json", "w", encoding="utf-8") as f:
            json.dump(bus_data, f, indent=4, ensure_ascii=False)

        print("✅ データを取得しました。次の取得まで60秒待機します...")
        time.sleep(60)

if __name__ == "__main__":
    main()
