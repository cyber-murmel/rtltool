def read_mac(rtl, args):
    mac = rtl.read_mac()
    print(f'MAC: {":".join(map(lambda x: "%02x" % x, mac))}')


def chip_id(rtl, args):
    pass


def read_flash(rtl, args):
    with open(args.filename, "wb") as file:
        file.write(rtl.read_flash(args.address, args.size))


def erase_flash(rtl, args):
    rtl.erase_flash()


def erase_region(rtl, args):
    rtl.erase_region(args.address, args.size)


def write_flash(rtl, args):
    for address, filename in args.addr_filename:
        with open(filename, "rb") as file:
            rtl.write_flash(address, file.read())


def verify_flash(rtl, args):
    for address, filename in args.addr_filename:
        with open(filename, "rb") as file:
            rtl.verify_flash(address, file.read())
