"""The Linux collection."""

from __future__ import annotations

from terminal_manager.collection import Collection
from terminal_manager.command import ActionCommand, SensorCommand
from terminal_manager.const import ActionKey, SensorKey
from terminal_manager.sensor import BinarySensor, NumberSensor, TextSensor

linux = Collection(
    "Linux",
    [
        ActionCommand(
            "/sbin/shutdown -h now",
            key=ActionKey.TURN_OFF,
        ),
        ActionCommand(
            "/sbin/shutdown -r now",
            key=ActionKey.RESTART,
        ),
    ],
    [
        # TODO: OS_ARCHITECTURE
        SensorCommand(
            "x=$(/sbin/ip route show default 2>/dev/null) && "
            "echo \"$x\" | awk '{print $5}' || "
            "x=$(/sbin/route -n 2>/dev/null) && "
            "echo \"$x\" | awk '/^0.0.0.0/ {print $NF}'",
            sensors=[
                TextSensor(key=SensorKey.NETWORK_INTERFACE),
            ],
        ),
        SensorCommand(
            "cat /sys/class/net/&{network_interface}/address",
            sensors=[
                TextSensor(key=SensorKey.MAC_ADDRESS),
            ],
        ),
        SensorCommand(
            "cat /sys/class/net/&{network_interface}/device/power/wakeup",
            sensors=[
                BinarySensor(key=SensorKey.WAKE_ON_LAN),
            ],
        ),
        SensorCommand(
            "uname -n",
            sensors=[
                TextSensor(key=SensorKey.HOSTNAME),
            ],
        ),
        SensorCommand(
            "uname -m",
            sensors=[
                TextSensor(key=SensorKey.MACHINE_TYPE),
            ],
        ),
        SensorCommand(
            "uname -s",
            sensors=[
                TextSensor(key=SensorKey.OS_NAME),
            ],
        ),
        SensorCommand(
            "uname -r",
            sensors=[
                TextSensor(key=SensorKey.OS_VERSION),
            ],
        ),
        SensorCommand(
            '(. /etc/os-release && echo "$PRETTY_NAME")',
            sensors=[
                TextSensor(key=SensorKey.OS_RELEASE),
            ],
        ),
        SensorCommand(
            "x=$(/sbin/dmidecode -t system 2>/dev/null) && "
            'echo "$x" | awk -F ": " \''
            "/Product Name:/ {a=$2} "
            "/Version:/ {b=$2} "
            "/Manufacturer:/ {c=$2} "
            "/Serial Number:/ {d=$2} "
            'END {print a"\\n"b"\\n"c"\\n"d}\'',
            sensors=[
                TextSensor(key=SensorKey.DEVICE_NAME),
                TextSensor(key=SensorKey.DEVICE_MODEL),
                TextSensor(key=SensorKey.MANUFACTURER),
                TextSensor(key=SensorKey.SERIAL_NUMBER),
            ],
        ),
        SensorCommand(
            'cat /proc/cpuinfo | awk -F ": " \''
            "/^model name/ {a=$2} "
            "/^processor/ {b=$2+1} "
            "/^Hardware/ {c=$2} "
            "/^Model/ {d=$2} "
            'END {print a"\\n"b"\\n"c"\\n"d}\'',
            sensors=[
                TextSensor(key=SensorKey.CPU_NAME),
                NumberSensor(key=SensorKey.CPU_CORES),
                TextSensor(key=SensorKey.CPU_HARDWARE),
                TextSensor(key=SensorKey.CPU_MODEL),
            ],
        ),
        SensorCommand(
            "cat /proc/meminfo | awk '/MemTotal/ {print $2}'",
            sensors=[
                NumberSensor(key=SensorKey.TOTAL_MEMORY, unit="KiB"),
            ],
        ),
        SensorCommand(
            "cat /proc/meminfo | awk '/MemFree/ {print $2}'",
            interval=30,
            sensors=[
                NumberSensor(key=SensorKey.FREE_MEMORY, unit="KiB"),
            ],
        ),
        SensorCommand(
            "x=$(df -k) && "
            'echo "$x" | awk \'/^\\/dev\\// {'
            "b=$4; "
            '$1=$2=$3=$4=$5=""; '
            'gsub(/^ +/, ""); '
            'print $0"|"b}\'',
            interval=60,
            separator="|",
            sensors=[
                NumberSensor(key=SensorKey.FREE_DISK_SPACE, dynamic=True, unit="KiB")
            ],
        ),
        SensorCommand(
            "read _ u n s i w q o t _ < /proc/stat; "
            "i1=$((i+w)); "
            "t1=$((u+n+s+q+o+t+i1)); "
            "sleep 1; "
            "read _ u n s i w q o t _ < /proc/stat; "
            "i2=$((i+w)); "
            "t2=$((u+n+s+q+o+t+i2)); "
            "id=$((i2-i1)); "
            "td=$((t2-t1)); "
            "echo $((100*(td-id)/td))",
            interval=30,
            sensors=[
                NumberSensor(key=SensorKey.CPU_LOAD, unit="%"),
            ],
        ),
        SensorCommand(
            "for x in /sys/class/thermal/thermal_zone*; do "
            'echo "$(cat $x/type),$(($(cat $x/temp)/1000))"; '
            "done",
            interval=60,
            separator=",",
            sensors=[
                NumberSensor(key=SensorKey.TEMPERATURE, dynamic=True, unit="°C"),
            ],
        ),
        SensorCommand(
            "printf '%s\\n' /proc/[0-9]* | wc -l",
            interval=60,
            sensors=[
                NumberSensor(key=SensorKey.PROCESSES),
            ],
        ),
    ],
)
