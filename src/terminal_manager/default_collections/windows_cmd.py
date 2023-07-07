from ..collection import Collection
from ..command import ActionCommand, SensorCommand
from ..sensor import NumberSensor, TextSensor
from .const import ActionKey, ActionName, SensorKey, SensorName

windows_cmd = Collection(
    "Windows",
    [
        ActionCommand(
            "shutdown -t 0",
            ActionName.TURN_OFF,
            ActionKey.TURN_OFF,
        ),
        ActionCommand(
            "shutdown -r -t 0",
            ActionName.RESTART,
            ActionKey.RESTART,
        ),
    ],
    [
        # TODO: MAC_ADDRESS
        # TODO: WOL_SUPPORT
        # TODO: INTERFACE
        SensorCommand(
            "for /f \"skip=1 tokens=*\" %i in ('wmic ComputerSystem get SystemType') "
            + "do @echo %i",
            sensors=[
                TextSensor(
                    SensorName.MACHINE_TYPE,
                    SensorKey.MACHINE_TYPE,
                ),
            ],
        ),
        SensorCommand(
            "hostname",
            sensors=[
                TextSensor(
                    SensorName.HOSTNAME,
                    SensorKey.HOSTNAME,
                )
            ],
        ),
        SensorCommand(
            "for /f \"skip=1 tokens=*\" %i in ('wmic OS get Caption') do @echo %i",
            sensors=[
                TextSensor(
                    SensorName.OS_NAME,
                    SensorKey.OS_NAME,
                ),
            ],
        ),
        SensorCommand(
            "for /f \"skip=1\" %i in ('wmic OS get Version') do @echo %i",
            sensors=[
                TextSensor(
                    SensorName.OS_VERSION,
                    SensorKey.OS_VERSION,
                ),
            ],
        ),
        SensorCommand(
            "for /f \"skip=1\" %i in ('wmic OS get OSArchitecture') do @echo %i",
            sensors=[
                TextSensor(
                    SensorName.OS_ARCHITECTURE,
                    SensorKey.OS_ARCHITECTURE,
                ),
            ],
        ),
        SensorCommand(
            "for /f \"skip=1\" %i in ('wmic ComputerSystem get TotalPhysicalMemory') "
            + "do @echo %i",
            sensors=[
                NumberSensor(
                    SensorName.TOTAL_MEMORY,
                    SensorKey.TOTAL_MEMORY,
                    unit="B",
                ),
            ],
        ),
        SensorCommand(
            "for /f \"skip=1\" %i in ('wmic OS get FreePhysicalMemory') do @echo %i",
            interval=30,
            sensors=[
                NumberSensor(
                    SensorName.FREE_MEMORY,
                    SensorKey.FREE_MEMORY,
                    unit="kB",
                ),
            ],
        ),
        SensorCommand(
            'for /f "tokens=1,2" %i in (\'wmic LogicalDisk get DeviceID^, FreeSpace ^| '
            + 'findstr ":"\') '
            + "do @echo %i^|%j",
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
            "for /f \"skip=1\" %i in ('wmic CPU get LoadPercentage') do @echo %i",
            interval=30,
            sensors=[
                NumberSensor(
                    SensorName.CPU_LOAD,
                    SensorKey.CPU_LOAD,
                    unit="%",
                ),
            ],
        ),
        SensorCommand(
            "for /f %i in ('wmic /namespace:\\\\root\\wmi "
            + "PATH MSAcpi_ThermalZoneTemperature get CurrentTemperature ^| "
            + 'findstr /r "\\<[0-9][0-9]*\\>"\') '
            + "do @set /a x=(%i - 2732) / 10",
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
