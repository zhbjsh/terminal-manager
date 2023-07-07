from ..collection import Collection
from ..command import ActionCommand, SensorCommand
from ..sensor import NumberSensor, TextSensor
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
            sensors=[
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
            sensors=[
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
            + "$x.TotalPhysicalMemory;",
            sensors=[
                NumberSensor(
                    SensorName.TOTAL_MEMORY,
                    SensorKey.TOTAL_MEMORY,
                    unit="B",
                )
            ],
        ),
        SensorCommand(
            "$x = Get-CimInstance Win32_OperatingSystem | "
            + "Select FreePhysicalMemory;"
            + "$x.FreePhysicalMemory;",
            interval=30,
            sensors=[
                NumberSensor(
                    SensorName.FREE_MEMORY,
                    SensorKey.FREE_MEMORY,
                    unit="kB",
                )
            ],
        ),
        SensorCommand(
            "Get-CimInstance Win32_LogicalDisk | "
            + "Select DeviceID, FreeSpace | ForEach-Object "
            + '{{$_.DeviceID + "|" + $_.FreeSpace}}',
            interval=300,
            sensors=[
                NumberSensor(
                    SensorName.FREE_DISK_SPACE,
                    SensorKey.FREE_DISK_SPACE,
                    dynamic=True,
                    separator="|",
                    unit="B",
                )
            ],
        ),
        SensorCommand(
            "$x = Get-CimInstance Win32_Processor | "
            + "Select LoadPercentage;"
            + "$x.LoadPercentage;",
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
            "$x = Get-CimInstance msacpi_thermalzonetemperature "
            + '-namespace "root/wmi" | '
            + "Select CurrentTemperature;"
            + "($x.CurrentTemperature - 2732) / 10;",
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
