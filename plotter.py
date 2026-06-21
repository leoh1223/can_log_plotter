import pandas as pd
import plotly.express as px
import numpy as np

print("Vibe check: Libraries loaded successfully!")

def main():
    # 1. Generate some mock CAN data (simulating motor controller telemetry)
    time_sec = np.linspace(0, 5, 500) # 5 seconds of high-speed data
    phase_current = np.sin(time_sec * 2 * np.pi) * 50  # 50A sine wave
    bus_voltage = np.random.normal(48.0, 0.5, 500)     # 48V bus with some noise

    df = pd.DataFrame({
        'Time (s)': time_sec,
        'Phase_Current (A)': phase_current,
        'Bus_Voltage (V)': bus_voltage
    })

    print(f"Generated {len(df)} simulated CAN frames. Launching plot...")

    # 2. We use 'melt' to transform the data into "long-form" which is more robust
    # across different Plotly versions and provides better automatic labeling.
    df_melted = df.melt(id_vars=['Time (s)'], var_name='Telemetry Type', value_name='Value')

    fig = px.line(df_melted, x='Time (s)', y='Value', color='Telemetry Type',
                  title='Simulated Telemetry: Motor Controller Phase & Bus')
    
    # Explicitly using a renderer can help if the plot doesn't appear in some IDEs
    fig.show()

if __name__ == "__main__":
    main()