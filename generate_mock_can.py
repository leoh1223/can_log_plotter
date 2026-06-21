import math
import struct

print("Generating mock CAN network database and log...")

# 1. Create a minimal standard .dbc file
dbc_content = """VERSION ""
BS_:
BU_: 
BO_ 256 Motor_Status: 8 Vector__XXX
 SG_ Bus_Voltage : 0|16@1+ (0.1,0) [0|100] "V" Vector__XXX
 SG_ Phase_Current : 16|16@1- (0.1,0) [-500|500] "A" Vector__XXX
"""

with open("motor.dbc", "w") as f:
    f.write(dbc_content)

# 2. Create a Vector .asc log file
with open("motor_log.asc", "w") as f:
    # Standard Vector ASC header
    f.write("date Mon Jan 01 12:00:00 AM 2026\n")
    f.write("base hex  timestamps absolute\n")
    f.write("internal events logged\n")
    
    # Generate 5 seconds of traffic at 100Hz (10ms intervals)
    for i in range(500):
        t = i * 0.01 
        
        # Physical engineering values
        volts = 48.0 + (math.sin(t * 5) * 1.5)  # 48V with some voltage ripple
        amps = math.sin(t * 2 * math.pi) * 50   # 50A sine wave
        
        # Convert physical values to raw CAN integers based on our DBC scaling (0.1)
        raw_volts = int(volts / 0.1) 
        raw_amps = int(amps / 0.1)
        
        # Pack into 8 bytes. Little Endian '<'. 
        # 'H' = Unsigned 16-bit (Voltage), 'h' = Signed 16-bit (Current), 'I' = 32-bit zero padding
        payload = struct.pack('<Hh I', raw_volts, raw_amps, 0) 
        
        # Format payload into hex strings for the log
        hex_payload = " ".join([f"{b:02X}" for b in payload])
        
        # Write the ASC line (Message ID 100 hex = 256 decimal)
        f.write(f"   {t:.6f} 1  100             Rx   d 8 {hex_payload}\n")

print("Success! 'motor.dbc' and 'motor_log.asc' have been created in your workspace.")