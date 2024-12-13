"""The Windows cmd collection."""

from terminal_manager.collection import Collection
from terminal_manager.command import ActionCommand, SensorCommand
from terminal_manager.sensor import NumberSensor, TextSensor

from .const import ActionKey, ActionName, SensorKey, SensorName

windows_cmd = Collection(
    "Windows",
    [
        ActionCommand(
            "shutdown /s /t 0",
            ActionName.TURN_OFF,
            ActionKey.TURN_OFF,
        ),
        ActionCommand(
            "shutdown /r /t 0",
            ActionName.RESTART,
            ActionKey.RESTART,
        ),
    ],
    [
        # TODO: WAKE_ON_LAN
        SensorCommand(
            "for /f %i in ('wmic path win32_ip4routetable "
            "where \"Destination='0.0.0.0'\" "
            "get InterfaceIndex ^| "
            'findstr /r "\\<[0-9][0-9]*\\>"\') do '
            '@for /f "skip=2 tokens=2,3 delims=," %j in (\'wmic nic '
            'where "InterfaceIndex=%i" '
            "get MACAddress^,NetConnectionID /format:csv') do "
            "@echo %j & @echo %k",
            sensors=[
                TextSensor(
                    SensorName.MAC_ADDRESS,
                    SensorKey.MAC_ADDRESS,
                ),
                TextSensor(
                    SensorName.NETWORK_INTERFACE,
                    SensorKey.NETWORK_INTERFACE,
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
            'for /f "skip=1 tokens=*" %i in (\'wmic ComputerSystem '
            "get SystemType') do "
            "@echo %i",
            sensors=[
                TextSensor(
                    SensorName.MACHINE_TYPE,
                    SensorKey.MACHINE_TYPE,
                ),
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
            "for /f \"skip=1 tokens=*\" %i in ('wmic csproduct get Name') do @echo %i",
            sensors=[
                TextSensor(
                    SensorName.DEVICE_NAME,
                    SensorKey.DEVICE_NAME,
                ),
            ],
        ),
        SensorCommand(
            "for /f \"skip=1 tokens=*\" %i in ('wmic csproduct get Version') do @echo %i",
            sensors=[
                TextSensor(
                    SensorName.DEVICE_MODEL,
                    SensorKey.DEVICE_MODEL,
                ),
            ],
        ),
        SensorCommand(
            "for /f \"skip=1 tokens=*\" %i in ('wmic csproduct get Vendor') do @echo %i",
            sensors=[
                TextSensor(
                    SensorName.MANUFACTURER,
                    SensorKey.MANUFACTURER,
                ),
            ],
        ),
        SensorCommand(
            "for /f \"skip=1 tokens=*\" %i in ('wmic bios get SerialNumber') do @echo %i",
            sensors=[
                TextSensor(
                    SensorName.SERIAL_NUMBER,
                    SensorKey.SERIAL_NUMBER,
                ),
            ],
        ),
        SensorCommand(
            "for /f \"skip=1 tokens=*\" %i in ('wmic cpu get Name') do @echo %i",
            sensors=[
                TextSensor(
                    SensorName.CPU_NAME,
                    SensorKey.CPU_NAME,
                ),
            ],
        ),
        SensorCommand(
            "for /f \"skip=1\" %i in ('wmic cpu get NumberOfCores') do @echo %i",
            sensors=[
                NumberSensor(
                    SensorName.CPU_CORES,
                    SensorKey.CPU_CORES,
                ),
            ],
        ),
        SensorCommand(
            'for /f "skip=1" %i in (\'wmic ComputerSystem '
            "get TotalPhysicalMemory') do "
            "@echo %i",
            sensors=[
                NumberSensor(
                    SensorName.TOTAL_MEMORY,
                    SensorKey.TOTAL_MEMORY,
                    unit="B",
                ),
            ],
        ),
        SensorCommand(
            'for /f "skip=1" %i in (\'wmic OS '
            "get FreePhysicalMemory') do "
            "@echo %i",
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
            'for /f "tokens=1,2" %i in (\'wmic LogicalDisk '
            "get DeviceID^,FreeSpace ^| "
            'findstr ":"\') do '
            "@echo %i^|%j",
            interval=60,
            separator="|",
            sensors=[
                NumberSensor(
                    SensorName.FREE_DISK_SPACE,
                    SensorKey.FREE_DISK_SPACE,
                    dynamic=True,
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
            "path MSAcpi_ThermalZoneTemperature "
            "get CurrentTemperature ^| "
            'findstr /r "\\<[0-9][0-9]*\\>"\') do '
            "@set /a x=(%i - 2732) / 10",
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
            "wmic process get processId | "
            'findstr /r "\\<[0-9][0-9]*\\>" | '
            'find /c /v ""',
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
