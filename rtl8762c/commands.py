def read_mac(rtl, args):
    mac = rtl.read_mac()
    print(f'MAC: {":".join(map(lambda x: "%02x" % x, mac))}')


def chip_id(rtl, args):
    pass


def write_flash(rtl, args):
    pass
