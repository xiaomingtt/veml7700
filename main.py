# micropython
# MIT license
# Copyright (c) 2022 Roman Shevchik   goctaprog@gmail.com


# 使用前请阅读此文档！https://www.vishay.com/docs/84286/veml7700.pdf
from machine import I2C, Pin
import veml7700vishay
from sensor_pack.bus_service import I2cAdapter
import time

if __name__ == '__main__':
    # 请根据你的开发板设置scl和sda引脚，否则无法正常工作！
    # 参考：https://docs.micropython.org/en/latest/library/machine.I2C.html#machine-i2c
    i2c = I2C(id=1, scl=Pin(18), sda=Pin(17), freq=400_000) # ESP32S3
    # bus =  I2C(scl=Pin(4), sda=Pin(5), freq=100000)   # ESP8266 示例
    # i2c = I2C(0, scl=Pin(13), sda=Pin(12), freq=400_000)  # Arduino Nano RP2040 Connect 已测试
    # i2c = I2C(id=1, scl=Pin(7), sda=Pin(6), freq=400_000)  # 树莓派 Pico
    adaptor = I2cAdapter(i2c)
    # 初始化光照传感器
    sol = veml7700vishay.Veml7700(adaptor)

    # 如果出现EIO异常，请检查所有接线
    # 增益=1，积分时间=25ms，保护次数=1，关闭中断和休眠模式
    # sol.set_config_als(0, 2, 0, False, False)
    # 配置传感器：增益=3，积分时间=4，保护次数=1，关闭中断和休眠
    # sol.set_config_als(gain=3, integration_time=4, persistence=1, interrupt_enable=False, shutdown=False)
    sol.set_config_als(gain=2, integration_time=0, persistence=1, interrupt_enable=False, shutdown=False)
    # 设置省电模式：关闭省电模式，等级0
    sol.set_power_save_mode(enable_psm=False, psm=0)
    
    delay = old_lux = curr_max = 1
    # 获取当前配置下传感器可测量的最大光照强度（勒克斯）
    mpi = veml7700vishay.Veml7700.get_max_possible_illumination(sol.gain[0], sol.integration_time[0])
    print(f"当前配置下最大可测光照强度 [lux]: {mpi}")

    # 循环读取光照数据（迭代器模式）
    for lux in sol:
        if lux != old_lux:
            curr_max = max(lux, curr_max)
            lt = time.localtime()
            # 读取白光通道值
            wh = sol.get_white_channel()
            # 获取转换周期时间
            delay = sol.get_conversion_cycle_time()
            # 打印时间、光照值、原始值、白光通道、最大值、归一化百分比、转换延时
            print(f"{lt[3:6]}\t光照 [lux]: {lux}\t原始值: {sol.last_raw}\t白光通道: {wh}\t最大值: {curr_max}\t归一化 [%]:\
{100*lux/curr_max}\t延时: {delay} [ms]")
        
        old_lux = lux
        # 当光照超过最大量程95%时输出警告
        if lux > 0.95 * mpi:
            print("当前光照已接近当前配置下的最大测量值！"
                  " 需要重新调整传感器配置！即将达到测量上限！")
        # 按传感器转换时间延时
        time.sleep_ms(delay)
