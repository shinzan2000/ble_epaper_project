import ubluetooth
import time
import struct
import machine
from epaper2in13 import EPD_2in13_B_V4_Portrait, EPD_2in13_B_V4_Landscape

class BLEPeripheral:
    def __init__(self, name="PicoBLE"):
        self.name = name
        self.mtu = 244
        self.ble = ubluetooth.BLE()
        self.ble.active(True)
        self.ble.config(mtu=self.mtu)
        self.ble.irq(self._irq_handler)
        self._register_services()
        self._advertise()
        self.buffer = bytearray()
        self.expected_size = None
        self.received_end_notification = False
        self.timer = machine.Timer(-1)  # 描画処理用のハードウェアタイマーを初期化

        self.epd = EPD_2in13_B_V4_Portrait()
        self.epd.init()
        self.epd.Clear(0xFF, 0xFF)
        print("Peripheral initialized and advertising...")
        print(f"Configured MTU size: {self.ble.config('mtu')} bytes")
        print(f"[DEBUG] EPD black buffer size: {len(self.epd.buffer_black)}")
        print(f"[DEBUG] EPD red buffer size: {len(self.epd.buffer_red)}")

    def _irq_handler(self, event, data):
        if event == 1:  # _IRQ_CENTRAL_CONNECT
            print("Central connected")
        elif event == 2:  # _IRQ_CENTRAL_DISCONNECT
            print("Central disconnected")
            self._advertise()
        elif event == 3:  # _IRQ_GATTS_WRITE
            conn_handle, attr_handle = data
            if attr_handle == self.char_handle:
                self._handle_write_event(attr_handle)
        elif event == 21:  # _IRQ_MTU_EXCHANGED
            conn_handle, mtu = data
            self.mtu = mtu
            print(f"MTU exchange completed. Negotiated MTU: {mtu}")

    def _register_services(self):
        SERVICE_UUID = ubluetooth.UUID("12345678-1234-5678-1234-56789abcdef0")
        CHAR_UUID = ubluetooth.UUID("87654321-4321-8765-4321-fedcba987654")
        CHAR_PROPERTIES = ubluetooth.FLAG_READ | ubluetooth.FLAG_WRITE

        self.service = (
            SERVICE_UUID,
            (
                (CHAR_UUID, CHAR_PROPERTIES),
            ),
        )
        self.services = (self.service,)
        self.handles = self.ble.gatts_register_services(self.services)
        self.char_handle = self.handles[0][0]
        print("Service and Characteristic registered")
        self.ble.gatts_set_buffer(self.char_handle, self.mtu - 3, True)

    def _advertise(self):
        adv_payload = self._create_adv_payload(name=self.name)
        self.ble.gap_advertise(1000_000, adv_payload)
        print("Advertising started...")

    def _create_adv_payload(self, name):
        import struct
        payload = bytearray()
        name_bytes = name.encode()
        payload.extend(struct.pack("BB", len(name_bytes) + 1, 0x09))
        payload.extend(name_bytes)
        return payload

    def _handle_write_event(self, attr_handle):
        raw_value = self.ble.gatts_read(attr_handle)
        print(f"Received raw data length: {len(raw_value)} bytes")

        # データ終了時の処理
        if raw_value == b"END":
            print("[INFO] Received end notification from central.")
            self.received_end_notification = True

            # 描画処理をタイマーで遅延させてスケジュール
            self.timer.init(
                mode=machine.Timer.ONE_SHOT,  # 一回限りのタイマー
                period=1000,  # 1秒後に描画処理を開始
                callback=lambda t: self._check_and_process_buffer()
            )
            return

        self.buffer.extend(raw_value)
        print(f"[DEBUG] Current buffer length: {len(self.buffer)} / {self.expected_size or 'Unknown'} bytes")

        if self.expected_size is None:
            if len(self.buffer) >= 4:
                total_size = struct.unpack("I", self.buffer[:4])[0]
                self.expected_size = total_size - 4
                self.buffer = self.buffer[4:]
                print(f"[INFO] Expected data size dynamically set to {self.expected_size}")
            else:
                print("[ERROR] Insufficient data for header parsing. Awaiting more data...")
                return

        self._check_and_process_buffer()

    def _check_and_process_buffer(self):
        if self.received_end_notification:
            if len(self.buffer) == self.expected_size:
                print("[INFO] Starting buffer processing...")
                self._process_buffer()
            elif len(self.buffer) < self.expected_size:
                print(f"[ERROR] Buffer size mismatch: Expected={self.expected_size}, Received={len(self.buffer)}")

            else:
                print(f"[WARNING] Extra data received: Expected={self.expected_size}, Received={len(self.buffer)}")


    def _process_buffer(self):
        print(f"[DEBUG] Processing buffer of size: {len(self.buffer)} bytes")
        self.update_display(self.buffer)
        self.buffer = bytearray()
        self.expected_size = None
        self.received_end_notification = False
        time.sleep(1)  # 短時間待機してから再アドバタイズを実行
        self._advertise()  # 画面描画後にアドバタイズを再開

    def update_display(self, data):
        try:
            print(f"Updating display with data of size: {len(data)}")
            half_length = len(data) // 2
            black_buffer = data[:half_length]
            red_buffer = data[half_length:]

            # デバッグ: バッファの内容を一部確認

            print(f"[DEBUG] Black buffer size: {len(black_buffer)}")
            print(f"[DEBUG] Red buffer size: {len(red_buffer)}")

            self.epd.Clear(0xFF, 0xFF)
            self.epd.buffer_black[:len(black_buffer)] = black_buffer
            self.epd.buffer_red[:len(red_buffer)] = red_buffer

            # デバッグ: バッファ設定後の確認
            print(f"[DEBUG] EPD black buffer (first 64 bytes): {self.epd.buffer_black[:64]}")
            print(f"[DEBUG] EPD red buffer (first 64 bytes): {self.epd.buffer_red[:64]}")

            self.epd.display()
            print("Display updated successfully.")
        except Exception as e:
            print(f"Error updating display: {e}")

def main():
    BLEPeripheral(name="ShelfTag")
    while True:
        time.sleep(1)

if __name__ == "__main__":
    main()
