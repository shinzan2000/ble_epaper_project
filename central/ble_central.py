import os
import asyncio
from bleak import BleakClient
from PIL import Image, ImageEnhance

ADDRESS = "2C:CF:67:04:CF:1B"  # ペリフェラルのMACアドレス
CHAR_UUID = "87654321-4321-8765-4321-fedcba987654"  # キャラクターID

def prepare_image(file_path, size):
    """
    画像を電子ペーパー用に変換する。
    """
    from PIL import ImageFilter
    
    img = Image.open(file_path).convert("L")  # グレースケールに変換

    # コントラストを強調
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(1.5)  # 1.5倍のコントラスト強調

    # 高解像度でシャープ化
    img = img.resize((size[0] * 2, size[1] * 2), Image.LANCZOS)  # サイズを2倍にする
    img = img.filter(ImageFilter.SHARPEN)

    # 最終解像度にリサイズ
    img = img.resize(size, Image.LANCZOS)

    # しきい値を指定して2値化
    THRESHOLD = 140
    img = img.point(lambda p: 255 if p > THRESHOLD else 0, mode="1")
    
    # 電子ペーパーに合わせて回転
    img = img.rotate(90, expand=True)

    # バイトデータとして返却
    return bytearray(img.tobytes())

def reconstruct_image(data, size, output_path):
    """
    バイトデータから画像を再構築し、保存する。
    """
    try:
        img = Image.frombytes("1", size, bytes(data))
        img.save(output_path)
        print(f"[INFO] Reconstructed image saved to {output_path}")
    except Exception as e:
        print(f"[ERROR] Failed to reconstruct image: {e}")

async def send_image(file_path_black, file_path_red, size, mtu):
    data_black = prepare_image(file_path_black, size)
    data_red = prepare_image(file_path_red, size)

    combined_data = data_black + data_red  # 黒と赤を結合
    total_size = len(combined_data) + 4  # ヘッダー4バイトを加えたデータサイズ
    chunk_size = mtu - 3
    header = total_size.to_bytes(4, byteorder='little')  # ヘッダーは4バイト

    print(f"[DEBUG] Total data size (with header): {total_size} bytes")
    print(f"[DEBUG] Chunk size: {chunk_size} bytes")

    # 実際の送信部分
    async with BleakClient(ADDRESS) as client:
        if await client.is_connected():
            print("[INFO] Connected to peripheral")

            # ヘッダーの送信
            try:
                await client.write_gatt_char(CHAR_UUID, header)
                print("[INFO] Header sent successfully.")
            except Exception as e:
                print(f"[ERROR] Failed to send header: {e}")
                return

            # 画像データの送信
            for i in range(0, len(combined_data), chunk_size):
                chunk = combined_data[i:i + chunk_size]
                try:
                    await client.write_gatt_char(CHAR_UUID, chunk)
                    print(f"[INFO] Sent chunk {i // chunk_size + 1}/{-(-len(combined_data) // chunk_size)}: {len(chunk)} bytes")
                except Exception as e:
                    print(f"[ERROR] Failed to send chunk {i // chunk_size + 1}: {e}")
                    return

            # 終了信号の送信
            try:
                await client.write_gatt_char(CHAR_UUID, b"END")
                print("[INFO] End signal sent successfully.")
            except Exception as e:
                print(f"[ERROR] Failed to send end signal: {e}")
                return

            print("[INFO] All data sent successfully.")
        else:
            print("[ERROR] Failed to connect to peripheral")


def main():
    BLACK_IMAGE_PATH = "images/black_image.png"  # 黒色の入力画像データ
    RED_IMAGE_PATH = "images/red_image.png"  # 赤色の入力画像データ
    OUTPUT_DIR = "output_images"  # 出力ディレクトリ
    IMAGE_SIZE = (250, 122)  # 画像サイズ
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # 黒画像の処理
    black_data = prepare_image(BLACK_IMAGE_PATH, IMAGE_SIZE)
    reconstruct_image(black_data,  (IMAGE_SIZE[1], IMAGE_SIZE[0]), os.path.join(OUTPUT_DIR, "reconstructed_black_image.png"))

    # 赤画像の処理
    red_data = prepare_image(RED_IMAGE_PATH, IMAGE_SIZE)
    reconstruct_image(red_data,  (IMAGE_SIZE[1], IMAGE_SIZE[0]), os.path.join(OUTPUT_DIR, "reconstructed_red_image.png"))

    asyncio.run(send_image(BLACK_IMAGE_PATH, RED_IMAGE_PATH, IMAGE_SIZE, mtu=244))

if __name__ == "__main__":
    main()
