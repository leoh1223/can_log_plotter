import math
import struct
import time

print("Initializing High-Density BMS Telemetry Generator...")

# ==========================================
# 1. Create the BMS Network Database
# ==========================================
dbc_content = """VERSION ""
BS_:
BU_: 
BO_ 500 BMS_Status: 8 Vector__XXX
 SG_ State_of_Charge : 0|8@1+ (0.5,0) [0|100] "%" Vector__XXX
 SG_ Pack_Voltage : 8|16@1+ (0.1,0) [0|500] "V" Vector__XXX
 SG_ Pack_Current : 24|16@1- (0.1,0) [-500|500] "A" Vector__XXX
 SG_ Max_Cell_Temp : 40|8@1+ (1,-40) [-40|100] "C" Vector__XXX

BO_ 501 Cell_Voltages: 6 Vector__XXX
 SG_ Cell_1_Voltage : 0|16@1+ (0.001,0) [0|5] "V" Vector__XXX
 SG_ Cell_2_Voltage : 16|16@1+ (0.001,0) [0|5] "V" Vector__XXX
 SG_ Cell_3_Voltage : 32|16@1+ (0.001,0) [0|5] "V" Vector__XXX
"""

with open("bms.dbc", "w") as f:
    f.write(dbc_content)

# ==========================================
# 2. Generate the 30-Minute ASC Log
# ==========================================
# 30 minutes at 100Hz = 180,000 ticks. 
# We generate 2 messages per tick, totaling 360,000 CAN frames.
total_minutes = 30
fps = 100 
total_ticks = total_minutes * 60 * fps

print(f"Generating a {total_minutes}-minute drive ({total_ticks * 2} frames). This will take a few seconds...")

with open("bms_long_drive.asc", "w") as f:
    f.write("date Wed May 20 08:00:00 AM 2026\n")
    f.write("base hex  timestamps absolute\n")
    f.write("internal events logged\n")
    
    start_time = time.time()
    
    for i in range(total_ticks):
        t = i / fps
        
        # --- Simulate EV Physics ---
        # SoC drops linearly from 100% to 20%
        soc = 100.0 - (80.0 * (i / total_ticks))
        
        # Current spikes every 10 seconds (acceleration) and goes negative (regen braking)
        current = math.sin(t * (2 * math.pi / 10)) * 150.0 
        
        # Pack Voltage sags heavily when current draw is high
        pack_voltage = 400.0 - (current * 0.05)
        
        # Temperature rises slowly over the 30-minute drive from 25C to 45C
        temp = 25.0 + (20.0 * (i / total_ticks))
        
        # --- Pack Message 1: BMS Status (ID: 0x1F4 / 500) ---
        raw_soc = int(max(0, soc) / 0.5)
        raw_volt = int(pack_voltage / 0.1)
        raw_curr = int(current / 0.1)
        raw_temp = int((temp - (-40)) / 1)
        
        # Format: Unsigned 8-bit, Unsigned 16-bit, Signed 16-bit, Unsigned 8-bit, Padding
        payload_1 = struct.pack('<B H h B H', raw_soc, raw_volt, raw_curr, raw_temp, 0)
        hex_1 = " ".join([f"{b:02X}" for b in payload_1[:8]])
        f.write(f"   {t:.6f} 1  1F4             Rx   d 8 {hex_1}\n")
        
        # --- Pack Message 2: Cell Voltages (ID: 0x1F5 / 501) ---
        # Cells hover around the pack voltage average, with slight noise variations
        base_cell = pack_voltage / 96.0
        c1 = base_cell + (math.sin(t * 5) * 0.01)
        c2 = base_cell + (math.cos(t * 3) * 0.01)
        c3 = base_cell - (math.sin(t * 2) * 0.01)
        
        payload_2 = struct.pack('<H H H', int(c1/0.001), int(c2/0.001), int(c3/0.001))
        hex_2 = " ".join([f"{b:02X}" for b in payload_2])
        f.write(f"   {t:.6f} 1  1F5             Rx   d 6 {hex_2}\n")
        
        # Print a progress update to the terminal every 50,000 ticks
        if i % 50000 == 0 and i > 0:
            print(f"  -> Generated {i}/{total_ticks} frames...")

print(f"Success! Generated {total_ticks * 2} frames in {time.time()-start_time:.1f} seconds.")
print("Files ready: 'bms.dbc' and 'bms_long_drive.asc'")