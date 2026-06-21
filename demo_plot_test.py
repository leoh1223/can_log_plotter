from pathlib import Path
import sys
sys.path.append(str(Path('.').resolve()))
import decode_and_plot as dap
import plotly.express as px

# Decode ASC with DBC and prepare dataframe
df = dap.decode_asc_with_dbc('bms_long_drive.asc', 'bms.dbc')
df = dap.prepare_dataframe(df)

signals = [c for c in df.columns if c != 'timestamp']
print('Available signals:', signals)

# Demo 1: initial selection
sel1 = []
if 'State_of_Charge' in signals:
    sel1.append('State_of_Charge')
if 'Pack_Voltage' in signals:
    sel1.append('Pack_Voltage')
if not sel1 and signals:
    sel1 = signals[:2]

fig = px.line(df, x='timestamp', y=sel1, title='Demo: Initial selection')
fig.write_html('demo_plot1.html')
print('Wrote demo_plot1.html with', sel1)

# Demo 2: add a signal (Cell_1_Voltage) if present
sel2 = sel1.copy()
if 'Cell_1_Voltage' in signals and 'Cell_1_Voltage' not in sel2:
    sel2.append('Cell_1_Voltage')

fig2 = px.line(df, x='timestamp', y=sel2, title='Demo: After add')
fig2.write_html('demo_plot2.html')
print('Wrote demo_plot2.html with', sel2)
