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
            [
                TextSensor(
                    SensorName.MAC_ADDRESS,
                    SensorKey.MAC_ADDRESS,
                )
            ],
        ),
        SensorCommand(
            "cat /sys/class/net/{interface}/device/power/wakeup",
            [
                BinarySensor(
                    SensorName.WOL_SUPPORT,
                    SensorKey.WOL_SUPPORT,
                    payload_on="enabled",
                )
            ],
        ),
        SensorCommand(
            "/sbin/route -n | awk '($1 == \"0.0.0.0\") {{print $NF; exit}}'",
            [
                TextSensor(
                    SensorName.INTERFACE,
                    SensorKey.INTERFACE,
                )
            ],
        ),
        SensorCommand(
            "uname -a | awk '{{print $1; print $3; print $2; print $(NF-1);}}'",
            [
                TextSensor(
                    SensorName.OS_NAME,
                    SensorKey.OS_NAME,
                ),
                TextSensor(
                    SensorName.OS_VERSION,
                    SensorKey.OS_VERSION,
                ),
                TextSensor(
                    SensorName.HOSTNAME,
                    SensorKey.HOSTNAME,
                ),
                TextSensor(
                    SensorName.MACHINE_TYPE,
                    SensorKey.MACHINE_TYPE,
                ),
            ],
        ),
        # TODO: OS_ARCHITECTURE
        SensorCommand(
            "free -m | awk 'tolower($0)~/mem/ {{print $2}}'",
            [
                NumberSensor(
                    SensorName.TOTAL_MEMORY,
                    SensorKey.TOTAL_MEMORY,
                    unit="MB",
                )
            ],
        ),
        SensorCommand(
            "free -m | awk 'tolower($0)~/mem/ {{print $4}}'",
            [
                NumberSensor(
                    SensorName.FREE_MEMORY,
                    SensorKey.FREE_MEMORY,
                    unit="MB",
                )
            ],
            interval=30,
        ),
        SensorCommand(
            "df -m | awk '/^\\/dev\\// {{print $6 \"|\" $4}}'",
            [
                NumberSensor(
                    SensorName.FREE_DISK_SPACE,
                    SensorKey.FREE_DISK_SPACE,
                    dynamic=True,
                    separator="|",
                    unit="MB",
                )
            ],
            interval=300,
        ),
        SensorCommand(
            "top -bn1 | head -n3 | awk 'tolower($0)~/cpu/ "
            + "{{for(i=1;i<NF;i++){{if(tolower($i)~/cpu/)"
            + "{{idle=$(i+7); print 100-idle;}}}}}}'",
            [
                NumberSensor(
                    SensorName.CPU_LOAD,
                    SensorKey.CPU_LOAD,
                    unit="%",
                )
            ],
            interval=30,
        ),
        SensorCommand(
            "echo $(($(cat /sys/class/thermal/thermal_zone0/temp) / 1000))",
            [
                NumberSensor(
                    SensorName.TEMPERATURE,
                    SensorKey.TEMPERATURE,
                    unit="°C",
                )
            ],
            interval=60,
        ),
    ],
)
