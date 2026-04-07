# micropython
# MIT license
# Copyright (c) 2022 Roman Shevchik   goctaprog@gmail.com

import micropython
import ustruct
from sensor_pack import bus_service


class BaseSensor:
    """传感器基类"""

    def __init__(self, adapter: bus_service.BusAdapter, address: int, big_byte_order: bool):
        """基础传感器类。
        如果 big_byte_order 等于 True -> 传感器寄存器中的字节序为「大端序」
        （高位字节在前，低位字节在后），否则寄存器中的字节序为「小端序」
        （低位字节在前，高位字节在后）
        address - 总线上的传感器地址。

        基础传感器类。如果 big_byte_order 为 True -> 寄存器值字节序为「大端」
        否则寄存器值字节序为「小端」
        address - 总线上的传感器地址。"""
        self.adapter = adapter
        self.address = address
        self.big_byte_order = big_byte_order

    def _get_byteorder_as_str(self) -> tuple:
        """以字符串形式返回字节序配置"""
        if self.is_big_byteorder():
            return 'big', '>'
        else:
            return 'little', '<'

    def unpack(self, fmt_char: str, source: bytes) -> tuple:
        """对从传感器读取的数组进行解包。
        fmt_char: 格式字符，可选 c, b, B, h, H, i, I, l, L, q, Q。详情参考：https://docs.python.org/3/library/struct.html"""
        if len(fmt_char) != 1:
            raise ValueError(f"格式字符参数长度无效：{len(fmt_char)}")
        bo = self._get_byteorder_as_str()[1]
        return ustruct.unpack(bo + fmt_char, source)

    @micropython.native
    def is_big_byteorder(self) -> bool:
        """判断是否为大端字节序"""
        return self.big_byte_order

    def get_id(self):
        """获取传感器ID（需子类实现）"""
        raise NotImplementedError

    def soft_reset(self):
        """传感器软复位（需子类实现）"""
        raise NotImplementedError


class Iterator:
    """基础迭代器类"""
    def __iter__(self):
        """返回迭代器自身"""
        return self

    def __next__(self):
        """迭代器取下一个元素（需子类实现）"""
        raise NotImplementedError
