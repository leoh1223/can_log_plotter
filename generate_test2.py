import math
import struct

print("Generating Test 2: Vehicle Dynamics (Steering, Speed, Brakes)...")

# ==========================================
# 1. Create a Vehicle Dynamics DBC
# ==========================================
dbc_content = """VERSION ""
BS_:
BU_: 
BO_ 200 Vehicle_Dynamics: 8 Vector__XXX
 SG_ Steering_Angle : 0|16@1- (0.1,0) [-360|360] "deg" Vector__XXX
 SG_ Vehicle_Speed : 16|8@1+ (1,0) [0|250] "km/h" Vector__XXX
 SG_ Brake_Pedal : 24|8@1+ (0.5,0) [0|100] "%" Vector__XXX
"""

with open("vehicle.dbc", "w") as f:
    f.write(dbc_content)

# ==========================================
# 2. Create the ASC Log File
# ==========================================
with open("driving_log.asc", "w") as f:
    f.write("date Tue May 16 14:00:00 PM 2026\n")
    f.write("base hex  timestamps absolute\n")
    f.write("internal events logged\n")
    
    # Generate 10 seconds of traffic at 100Hz (1000 frames)
    for i in range(1000):
        t = i * 0.01 
        
        # --- Simulate Physical Behavior ---
        # Steering: Sine wave moving left/right every 2 seconds
        steer_deg = 45.0 * math.sin(t * math.pi) 
        
        # Speed: Accelerate to 100km/h over 5 seconds, then hold, then brake at end
        if t < 5:
            speed_kmh = 20.0 * t  # Accel
            brake_pct = 0.0
        elif t < 8:
            speed_kmh = 100.0     # Coast/Hold
            brake_pct = 0.0
        else:
            speed_kmh = max(0, 100.0 - 50.0 * (t - 8)) # Heavy braking
            brake_pct = 85.0 if speed_kmh > 0 else 0.0
        
        # --- Convert to raw CAN integers based on DBC scaling ---
        raw_steer = int(steer_deg / 0.1)
        raw_speed = int(speed_kmh / 1.0)
        raw_brake = int(brake_pct / 0.5)
        
        # Pack into 8 bytes. Little Endian '<'.
        # 'h' = Signed 16-bit (Steering)
        # 'B' = Unsigned 8-bit (Speed)
        # 'B' = Unsigned 8-bit (Brake)
        # 'I' = 32-bit zero padding for the remaining 4 bytes
        payload = struct.pack('<h B B I', raw_steer, raw_speed, raw_brake, 0) 
        
        # Format into hex strings
        hex_payload = " ".join([f"{b:02X}" for b in payload])
        
        # Write the ASC line (Message ID 0xC8 hex = 200 decimal)
        f.write(f"   {t:.6f} 1  C8              Rx   d 8 {hex_payload}\n")

print("Success! 'vehicle.dbc' and 'driving_log.asc' have been generated.")