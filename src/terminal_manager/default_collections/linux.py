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
        SensorCommand(
            "cat /sys/class/net/{interface}/address",
            sensors=[
                TextSensor(
                    SensorName.MAC_ADDRESS,
                    SensorKey.MAC_ADDRESS,
                )
            ],
        ),
        SensorCommand(
            "file=/sys/class/net/{interface}/device/power/wakeup; "
            + "[[ ! -f $file ]] || cat $file",
            sensors=[
                BinarySensor(
                    SensorName.WOL_SUPPORT,
                    SensorKey.WOL_SUPPORT,
                    payload_on="enabled",
                )
            ],
        ),
        SensorCommand(
            "/sbin/route -n | awk '/^0.0.0.0/ {{print $NF}}'",
            sensors=[
                TextSensor(
                    SensorName.INTERFACE,
                    SensorKey.INTERFACE,
                )
            ],
        ),
        SensorCommand(
            "uname -a | awk '{{print $1; print $2; print $3; print $(NF-1)}}'",
            sensors=[
                TextSensor(
                    SensorName.OS_NAME,
                    SensorKey.OS_NAME,
                ),
                TextSensor(
                    SensorName.HOSTNAME,
                    SensorKey.HOSTNAME,
                ),
                TextSensor(
                    SensorName.OS_VERSION,
                    SensorKey.OS_VERSION,
                ),
                TextSensor(
                    SensorName.MACHINE_TYPE,
                    SensorKey.MACHINE_TYPE,
                ),
            ],
        ),
        # TODO: OS_ARCHITECTURE
        SensorCommand(
            "free -k | awk '/^Mem:/ {{print $2}}'",
            sensors=[
                NumberSensor(
                    SensorName.TOTAL_MEMORY,
                    SensorKey.TOTAL_MEMORY,
                    unit="KiB",
                )
            ],
        ),
        SensorCommand(
            "free -k | awk '/^Mem:/ {{print $4}}'",
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
            "df -k | awk '/^\\/dev\\// {{print $6 \"|\" $4}}'",
            interval=300,
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
            "top -bn1 | awk 'NR<4 && tolower($0)~/cpu/ {{print 100-$8}}'",
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
                    float=True,
                )
            ],
        ),
    ],
)
