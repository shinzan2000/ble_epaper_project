import asyncio
from bleak import BleakClient
from PIL import Image

ADDRESS = "2C:CF:67:04:CF:1A"  # ペリフェラルのMACアドレス
CHAR_UUID = "87654321-4321-8765-4321-fedcba987654"

def prepare_image(file_path, size):
    img = Image.open(file_path).convert("1")
    img = img.resize(size)
    data = bytearray(img.tobytes())
    return data

async def send_image(file_path_black, file_path_red, size, mtu):
    data_black = prepare_image(file_path_black, size)
    data_red = prepare_image(file_path_red, size)

    combined_data = data_black + data_red  # 黒と赤を結合
    total_size = len(combined_data) + 4  # ヘッダー4バイトを加えた総データサイズ
    chunk_size = mtu - 3
    header = total_size.to_bytes(4, byteorder='little')  # ヘッダーは4バイト

    async with BleakClient(ADDRESS) as client:
        if await client.is_connected():
            print("[INFO] Connected to peripheral")
            print(f"[INFO] Total data size (with header): {total_size} bytes")
            
            try:
                await client.write_gatt_char(CHAR_UUID, header)
                print("[INFO] Header sent successfully.")
            except Exception as e:
                print(f"[ERROR] Failed to send header: {e}")
                return

            for i in range(0, len(combined_data), chunk_size):
                chunk = combined_data[i:i + chunk_size]
                try:
                    await client.write_gatt_char(CHAR_UUID, chunk)
                    print(f"[INFO] Sent chunk {i // chunk_size + 1}/{-(-len(combined_data) // chunk_size)}: {len(chunk)} bytes")
                except Exception as e:
                    print(f"[ERROR] Failed to send chunk {i // chunk_size + 1}: {e}")
                    return

            try:
                await client.write_gatt_char(CHAR_UUID, b"END")
                print("[INFO] End signal sent successfully.")
            except Exception as e:
                print(f"[ERROR] Failed to send end signal: {e}")
                return

            print("[INFO] All data sent successfully.")
        else:
            print("[ERROR] Failed to connect to peripheral")

# Define image paths and resolution
image_size = (250, 122)
black_image_path = "images/black_image.png"
red_image_path = "images/red_image.png"

# Main entry
asyncio.run(send_image(black_image_path, red_image_path, image_size, mtu=244))