import subprocess
import re
import struct
import time

# === CONFIGURACIÓN ===
SLAVE_ID = "31"
PORT = "/dev/ttyUSB0"
BAUD = "9600"
PARITY = "none"
DATABITS = "8"
STOPBITS = "1"
BLOCK_SIZE = 48
START_REGISTER = 4097
END_REGISTER = 4516

# Archivos de salida
OUTPUT_TXT = "/home/arocatagliatta/Monitoreo/lectura_filtrada.txt"
OUTPUT_PROM = "/var/lib/node_exporter/textfile_collector/abb.prom"

# === MAPEO DE REGISTROS DOCUMENTADOS ===
# (nombre_metrica, unidad, tipo, descripcion)
referencias = {
    4097: ("three_phase_voltage", "Volt", "Unsigned", "3-phase system voltage"),
    4099: ("voltage_l1", "Volt", "Unsigned", "Phase voltage L1-N"),
    4101: ("voltage_l2", "Volt", "Unsigned", "Phase voltage L2-N"),
    4103: ("voltage_l3", "Volt", "Unsigned", "Phase voltage L3-N"),
    4111: ("three_phase_current", "mA", "Unsigned", "3-phase system current"),
    4113: ("current_l1", "mA", "Unsigned", "Line current L1"),
    4115: ("current_l2", "mA", "Unsigned", "Line current L2"),
    4117: ("current_l3", "mA", "Unsigned", "Line current L3"),
    4143: ("three_phase_active_power", "Watt", "Signed", "3-phase total active power"),
    4145: ("power_l1", "Watt", "Signed", "Active power L1"),
    4147: ("power_l2", "Watt", "Signed", "Active power L2"),
    4149: ("power_l3", "Watt", "Signed", "Active power L3"),
    4151: ("three_phase_reactive_power", "VAr", "Signed", "3-phase reactive power"),
    4167: ("frequency", "mHz", "Unsigned", "Frequency"),
}

# === FUNCIÓN PARA LEER UN BLOQUE ===
def leer_bloque(start_reg, count):
    cmd = [
        "mbpoll", "-m", "rtu",
        "-a", SLAVE_ID,
        "-r", str(start_reg),
        "-c", str(count),
        "-b", BAUD,
        "-P", PARITY,
        "-d", DATABITS,
        "-s", STOPBITS,
        "-1",
        PORT
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout

# === LECTURA COMPLETA ===
def obtener_datos():
    output = ""
    current_reg = START_REGISTER

    while current_reg <= END_REGISTER:
        output += leer_bloque(current_reg, BLOCK_SIZE)
        current_reg += BLOCK_SIZE

    pattern = re.compile(r"\[(\d+)\]:\s+([\d\-]+)")
    valores_16 = [(int(r), int(v)) for r, v in pattern.findall(output)]
    valores_32 = {}

    # Convertir cada par HIGH/LOW en 32 bits
    for i in range(0, len(valores_16) - 1, 2):
        reg_high, val_high = valores_16[i]
        reg_low, val_low = valores_16[i + 1]
        reg_base = reg_high

        if reg_base not in referencias:
            continue

        combined = (val_high << 16) | (val_low & 0xFFFF)

        # Si está marcado como signed → convertir a entero con signo
        if referencias[reg_base][2] == "Signed":
            combined = struct.unpack(">i", struct.pack(">I", combined))[0]

        valores_32[reg_base] = combined

    return valores_32


# === OBTENER DATOS PROCESADOS ===
valores = obtener_datos()

# === GUARDAR ARCHIVO TXT (FORMATO HUMANO) ===
with open(OUTPUT_TXT, "w") as f:
    f.write("Registro\tDescripción\tValor 32-bit\tUnidad\n")
    f.write("-------------------------------------------------------------\n")
    for reg in sorted(valores.keys()):
        nombre, unidad, tipo, desc = referencias[reg]
        f.write(f"{reg}\t{desc}\t{valores[reg]}\t{unidad}\n")

# === GENERAR ARCHIVO PROMETHEUS ===
with open(OUTPUT_PROM, "w") as f:
    timestamp = int(time.time())
    f.write(f"# Archivo generado automáticamente — {timestamp}\n")

    for reg, valor in valores.items():
        nombre, unidad, tipo, desc = referencias[reg]

        # Métrica con etiquetas unit y desc
        f.write(
            f'abb_{nombre}{{unit="{unidad}",desc="{desc}"}} {valor}\n'
        )

print("✅ Exportación completa: TXT + PROM actualizados.")
