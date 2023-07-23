from ..collection import Collection
from ..command import ActionCommand, SensorCommand
from ..sensor import BinarySensor, NumberSensor, TextSensor
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
            "df -k | awk '/^\/dev\// {"
            + "x=$4; "
            + '$1=$2=$3=$4=$5=""; '
            + 'sub(/^ +/, "", $0); '
            + 'print $0 "|" x}\'',
            interval=60,
            sensors=[
                NumberSensor(
                    SensorName.FREE_DISK_SPACE,
                    SensorKey.FREE_DISK_SPACE,
                    dynamic=True,
                    separator="|",
                    unit="KiB",
                )
            ],
        ),
        SensorCommand(
            "top -bn1 | awk 'NR<4 && tolower($0) ~ /cpu/ {print 100-$8}'",
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
            "echo $(($(cat /sys/class/thermal/thermal_zone0/temp) / 1000))",
            interval=60,
            sensors=[
                NumberSensor(
                    SensorName.TEMPERATURE,
                    SensorKey.TEMPERATURE,
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
