from __future__ import annotations

from enum import StrEnum


class ActionKey(StrEnum):
    TURN_OFF = "turn_off"
    RESTART = "restart"


class SensorKey(StrEnum):
    NETWORK_INTERFACE = "network_interface"
    MAC_ADDRESS = "mac_address"
    WAKE_ON_LAN = "wake_on_lan"
    MACHINE_TYPE = "machine_type"
    HOSTNAME = "hostname"
    OS_NAME = "os_name"
    OS_VERSION = "os_version"
    OS_RELEASE = "os_release"
    OS_ARCHITECTURE = "os_architecture"
    DEVICE_NAME = "device_name"
    DEVICE_MODEL = "device_model"
    MANUFACTURER = "manufacturer"
    SERIAL_NUMBER = "serial_number"
    CPU_NAME = "cpu_name"
    CPU_CORES = "cpu_cores"
    CPU_HARDWARE = "cpu_hardware"
    CPU_MODEL = "cpu_model"
    TOTAL_MEMORY = "total_memory"
    FREE_MEMORY = "free_memory"
    CPU_LOAD = "cpu_load"
    FREE_DISK_SPACE = "free_disk_space"
    TEMPERATURE = "temperature"
    PROCESSES = "processes"


ACTION_NAMES = {
    ActionKey.TURN_OFF: "Turn off",
    ActionKey.RESTART: "Restart",
}

SENSOR_NAMES = {
    SensorKey.NETWORK_INTERFACE: "Network interface",
    SensorKey.MAC_ADDRESS: "MAC address",
    SensorKey.WAKE_ON_LAN: "Wake on LAN",
    SensorKey.MACHINE_TYPE: "Machine type",
    SensorKey.HOSTNAME: "Hostname",
    SensorKey.OS_NAME: "OS name",
    SensorKey.OS_VERSION: "OS version",
    SensorKey.OS_RELEASE: "OS release",
    SensorKey.OS_ARCHITECTURE: "OS architecture",
    SensorKey.DEVICE_NAME: "Device name",
    SensorKey.DEVICE_MODEL: "Device model",
    SensorKey.MANUFACTURER: "Manufacturer",
    SensorKey.SERIAL_NUMBER: "Serial number",
    SensorKey.CPU_NAME: "CPU name",
    SensorKey.CPU_CORES: "CPU cores",
    SensorKey.CPU_HARDWARE: "CPU hardware",
    SensorKey.CPU_MODEL: "CPU model",
    SensorKey.TOTAL_MEMORY: "Total memory",
    SensorKey.FREE_MEMORY: "Free memory",
    SensorKey.CPU_LOAD: "CPU load",
    SensorKey.FREE_DISK_SPACE: "Free disk space",
    SensorKey.TEMPERATURE: "Temperature",
    SensorKey.PROCESSES: "Processes",
}
