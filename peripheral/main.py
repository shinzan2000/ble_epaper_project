import ubluetooth
import time
from epaper2in13 import EPD_2in13_B_V4_Landscape

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
        self.expected_size = 128 * 250 // 8 * 2

        # 電子ペーパーの初期化処理を復元
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
        print(f"Received raw data length: {len(raw_value)}")
        self.buffer.extend(raw_value)

        if len(self.buffer) == self.expected_size:
            print("Received full data, processing buffer...")
            self._process_buffer()

    def _process_buffer(self):
        print(f"[DEBUG] Buffer size: {len(self.buffer)} bytes")
        self.update_display(self.buffer)
        self.buffer = bytearray()

    def update_display(self, data):
        try:
            print(f"Updating display with data of size: {len(data)}")
            half_length = len(data) // 2
            black_buffer = data[:half_length]
            red_buffer = data[half_length:]

            # 電子ペーパーの更新処理を復元
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