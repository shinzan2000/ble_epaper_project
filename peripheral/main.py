import bluetooth
from micropython import const
import struct
import time

# Constants
_ADV_TYPE = const(0x01)
_MTU_DEFAULT = 23  # Default MTU size

class BLEPeripheral:
    def __init__(self, name="ShelfTag", expected_size=128 * 250 // 8 * 2):
        self.name = name
        self.expected_size = expected_size
        self.buffer = bytearray()
        self.mtu = _MTU_DEFAULT
        self._ble = bluetooth.BLE()
        self._ble.active(True)
        self._register_services()
        self._ble.irq(self._irq)
        self._advertise()
        print(f"Peripheral initialized and advertising...")

    def _register_services(self):
        # Custom GATT service and characteristic
        service_uuid = bluetooth.UUID("12345678-1234-5678-1234-56789abcdef0")
        char_uuid = bluetooth.UUID("87654321-4321-8765-4321-fedcba987654")
        self._char = (char_uuid, bluetooth.FLAG_WRITE)
        self._service = (service_uuid, (self._char,))
        ((self._char_handle,),) = self._ble.gatts_register_services((self._service,))
        print("GATT service registered.")

    def _advertise(self):
        name = bytes(self.name, "utf-8")
        adv_data = bytearray(b"\x02\x01\x06") + bytearray(
            (len(name) + 1, 0x09)
        ) + name
        self._ble.gap_advertise(100_000, adv_data)
        print(f"Advertising started...")

    def _irq(self, event, data):
        if event == bluetooth.IRQ_CENTRAL_CONNECT:
            conn_handle, _, _ = data
            print("Central connected")
            self._conn_handle = conn_handle
            self.mtu = self._ble.gatts_get_mtu(self._conn_handle)
            print(f"MTU after connection: {self.mtu}")

        elif event == bluetooth.IRQ_CENTRAL_DISCONNECT:
            print("Central disconnected")
            self._advertise()

        elif event == bluetooth.IRQ_GATTS_WRITE:
            conn_handle, attr_handle = data
            if attr_handle == self._char_handle:
                self._handle_write_event(attr_handle)

    def _handle_write_event(self, attr_handle):
        # Write event handling
        raw_data = self._ble.gatts_read(attr_handle)
        print(f"Received raw data length: {len(raw_data)}")
        self.buffer.extend(raw_data)

        # Check if buffer overflow occurs
        if len(self.buffer) > self.expected_size:
            print("[ERROR] Buffer overflow detected. Clearing buffer...")
            self.buffer.clear()
            return

        if len(self.buffer) >= self.expected_size:
            print("Received full data, processing buffer...")
            self._process_buffer()

    def _process_buffer(self):
        print(f"Processing buffer of size: {len(self.buffer)}")
        self.update_display(self.buffer)
        self.buffer.clear()

    def update_display(self, data):
        """
        Simulate sending data to an e-paper display.
        """
        print(f"Updating display with data of size: {len(data)}")
        time.sleep(1)
        print("Display update completed successfully.")

def main():
    peripheral = BLEPeripheral()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Shutting down peripheral...")

if __name__ == "__main__":
    main()