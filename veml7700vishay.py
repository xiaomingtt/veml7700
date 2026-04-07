# micropython
# MIT license
# Copyright (c) 2022 Roman Shevchik   goctaprog@gmail.com

import micropython
from sensor_pack import bus_service
from sensor_pack.base_sensor import BaseSensor, Iterator


@micropython.native
def _check_value(value: int, valid_range, error_msg: str) -> int:
    """检查数值是否在有效范围内，无效则抛出异常"""
    if value not in valid_range:
        raise ValueError(error_msg)
    return value


class Veml7700(BaseSensor, Iterator):
    """VEML7700 环境光传感器驱动类
    参考手册：https://www.vishay.com/docs/84286/veml7700.pdf"""
    # 积分时间常量
    _IT = 12, 8, 0, 1, 2, 3

    @staticmethod
    def _it_to_raw_it(it: int) -> int:
        """将用户配置的积分时间，转换为传感器寄存器使用的原始值
        对应关系：
        it    返回值   积分时间(毫秒)
        0     12       25
        1     8        50
        2     0        100
        3     1        200
        4     2        400
        5     3        800
        """
        return Veml7700._IT[it]

    @staticmethod
    def _raw_it_to_it(raw_it: int) -> int:
        """与 _it_to_raw_it 互为逆操作，将原始值转回用户配置值"""
        return Veml7700._IT.index(raw_it)

    @staticmethod
    def _get_integration_time(raw_it: int) -> int:
        """根据原始积分时间值，返回实际积分时间（单位：毫秒）"""
        return 25 * 2 ** raw_it

    @staticmethod
    def _raw_gain_to_gain(raw_gain: int) -> float:
        """将传感器原始增益值(0~3)转换为实际增益系数"""
        _g = 1, 2, 0.125, 0.25
        return _g[raw_gain]

    @staticmethod
    def _check_gain(_gain: float) -> float:
        """校验增益值是否合法"""
        _gains = 0.125, 0.25, 1, 2
        if not _gain in _gains:
            raise ValueError(f"无效的增益值：{_gain}")
        return _gain

    @staticmethod
    def _check_raw(raw_gain: int, raw_it: int):
        """校验原始增益和积分时间参数是否合法"""
        _check_value(raw_gain, range(4), f"无效的ALS增益值：{raw_gain}")
        _check_value(raw_it, range(6), f"无效的ALS原始积分时间：{raw_it}")

    @staticmethod
    def get_max_possible_illumination(raw_gain: int, raw_it: int) -> float:
        """根据增益和积分时间原始值，返回传感器可测量的最大光照强度（单位：勒克斯）"""
        Veml7700._check_raw(raw_gain, raw_it)
        _gain = Veml7700._raw_gain_to_gain(raw_gain)
        _g_base = 0.125
        _max_ill = 120796
        _k = _gain / _g_base
        return (_max_ill / 2 ** raw_it) / _k

    @staticmethod
    def _get_resolution(raw_gain: int, raw_it: int) -> float:
        """根据增益和积分时间，返回传感器最低有效位对应的光照分辨率（单位：勒克斯）"""
        Veml7700._check_raw(raw_gain, raw_it)
        _gain = Veml7700._raw_gain_to_gain(raw_gain)
        _g_base = 0.125
        _max_res = 1.8432
        _k = _gain / _g_base
        return (_max_res / 2 ** raw_it) / _k

    def __init__(self, adapter: bus_service.I2cAdapter, address: int = 0x10):
        """初始化传感器"""
        super().__init__(adapter, address, False)
        self._last_raw_ill = None    # 保存最后一次读取的光照原始值
        self._als_gain = 0           # 增益
        self._als_it = 0             # 积分时间
        self._als_pers = 0           # 中断保护次数设置
        self._als_int_en = False     # 中断使能
        self._als_shutdown = False   # ALS休眠模式
        self._enable_psm = False     # 传感器省电模式使能
        self._psm = 0                # 传感器省电模式等级 0~3

    def _read_register(self, reg_addr, bytes_count=2) -> bytes:
        """从传感器寄存器读取值
        bytes_count - 读取的字节数"""
        return self.adapter.read_register(self.address, reg_addr, bytes_count)

    def _write_register(self, reg_addr, value: int, bytes_count=2) -> int:
        """向传感器指定寄存器写入值
        bytes_count - 写入的字节数"""
        byte_order = self._get_byteorder_as_str()[0]
        return self.adapter.write_register(self.address, reg_addr, value, bytes_count, byte_order)

    def set_config_als(self, gain: int, integration_time: int, persistence: int = 1,
                       interrupt_enable: bool = False, shutdown: bool = False):
        """配置环境光传感器(ALS)参数
        gain = 0~3；0-增益1，1-增益2，2-增益0.125(1/8)，3-增益0.25(1/4)
        integration_time = 0~5；0-25ms；1-50ms；2-100ms，3-200ms，4-400ms，5-800ms
        persistence 中断保护次数 = 0~3；0-1次，1-2次，2-4次，3-8次
        """
        _cfg = 0
        # 手册要求：修改配置前，必须先将传感器进入休眠模式
        _bts = self._read_register(0x00, 2)
        _cfg = self.unpack("H", _bts)[0]
        self._write_register(0x00, _cfg | 0x01, 2)

        _cfg = 0
        gain = _check_value(gain, range(4), f"无效的ALS增益值：{gain}")
        _tmp = _check_value(integration_time, range(6), f"无效的ALS积分时间：{integration_time}")
        it = Veml7700._it_to_raw_it(_tmp)

        pers = _check_value(persistence, range(4), f"无效的ALS保护次数：{persistence}")
        ie = 1 if interrupt_enable else 0
        sd = 1 if shutdown else 0

        # 组装配置寄存器数据
        _cfg |= sd
        _cfg |= ie << 1
        _cfg |= pers << 4
        _cfg |= it << 6
        _cfg |= gain << 11

        self._write_register(0x00, _cfg, 2)
        # 保存当前配置
        self._als_gain = gain
        self._als_it = integration_time
        self._als_pers = pers
        self._als_int_en = interrupt_enable
        self._als_shutdown = shutdown

    def get_config_als(self) -> None:
        """从传感器寄存器读取ALS配置（2字节）"""
        reg_val = self._read_register(0x00, 2)
        cfg = self.unpack("H", reg_val)[0]
        # 解析增益
        tmp = (cfg & 0b0001_1000_0000_0000) >> 11
        self._als_gain = tmp
        # 解析积分时间
        tmp = (cfg & 0b0000_0011_1100_0000) >> 6
        self._als_it = Veml7700._raw_it_to_it(tmp)
        # 解析保护次数
        tmp = (cfg & 0b0000_0000_0011_0000) >> 4
        self._als_pers = tmp
        # 解析中断使能
        self._als_int_en = bool(cfg & 0b0000_0000_0000_0010)
        # 解析休眠状态
        self._als_shutdown = bool(cfg & 0b0000_0000_0000_0001)

    def set_power_save_mode(self, enable_psm: bool, psm: int) -> None:
        """设置传感器省电模式
        enable_psm：省电模式使能，False-关闭，True-开启
        psm：省电模式等级 0~3
        """
        psm = _check_value(psm, range(4), f"无效的省电模式值：{psm}")
        reg_val = 0
        reg_val |= int(enable_psm)
        reg_val |= psm << 1
        self._write_register(0x03, reg_val, 2)
        self._enable_psm = enable_psm
        self._psm = psm

    def get_interrupt_status(self) -> tuple:
        """获取中断状态：数据是否触发了低/高阈值中断
        返回元组(低阈值触发, 高阈值触发)"""
        reg_val = self._read_register(0x06, 2)
        irq_status = self.unpack("H", reg_val)[0]
        # 低阈值中断标志
        int_th_low = bool(irq_status & 0b1000_0000_0000_0000)
        # 高阈值中断标志
        int_th_high = bool(irq_status & 0b0100_0000_0000_0000)
        return int_th_low, int_th_high

    def get_illumination(self, raw=False) -> [int, float]:
        """获取光照强度，默认返回勒克斯(lux)，raw=True返回传感器原始值"""
        reg_val = self._read_register(0x04, 2)
        raw_lux = self.unpack("H", reg_val)[0]
        self._last_raw_ill = raw_lux
        if raw:
            return raw_lux
        return raw_lux * Veml7700._get_resolution(self._als_gain, self._als_it)

    def get_white_channel(self):
        """获取白光通道输出值"""
        reg_val = self._read_register(0x05, 2)
        return self.unpack("H", reg_val)[0]

    def get_high_threshold(self) -> int:
        """获取ALS高阈值设置"""
        reg_val = self._read_register(0x01, 2)
        return self.unpack("H", reg_val)[0]

    def get_low_threshold(self) -> int:
        """获取ALS低阈值设置"""
        reg_val = self._read_register(0x02, 2)
        return self.unpack("H", reg_val)[0]

    def get_id(self):
        """传感器无ID功能，返回None"""
        return None

    def soft_reset(self):
        """软件复位（传感器不支持，返回None）"""
        return None

    @property
    def last_raw(self)->int:
        """返回最后一次读取的光照原始值"""
        return self._last_raw_ill

    def __next__(self) -> float:
        """迭代器方法，返回当前光照强度(lux)"""
        return self.get_illumination(raw=False)

    @micropython.native
    def get_conversion_cycle_time(self, offset: int = 100) -> int:
        """获取传感器转换周期时间（单位：毫秒）
        未开启省电模式时，至少需要等待一个积分时间才能读取有效数据
        """
        base = 25 * 2 ** self._als_it
        if not self._enable_psm:
            return base
        # 开启省电模式时的计算（基于手册推测）
        return offset + base + 500 * (2 ** self._psm)

    @property
    def gain(self) -> tuple[int, float]:
        """返回增益信息：(原始增益值, 实际增益系数)"""
        rg = self._als_gain
        return rg, Veml7700._raw_gain_to_gain(rg)

    @property
    def integration_time(self) -> tuple[int, int]:
        """返回积分时间信息：(原始值, 实际时间毫秒)"""
        rit = self._als_it
        return rit, self._get_integration_time(rit)
