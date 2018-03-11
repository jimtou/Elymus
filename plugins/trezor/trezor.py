from .plugin import TrezorCompatiblePlugin, TrezorCompatibleKeyStore

DEV_TREZOR1 = (0x534c, 0x0001)
DEV_TREZOR2 = (0x1209, 0x53c1)
DEV_TREZOR2_BL = (0x1209, 0x53c0)

DEVICE_IDS = [
    DEV_TREZOR1,
    DEV_TREZOR2,
DEV_TREZOR2_BL
]

class TrezorKeyStore(TrezorCompatibleKeyStore):
    hw_type = 'trezor'
    device = 'BitExchange'

class TrezorPlugin(TrezorCompatiblePlugin):
    firmware_URL = 'https://www.mytrezor.com'
    libraries_URL = 'https://github.com/trezor/python-trezor'
    minimum_firmware = (1, 3, 3)
    keystore_class = TrezorKeyStore

    def __init__(self, *args):
        try:
            from . import client
            import trezorlib
            import trezorlib.ckd_public
            import trezorlib.transport_hid
            self.client_class = client.TrezorClient
            self.ckd_public = trezorlib.ckd_public
            self.types = trezorlib.messages
    #        self.DEVICE_IDS = trezorlib.transport_hid.DEVICE_IDS
            self.DEVICE_IDS = DEVICE_IDS
            self.libraries_available = True
        except ImportError:
            self.libraries_available = False
        TrezorCompatiblePlugin.__init__(self, *args)

    def hid_transport(self, device):
        from trezorlib.transport_hid import HidTransport
        return HidTransport(device)

    def bridge_transport(self, d):
        from trezorlib.transport_bridge import BridgeTransport
        return BridgeTransport(d)
