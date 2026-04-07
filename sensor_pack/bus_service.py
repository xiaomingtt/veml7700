# micropython
# MIT license
# Copyright (c) 2022 Roman Shevchik   goctaprog@gmail.com

"""用于I/O总线操作的工具类"""

from machine import I2C


class BusAdapter:
    """I/O总线与设备I/O类之间的代理类"""
    def __init__(self, bus):
        self.bus = bus

    def read_register(self, device_addr: int, reg_addr: int, bytes_count: int) -> bytes:
        """从传感器寄存器中读取值。
        device_addr - 总线上的传感器地址。
        reg_addr - 传感器地址空间中的寄存器地址。
        bytes_count - 读取值的字节大小。
        从传感器寄存器中读取值。
        device_addr - 总线上的传感器地址。
        reg_addr - 传感器地址空间中的寄存器地址"""
        raise NotImplementedError

    def write_register(self, device_addr: int, reg_addr: int, value: int,
                       bytes_count: int, byte_order: str):
        """将数据value写入传感器的reg_addr地址处。
        bytes_count - 从value中写入的字节数。
        byte_order - 待写入值中的字节排列顺序。
        将数据value写入传感器的reg_addr地址处。
        bytes_count - 从value中写入的字节数。
        byte_order - 待写入值中的字节排列顺序。
        """
        raise NotImplementedError

    def read(self, device_addr, n_bytes: int) -> bytes:
        raise NotImplementedError

    def write(self, device_addr, buf: bytes):
        raise NotImplementedError


class I2cAdapter(BusAdapter):
    def __init__(self, bus: I2C):
        super().__init__(bus)

    def write_register(self, device_addr: int, reg_addr: int, value: int,
                       bytes_count: int, byte_order: str):
        """将数据value写入传感器的reg_addr地址处。
        bytes_count - 待写入数据的字节数"""
        buf = value.to_bytes(bytes_count, byte_order)
        return self.bus.writeto_mem(device_addr, reg_addr, buf)

    def read_register(self, device_addr: int, reg_addr: int, bytes_count: int) -> bytes:
        """从传感器寄存器中读取值。
        bytes_count - 读取值的字节大小"""
        return self.bus.readfrom_mem(device_addr, reg_addr, bytes_count)

    def read(self, device_addr, n_bytes: int) -> bytes:
        return self.bus.readfrom(device_addr, n_bytes)

    def write(self, device_addr, buf: bytes):
        return self.bus.writeto(device_addr, buf)
