"""The Linux collection."""

from terminal_manager.collection import Collection
from terminal_manager.command import ActionCommand, SensorCommand
from terminal_manager.sensor import BinarySensor, NumberSensor, TextSensor

from .const import ActionKey, ActionName, SensorKey, SensorName

linux = Collection(
    "Linux",
    [
        ActionCommand(
            "/sbin/shutdown -h now",
            ActionName.TURN_OFF,
            ActionKey.TURN_OFF,
        ),
        ActionCommand(
            "/sbin/shutdown -r now",
            ActionName.RESTART,
            ActionKey.RESTART,
        ),
    ],
    [
        # TODO: OS_ARCHITECTURE
        SensorCommand(
            "/sbin/ip route show default | awk '{print $5}' || "
            "/sbin/route -n | awk '/^0.0.0.0/ {print $NF}'",
            sensors=[
                TextSensor(
                    SensorName.NETWORK_INTERFACE,
                    SensorKey.NETWORK_INTERFACE,
                )
            ],
        ),
        SensorCommand(
            "cat /sys/class/net/&{network_interface}/address",
            sensors=[
                TextSensor(
                    SensorName.MAC_ADDRESS,
                    SensorKey.MAC_ADDRESS,
                )
            ],
        ),
        SensorCommand(
            "cat /sys/class/net/&{network_interface}/device/power/wakeup 2>/dev/null",
            sensors=[
                BinarySensor(
                    SensorName.WAKE_ON_LAN,
                    SensorKey.WAKE_ON_LAN,
                )
            ],
        ),
        SensorCommand(
            "uname -n",
            sensors=[
                TextSensor(
                    SensorName.HOSTNAME,
                    SensorKey.HOSTNAME,
                ),
            ],
        ),
        SensorCommand(
            "uname -m",
            sensors=[
                TextSensor(
                    SensorName.MACHINE_TYPE,
                    SensorKey.MACHINE_TYPE,
                ),
            ],
        ),
        SensorCommand(
            "uname -s",
            sensors=[
                TextSensor(
                    SensorName.OS_NAME,
                    SensorKey.OS_NAME,
                ),
            ],
        ),
        SensorCommand(
            "uname -r",
            sensors=[
                TextSensor(
                    SensorName.OS_VERSION,
                    SensorKey.OS_VERSION,
                ),
            ],
        ),
        SensorCommand(
            '/sbin/dmidecode -t system | awk -F": " \''
            "/Product Name:/ {a=$2} "
            "/Version:/ {b=$2} "
            "/Manufacturer:/ {c=$2} "
            "/Serial Number:/ {d=$2} "
            'END {print a"\\n"b"\\n"c"\\n"d}\'',
            sensors=[
                TextSensor(
                    SensorName.DEVICE_NAME,
                    SensorKey.DEVICE_NAME,
                ),
                TextSensor(
                    SensorName.DEVICE_MODEL,
                    SensorKey.DEVICE_MODEL,
                ),
                TextSensor(
                    SensorName.MANUFACTURER,
                    SensorKey.MANUFACTURER,
                ),
                TextSensor(
                    SensorName.SERIAL_NUMBER,
                    SensorKey.SERIAL_NUMBER,
                ),
            ],
        ),
        SensorCommand(
            'cat /proc/cpuinfo | awk -F": " \''
            "/^model name/ {a=$2} "
            "/^processor/ {b=$2+1} "
            "/^Hardware/ {c=$2} "
            "/^Model/ {d=$2} "
            'END {print a"\\n"b"\\n"c"\\n"d}\'',
            sensors=[
                TextSensor(
                    SensorName.CPU_NAME,
                    SensorKey.CPU_NAME,
                ),
                NumberSensor(
                    SensorName.CPU_CORES,
                    SensorKey.CPU_CORES,
                ),
                TextSensor(
                    SensorName.CPU_HARDWARE,
                    SensorKey.CPU_HARDWARE,
                ),
                TextSensor(
                    SensorName.CPU_MODEL,
                    SensorKey.CPU_MODEL,
                ),
            ],
        ),
        SensorCommand(
            "free -k | awk '/^Mem:/ {print $2}'",
            sensors=[
                NumberSensor(
                    SensorName.TOTAL_MEMORY,
                    SensorKey.TOTAL_MEMORY,
                    unit="KiB",
                )
            ],
        ),
        SensorCommand(
            "free -k | awk '/^Mem:/ {print $4}'",
            interval=30,
            sensors=[
                NumberSensor(
                    SensorName.FREE_MEMORY,
                    SensorKey.FREE_MEMORY,
                    unit="KiB",
                )
            ],
        ),
        SensorCommand(
            "df -k | awk '/^\\/dev\\// {"
            'x=$4; $1=$2=$3=$4=$5=""; '
            'gsub(/^ +/, ""); '
            'print $0"|"x}\'',
            interval=60,
            separator="|",
            sensors=[
                NumberSensor(
                    SensorName.FREE_DISK_SPACE,
                    SensorKey.FREE_DISK_SPACE,
                    dynamic=True,
                    unit="KiB",
                )
            ],
        ),
        SensorCommand(
            # https://www.baeldung.com/linux/get-cpu-usage
            "echo $((100-$(vmstat 1 2 | awk 'END {print $15}')))",
            interval=30,
            sensors=[
                NumberSensor(
                    SensorName.CPU_LOAD,
                    SensorKey.CPU_LOAD,
                    unit="%",
                )
            ],
        ),
        SensorCommand(
            "for x in $(ls -d /sys/class/thermal/thermal_zone*); do "
            "echo $(cat $x/type),$(($(cat $x/temp)/1000)); done",
            interval=60,
            separator=",",
            sensors=[
                NumberSensor(
                    SensorName.TEMPERATURE,
                    SensorKey.TEMPERATURE,
                    dynamic=True,
                    unit="°C",
                )
            ],
        ),
        SensorCommand(
            "ps -e | awk 'END {print NR-1}'",
            interval=60,
            sensors=[
                NumberSensor(
                    SensorName.PROCESSES,
                    SensorKey.PROCESSES,
                )
            ],
        ),
    ],
)
