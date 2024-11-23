import ubluetooth
import time
from epaper2in13 import EPD_2in13_B_V4_Landscape
import struct
import hashlib

class BLEPeripheral:
    def __init__(self, name="PicoBLE"):
        self.ble = ubluetooth.BLE()
        self.ble.active(True)
        self.name = name
        self.mtu = 244
        self.ble.config(mtu=self.mtu)
        self.ble.irq(self._irq_handler)
        self._register_services()
        self._advertise()
        self.buffer = bytearray()
        self.expected_size = None  # ヘッダーで設定
        self.received_end_notification = False  # 完了通知フラグ

        self.epd = EPD_2in13_B_V4_Landscape()
        self.epd.init()
        self.epd.Clear(0xFF, 0xFF)
        print("Peripheral initialized and advertising...")
        print(f"Configured MTU size: {self.ble.config('mtu')} bytes")

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
        service_uuid = ubluetooth.UUID("12345678-1234-5678-1234-56789abcdef0")
        char_uuid = ubluetooth.UUID("87654321-4321-8765-4321-fedcba987654")
        char_properties = ubluetooth.FLAG_READ | ubluetooth.FLAG_WRITE

        self.service = (
            service_uuid,
            (
                (char_uuid, char_properties),
            ),
        )
        self.services = (self.service,)
        self.handles = self.ble.gatts_register_services(self.services)
        self.char_handle = self.handles[0][0]
        print("Service and Characteristic registered")

        self.ble.gatts_set_buffer(self.char_handle, self.mtu - 3, True)

    def _advertise(self):
        adv_payload = self._create_adv_payload(name=self.name)
        self.ble.gap_advertise(500_000, adv_payload)
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
        if raw_value == b"END":  # セントラルから送信終了通知を受信
            print("[INFO] Received end notification from central.")
            self.received_end_notification = True
            self._check_and_process_buffer()
            return

        self.buffer.extend(raw_value)
        print(f"[DEBUG] Current buffer length: {len(self.buffer)} / {self.expected_size or 'Unknown'} bytes")

        # 初回受信でヘッダー解析
        if self.expected_size is None:
            if len(self.buffer) >= 4:  # ヘッダーの4バイトを確認
                total_size = struct.unpack("I", self.buffer[:4])[0]  # ヘッダーに格納された総サイズ
                self.expected_size = total_size - 4  # ヘッダーサイズを除外
                self.buffer = self.buffer[4:]  # ヘッダー部分を除去
                print(f"[INFO] Expected data size dynamically set to {self.expected_size}")
            else:
                print("[ERROR] Insufficient data for header parsing. Awaiting more data...")
                return

        self._check_and_process_buffer()

    def _check_and_process_buffer(self):
        # ペリファラル側の完全受信を確認
        if self.received_end_notification:
            # expected_size（セントラルのtotal_sizeに基づく）と受信バッファサイズを検証
            if len(self.buffer) == self.expected_size:
                print("Received full data and end notification, processing buffer...")
                received_hash = hashlib.sha256(self.buffer).hexdigest()
                print(f"[INFO] Received data hash (SHA-256): {received_hash}")
                self._process_buffer()
            elif len(self.buffer) < self.expected_size:
                print(f"[ERROR] Buffer size mismatch: Expected={self.expected_size}, Received={len(self.buffer)}")
                print("[ERROR] Transmission error detected. Please check MTU settings or retransmit.")
            elif len(self.buffer) > self.expected_size:
                print(f"[WARNING] Extra data received: Expected={self.expected_size}, Received={len(self.buffer)}")
                print("[INFO] Adjusting buffer size and processing...")
                self.buffer = self.buffer[:self.expected_size]
                self._process_buffer()

    def _process_buffer(self):
        print(f"[DEBUG] Processing buffer of size: {len(self.buffer)} bytes")
        self.update_display(self.buffer)
        self.buffer = bytearray()
        self.expected_size = None  # リセット
        self.received_end_notification = False

    def update_display(self, data):
        try:
            print(f"Updating display with data of size: {len(data)}")
            half_length = len(data) // 2
            black_buffer = data[:half_length]
            red_buffer = data[half_length:]

            self.epd.Clear(0xFF, 0xFF)
            self.epd.buffer_black[:len(black_buffer)] = black_buffer
            self.epd.buffer_red[:len(red_buffer)] = red_buffer

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