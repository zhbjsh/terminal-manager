from ..collection import Collection
from ..command import ActionCommand, SensorCommand
from ..sensor import BinarySensor, NumberSensor, TextSensor
from .const import ActionKey, ActionName, SensorKey, SensorName

windows_ps = Collection(
    "Windows (Power Shell)",
    [
        ActionCommand(
            "Stop-Computer -Force",
            ActionName.TURN_OFF,
            ActionKey.TURN_OFF,
        ),
        ActionCommand(
            "Restart-Computer -Force",
            ActionName.RESTART,
            ActionKey.RESTART,
        ),
    ],
    [
        # TODO: MAC_ADDRESS
        # TODO: WOL_SUPPORT
        # TODO: INTERFACE
        SensorCommand(
            "$x = Get-CimInstance Win32_ComputerSystem | "
            + "Select Name, SystemType;"
            + "$x.Name;"
            + "$x.SystemType;",
            [
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
        SensorCommand(
            "$x = Get-CimInstance Win32_OperatingSystem | "
            + "Select Caption, Version, OSArchitecture;"
            + "$x.Caption;"
            + "$x.Version;"
            + "$x.OSArchitecture;",
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
                    SensorName.OS_ARCHITECTURE,
                    SensorKey.OS_ARCHITECTURE,
                ),
            ],
        ),
        SensorCommand(
            "$x = Get-CimInstance Win32_ComputerSystem | "
            + "Select TotalPhysicalMemory;"
            + "[math]::Round($x.TotalPhysicalMemory/1MB);",
            [
                NumberSensor(
                    SensorName.TOTAL_MEMORY,
                    SensorKey.TOTAL_MEMORY,
                    unit="MB",
                )
            ],
        ),
        SensorCommand(
            "$x = Get-CimInstance Win32_OperatingSystem | "
            + "Select FreePhysicalMemory;"
            + "[math]::Round($x.FreePhysicalMemory/1KB);",
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
            "Get-CimInstance Win32_LogicalDisk | "
            + "Select DeviceID, FreeSpace | ForEach-Object "
            + '{{$_.DeviceID+"|"+[math]::Round($_.FreeSpace/1MB)}}',
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
            "$x = Get-CimInstance Win32_Processor | "
            + "Select LoadPercentage;"
            + "$x.LoadPercentage;",
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
            "$x = Get-CimInstance msacpi_thermalzonetemperature "
            + '-namespace "root/wmi" | '
            + "Select CurrentTemperature;"
            + "($x.CurrentTemperature - 2732) / 10;",
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
