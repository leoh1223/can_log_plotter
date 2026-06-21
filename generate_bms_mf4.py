import numpy as np
from asammdf import MDF, Signal
import time

print("Generating 30-Minute BMS .mf4 Telemetry File...")
start_time = time.time()

# 1. Create a time array (30 minutes at 100Hz = 180,000 samples)
# This is mathematically identical to the massive ASC log we built, but in binary!
fps = 100
total_seconds = 30 * 60
timestamps = np.linspace(0, total_seconds, total_seconds * fps)

# 2. Simulate the EV Physics (Vectorized for extreme speed)
print("Calculating physics vectors...")

# SoC drops linearly from 100% to 20%
soc_data = 100.0 - (80.0 * (timestamps / total_seconds))

# Current spikes (accel) and negative dips (regen) every 10 seconds
current_data = np.sin(timestamps * (2 * np.pi / 10)) * 150.0 

# Pack voltage sags based on current draw
pack_voltage_data = 400.0 - (current_data * 0.05)

# Temp rises from 25C to 45C over the 30 minutes
temp_data = 25.0 + (20.0 * (timestamps / total_seconds))

# Cell voltages hovering around the pack average
base_cell = pack_voltage_data / 96.0
cell1_data = base_cell + (np.sin(timestamps * 5) * 0.01)
cell2_data = base_cell + (np.cos(timestamps * 3) * 0.01)
cell3_data = base_cell - (np.sin(timestamps * 2) * 0.01)

# 3. Create asammdf Signal Objects
# Notice how these EXACTLY match the names and units from your bms.dbc!
print("Packing signals into ASAM MDF4 format...")
signals = [
    Signal(samples=soc_data, timestamps=timestamps, name='State_of_Charge', unit='%'),
    Signal(samples=pack_voltage_data, timestamps=timestamps, name='Pack_Voltage', unit='V'),
    Signal(samples=current_data, timestamps=timestamps, name='Pack_Current', unit='A'),
    Signal(samples=temp_data, timestamps=timestamps, name='Max_Cell_Temp', unit='C'),
    Signal(samples=cell1_data, timestamps=timestamps, name='Cell_1_Voltage', unit='V'),
    Signal(samples=cell2_data, timestamps=timestamps, name='Cell_2_Voltage', unit='V'),
    Signal(samples=cell3_data, timestamps=timestamps, name='Cell_3_Voltage', unit='V')
]

# 4. Save to Binary
mdf = MDF()
mdf.append(signals)

output_filename = 'bms_telemetry.mf4'
mdf.save(output_filename, overwrite=True)

print(f"Success! Created '{output_filename}' in {time.time() - start_time:.2f} seconds.")
print("File size will be drastically smaller than the equivalent .asc file.")