import asyncio
from bleak import BleakClient
from PIL import Image

ADDRESS = "2C:CF:67:04:CF:1B"
CHAR_UUID = "87654321-4321-8765-4321-fedcba987654"

def prepare_image(file_path, size):
    img = Image.open(file_path).convert("1")
    img = img.resize(size)
    data = bytearray(img.tobytes())
    return data

async def send_image(file_path_black, file_path_red, size, mtu):
    data_black = prepare_image(file_path_black, size)
    data_red = prepare_image(file_path_red, size)

    combined_data = data_black + data_red
    chunk_size = mtu - 3

    async with BleakClient(ADDRESS) as client:
        if await client.is_connected():
            print("[INFO] Connected to peripheral")
            print(f"[INFO] Total data size: {len(combined_data)} bytes")

            for i in range(0, len(combined_data), chunk_size):
                chunk = combined_data[i:i + chunk_size]
                try:
                    await client.write_gatt_char(CHAR_UUID, chunk)
                    print(f"[INFO] Sent chunk {i // chunk_size + 1}/{-(-len(combined_data) // chunk_size)}: {len(chunk)} bytes")
                except Exception as e:
                    print(f"[ERROR] Failed to send chunk {i // chunk_size + 1}: {e}")
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