import asyncio
from bleak import BleakClient
from PIL import Image

ADDRESS = "2C:CF:67:04:CF:1B"  # ペリフェラルのMACアドレス
CHAR_UUID = "87654321-4321-8765-4321-fedcba987654"  # ペリフェラルのキャラクタリスティックUUID

def prepare_image(file_path, size):
    """画像を指定されたサイズに変換し、バイナリデータに変換します。"""
    img = Image.open(file_path).convert("1")  # 白黒画像に変換
    img = img.resize(size)  # 指定サイズにリサイズ
    data = bytearray(img.tobytes())  # バイナリデータに変換
    return data

async def send_image(file_path_black, file_path_red, size, mtu):
    """赤色と黒色の画像データを送信します。"""
    data_black = prepare_image(file_path_black, size)
    data_red = prepare_image(file_path_red, size)

    # ヘッダー + データの構築
    combined_data = data_black + data_red
    header = len(combined_data).to_bytes(4, byteorder="little")  # データサイズをヘッダーとして追加
    full_data = header + combined_data
    chunk_size = mtu - 3

    async with BleakClient(ADDRESS) as client:
        if await client.is_connected():
            print("[INFO] Connected to peripheral")
            print(f"[INFO] Total data size (with header): {len(full_data)} bytes")

            for i in range(0, len(full_data), chunk_size):
                chunk = full_data[i:i + chunk_size]
                try:
                    await client.write_gatt_char(CHAR_UUID, chunk)
                    print(f"[INFO] Sent chunk {i // chunk_size + 1}/{-(-len(full_data) // chunk_size)}: {len(chunk)} bytes")
                except Exception as e:
                    print(f"[ERROR] Failed to send chunk {i // chunk_size + 1}: {e}")
                    return
            print("[INFO] All data sent successfully.")
        else:
            print("[ERROR] Failed to connect to peripheral")

# Define image paths and resolution
image_size = (250, 122)  # 横:250, 縦:122
black_image_path = "images/black_image.png"  # 黒色データ用画像ファイルパス
red_image_path = "images/red_image.png"  # 赤色データ用画像ファイルパス

# Main entry point
asyncio.run(send_image(black_image_path, red_image_path, image_size, mtu=244))