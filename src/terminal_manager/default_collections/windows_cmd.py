from ..collection import Collection
from ..command import ActionCommand, SensorCommand
from ..sensor import BinarySensor, NumberSensor, TextSensor
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
            "for /f \"skip=1 delims=\" %i in ('wmic ComputerSystem get SystemType') "
            + "do @echo %i",
            [
                TextSensor(
                    SensorName.MACHINE_TYPE,
                    SensorKey.MACHINE_TYPE,
                )
            ],
        ),
        SensorCommand(
            "hostname",
            [
                TextSensor(
                    SensorName.HOSTNAME,
                    SensorKey.HOSTNAME,
                )
            ],
        ),
        SensorCommand(
            "for /f \"skip=1 delims=\" %i in ('wmic OS get Caption') do @echo %i",
            [
                TextSensor(
                    SensorName.OS_NAME,
                    SensorKey.OS_NAME,
                )
            ],
        ),
        SensorCommand(
            "for /f \"skip=1 delims=\" %i in ('wmic OS get Version') do @echo %i",
            [
                TextSensor(
                    SensorName.OS_VERSION,
                    SensorKey.OS_VERSION,
                )
            ],
        ),
        SensorCommand(
            "for /f \"skip=1 delims=\" %i in ('wmic OS get OSArchitecture') do @echo %i",
            [
                TextSensor(
                    SensorName.OS_ARCHITECTURE,
                    SensorKey.OS_ARCHITECTURE,
                )
            ],
        ),
        SensorCommand(
            # TODO: Should return MB but number is too long
            "for /f  %i in ('wmic ComputerSystem get TotalPhysicalMemory ^| "
            + 'findstr /r "\\<[0-9][0-9]*\\>"\') '
            + "do set /a mb=%i / 1024 / 1024",
            [
                NumberSensor(
                    SensorName.TOTAL_MEMORY,
                    SensorKey.TOTAL_MEMORY,
                    unit="MB",
                )
            ],
        ),
        SensorCommand(
            "for /f  %i in ('wmic OS get FreePhysicalMemory ^| "
            + 'findstr /r "\\<[0-9][0-9]*\\>"\') '
            + "do set /a mb=%i / 1024",
            [
                NumberSensor(
                    SensorName.FREE_MEMORY,
                    SensorKey.FREE_MEMORY,
                    unit="MB",
                )
            ],
            interval=30,
        ),
        # TODO: FREE_DISK_SPACE
        SensorCommand(
            "for /f \"skip=1\" %i in ('wmic CPU get LoadPercentage') do @echo %i",
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
            "for /f  %i in ('wmic /namespace:\\\\root\\wmi "
            + "PATH MSAcpi_ThermalZoneTemperature get CurrentTemperature ^| "
            + 'findstr /r "\\<[0-9][0-9]*\\>"\') '
            + "do set /a mb=(%i - 2732) / 10",
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
