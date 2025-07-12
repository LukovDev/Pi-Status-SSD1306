#
# main.py - Файл который выводит минимальную системную инфу на экранчик ssd1306 по i2c.
#
# Проект построен на основе Pi-Status-Panel!
#


# Импортируем:
import os
import time
import psutil
from PIL import ImageFont
from datetime import datetime
from luma.oled.device import ssd1306
from luma.core.render import canvas
from luma.core.interface.serial import i2c


# ---------------- ФУНКЦИИ НИЖЕ ИЗ ПРОЕКТА Pi-Status-Panel (utils.py)! ----------------


# Получить вывод команды:
def get_cmd_result(cmd: str) -> str:
    try:
        with os.popen(cmd) as f:
            value = str(f.read().strip())
        return value
    except Exception:
        return "n/a"


# Прочитать информацию об оперативной памяти:
def _read_meminfo_() -> dict:
    info = {}
    with open("/proc/meminfo") as f:
        for L in f:
            key, val = L.split(":", 1)
            info[key] = int(val.split()[0])
    return info


# Округлить размер памяти:
def format_memory_size(bytes_size: int) -> str:
    units = ["B", "KB", "MB", "GB", "TB", "PB"]
    size = float(bytes_size)
    for unit in units:
        if size < 1024:
            return f"{round(size, 2)} {unit}"
        size /= 1024
    return f"{bytes_size} B"


# Получить сколько времени прошло с момента запуска системы:
def format_uptime() -> str:
    with open("/proc/uptime", "r") as f:
        uptime_seconds = float(f.readline().split()[0])
    minutes, seconds = divmod(int(uptime_seconds), 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    return f"{days:02}:{hours:02}:{minutes:02}:{seconds:02}"


# Ждём до следующей системной секунды:
def wait_for_next_second() -> None:
    time.sleep(1 - (time.time() % 1))


# Получить загруженность вентилятора от 0 до 100%:
def get_fan_percent() -> str:
    try:
        return str(round(int(get_cmd_result("cat /sys/class/hwmon/hwmon*/pwm1"))/255*100, 1))
    except Exception:
        return "n/a"


# Получить архитектуру процессора:
def get_arch() -> str:
    return get_cmd_result("uname -m")


# Получить температуру процессора:
def get_cpu_temp() -> str:
    values = []
    try:
        for i in range(5):  # 5 раз запрашиваем температуру чтобы узнать среднее значение:
            values.append(int(get_cmd_result("cat /sys/class/thermal/thermal_zone0/temp"))/1000)
        return str(round(sum(values)/len(values), 1))
    except Exception:
        return "n/a"


# Получить текущую частоту процессора (в ГГц):
def get_cpu_freq() -> str:
    try:
        value = get_cmd_result("vcgencmd measure_clock arm")
        return str(round(int(value.split("=")[1])/1000/1000/1000, 2))
    except Exception:
        return "n/a"


# Получить минимальную частоту процессора (в ГГц):
def get_cpu_min_freq() -> str:
    try:
        return str(round(int(get_cmd_result("cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_min_freq"))/1000/1000, 2))
    except Exception:
        return "n/a"


# Получить максимальную частоту процессора (в ГГц):
def get_cpu_max_freq() -> str:
    try:
        return str(round(int(get_cmd_result("cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_max_freq"))/1000/1000, 2))
    except Exception:
        return "n/a"


# Получить общую загруженность процессора:
def get_cpu_usage() -> float:
    return psutil.cpu_percent()  # ЭТОТ КОД НЕ ТОТ ЧТО В ОРИГИНАЛЬНОМ utils.py


# Получить сколько занято пространства в оперативной памяти в байтах:
def get_ram_used_size() -> int:
    info = _read_meminfo_()
    return int((info.get("MemTotal", 0)-info.get("MemAvailable", 0))*1024)


# Получить сколько всего пространства в оперативной памяти в байтах:
def get_ram_total_size() -> int:
    return int(_read_meminfo_().get("MemTotal", 0)*1024)


# Получить сколько занято пространства в хранилище в байтах:
def get_storage_used_size() -> int|str:
    return psutil.disk_usage("/").used


# Получить сколько всего пространства в хранилище в байтах:
def get_storage_total_size() -> int|str:
    return psutil.disk_usage("/").total

# -------------------------------------------------------------------------------------


# Основная функция программы:
def main() -> None:
    address    = 0x3C   # Адрес дисплея по I2C.
    brightness = 100.0  # Яркость экрана в процентах (0.0-100.0).

    # Подключение OLED дисплея:
    serial = i2c(port=1, address=address)
    device = ssd1306(serial, width=128, height=64)
    device.contrast(max(min(int(brightness / 100 * 255), 255), 0))

    # Шрифт с поддержкой кириллицы:
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 10)

    try:
        # Вечный цикл:
        while True:
            # Получаем данные:
            cpu = get_cpu_usage()
            cpu_arch = get_arch()
            cpu_temp = get_cpu_temp()
            fan_percent = get_fan_percent()
            cpu_freq = get_cpu_freq()
            cpu_freq_min = get_cpu_min_freq()
            cpu_freq_max = get_cpu_max_freq()
            ram_percent = str(round(get_ram_used_size()/get_ram_total_size()*100, 1))
            ram_used = format_memory_size(get_ram_used_size())
            disk_percent = str(round(get_storage_used_size()/get_storage_total_size()*100, 1))
            disk_used = format_memory_size(get_storage_used_size())
            uptime = format_uptime()

            # Выводимые тексты:
            texts = [
                f"CPU: {round(cpu, 1)}% [{cpu_arch}]",
                f"Tmp: {cpu_temp}°C Fan: {fan_percent}%",
                f"Freq: {cpu_freq} GHz [{cpu_freq_min}-{cpu_freq_max}]",
                f"RAM: {ram_percent}% [{ram_used}]",
                f"Disk: {disk_percent}% [{disk_used}]",
                f"Uptime: {uptime}",
            ]

            # Смещения:
            x, y = 0, 0

            # Рисуем:
            with canvas(device) as draw:
                for idx, text in enumerate(texts):
                    draw.text((x, y+idx*10), text, font=font, fill=255)
            wait_for_next_second()  # Задержка до системного тика секунды.
    except KeyboardInterrupt:
        device.hide()
        device.clear()
        device.show()


# Если этот скрипт запускают:
if __name__ == "__main__":
    main()


"""
    < Pi-Status-SSD1306 >
    By LukovDev (@mr_lukov).
    License: MIT
    lakuworx@gmail.com

    Thank you for Using!
"""
