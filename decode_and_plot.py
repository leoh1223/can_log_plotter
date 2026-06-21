import sys
from argparse import ArgumentParser
from pathlib import Path

import cantools
import pandas as pd
import plotly.express as px
import tkinter as tk
from asammdf import MDF
from tkinter import filedialog


TIMESTAMP_COLUMN = 'timestamp'
SUPPORTED_LOG_TYPES = ('.mf4', '.asc')


def parse_asc_log(file_path):
    rows = []
    with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
        for raw_line in f:
            line = raw_line.strip()
            if not line or line.startswith(('date', 'base', 'internal')):
                continue

            parts = line.split()
            if 'Rx' in parts:
                event_index = parts.index('Rx')
            elif 'Tx' in parts:
                event_index = parts.index('Tx')
            else:
                continue

            if event_index < 2:
                continue

            try:
                timestamp = float(parts[0])
                arbitration_id = int(parts[event_index - 1], 16)
                dlc_index = event_index + 2
                dlc = int(parts[dlc_index])
                data_start = dlc_index + 1
                data_parts = parts[data_start:data_start + dlc]
                if len(data_parts) != dlc:
                    continue
                data_bytes = bytes(int(byte, 16) for byte in data_parts)
            except (ValueError, IndexError):
                continue

            rows.append((timestamp, arbitration_id, data_bytes))

    return rows


def decode_asc_with_dbc(asc_path, dbc_path):
    db = cantools.database.load_file(dbc_path)
    decoded_rows = []

    for timestamp, arb_id, data_bytes in parse_asc_log(asc_path):
        try:
            db.get_message_by_frame_id(arb_id)
        except KeyError:
            continue

        try:
            decoded_values = db.decode_message(arb_id, data_bytes, decode_choices=False)
        except Exception:
            continue

        if not decoded_values:
            continue

        row = {TIMESTAMP_COLUMN: timestamp}
        row.update(decoded_values)
        decoded_rows.append(row)

    df = pd.DataFrame(decoded_rows)
    if df.empty:
        raise ValueError('No decodable ASC rows found for the selected DBC.')

    # If the same timestamp appears in multiple decoded messages, combine them
    # so each timestamp row contains the first non-null signal values.
    df = df.groupby(TIMESTAMP_COLUMN, as_index=False).first()
    return df.sort_values(TIMESTAMP_COLUMN)


def prepare_dataframe(df):
    df = df.copy()

    # Normalize likely time/index columns to a single timestamp column name.
    for column_name in ('time', 'timestamps', 'Time', 'Time (s)'):
        if column_name in df.columns and TIMESTAMP_COLUMN not in df.columns:
            df = df.rename(columns={column_name: TIMESTAMP_COLUMN})

    if TIMESTAMP_COLUMN not in df.columns:
        index_name = df.index.name
        if index_name is None:
            df = df.reset_index(drop=False)
            if 'index' in df.columns:
                df = df.rename(columns={'index': TIMESTAMP_COLUMN})
        else:
            df = df.reset_index()
            if index_name in df.columns:
                df = df.rename(columns={index_name: TIMESTAMP_COLUMN})

    if TIMESTAMP_COLUMN in df.columns:
        df = df.sort_values(TIMESTAMP_COLUMN)

    return df


def signal_columns(df):
    return [col for col in df.columns if col != TIMESTAMP_COLUMN]


def dedupe_preserve_order(values):
    seen = set()
    unique = []
    for value in values:
        if value not in seen:
            seen.add(value)
            unique.append(value)
    return unique


def resolve_signal_selection(selection, available_signals):
    if not selection:
        return []

    if isinstance(selection, str):
        parts = [part.strip() for part in selection.split(',') if part.strip()]
    else:
        parts = [str(part).strip() for part in selection if str(part).strip()]

    if len(parts) == 1 and parts[0].upper() in ('ALL', '0'):
        return available_signals.copy()

    selected = []
    valid_names = set(available_signals)
    for part in parts:
        if part.isdigit():
            index = int(part)
            if 1 <= index <= len(available_signals):
                selected.append(available_signals[index - 1])
            else:
                raise ValueError(f'Index out of range: {part}')
        elif part in valid_names:
            selected.append(part)
        else:
            raise ValueError(f'Unknown signal: {part}')

    return dedupe_preserve_order(selected)


def choose_signal(df):
    available_signals = signal_columns(df)
    if not available_signals:
        sys.exit('No plot signals available.')

    print('\nSelect one or more signals to plot:')
    for index, name in enumerate(available_signals, start=1):
        print(f'  {index:>3}: {name}')
    print('  0: ALL')

    while True:
        choice = input("\nEnter signal number(s), exact name(s), or 'ALL' (comma-separated): ").strip()
        try:
            selected = resolve_signal_selection(choice, available_signals)
        except ValueError as exc:
            print(exc)
            print('Please enter valid signal numbers or names.')
            continue

        if selected:
            return selected


def select_file(title, filetypes):
    root = tk.Tk()
    root.withdraw()
    root.call('wm', 'attributes', '.', '-topmost', True)
    try:
        return filedialog.askopenfilename(title=title, filetypes=filetypes)
    finally:
        root.destroy()


def choose_paths(args):
    dbc_file = args.dbc or select_file(
        title='Select Network Database (.dbc)',
        filetypes=[('DBC Files', '*.dbc')],
    )
    if not dbc_file:
        sys.exit('No DBC selected.')

    log_file = args.log or select_file(
        title='Select CAN log file',
        filetypes=[
            ('All Supported Logs', '*.mf4;*.asc'),
            ('ASAM MDF4 Logs', '*.mf4'),
            ('Vector ASC Logs', '*.asc'),
        ],
    )
    if not log_file:
        sys.exit('No log selected.')

    return Path(dbc_file), Path(log_file)


def load_mf4_dataframe(log_file, dbc_file):
    mdf = MDF(log_file)
    try:
        try:
            decoded_mdf = mdf.extract_bus_logging(database_files={'CAN': [(str(dbc_file), 0)]})
            print('Converting decoded data to Pandas DataFrame...')
            df = decoded_mdf.to_dataframe()
        except Exception as exc:
            print(f'Warning: DBC decode failed ({exc}). Falling back to raw MDF channels.')
            df = mdf.to_dataframe()

        if df.empty or list(df.columns) == [TIMESTAMP_COLUMN]:
            print('Warning: decoded MDF produced no signal columns, falling back to raw MDF channels.')
            df = mdf.to_dataframe()

        return df
    finally:
        mdf.close()


def load_log_dataframe(log_file, dbc_file):
    log_ext = log_file.suffix.lower()
    if log_ext == '.mf4':
        print(f'\nLoading and decoding binary log: {log_file.name}...')
        return load_mf4_dataframe(log_file, dbc_file)
    if log_ext == '.asc':
        print(f'\nLoading and decoding ASC log: {log_file.name}...')
        return decode_asc_with_dbc(log_file, dbc_file)
    raise ValueError(f'Unsupported log format: {log_ext}')


def clean_dataframe(df):
    df = prepare_dataframe(df)
    df = df.dropna(axis=1, how='all')
    if TIMESTAMP_COLUMN not in df.columns:
        raise ValueError('Could not find or create a timestamp column.')
    if not signal_columns(df):
        raise ValueError('No signal columns available after decoding.')
    return df


def plot_signals(df, signals):
    title = f"Selected Signals: {', '.join(signals)}"
    fig = px.line(df, x=TIMESTAMP_COLUMN, y=signals, title=title)
    fig.update_layout(xaxis_title='Timestamp', yaxis_title='Value')
    fig.show()


def print_available_signals(df):
    print('\n--- Available Signals in Log ---')
    for col in df.columns:
        print(f'- {col}')
    print('--------------------------------')


def parse_args():
    parser = ArgumentParser(description='Decode CAN logs with a DBC and plot selected signals.')
    parser.add_argument('--dbc', help='Path to a .dbc network database file.')
    parser.add_argument('--log', help='Path to a .mf4 or .asc CAN log file.')
    parser.add_argument(
        '--signals',
        help="Initial signals to plot, as comma-separated numbers/names, or 'ALL'.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    print('Initializing CAN Plotter...')

    dbc_file, log_file = choose_paths(args)
    log_ext = log_file.suffix.lower()
    if log_ext not in SUPPORTED_LOG_TYPES:
        sys.exit(f'Unsupported log format: {log_ext}')

    print('Preparing decoded data...')
    df = clean_dataframe(load_log_dataframe(log_file, dbc_file))
    print_available_signals(df)

    available_signals = signal_columns(df)
    if args.signals:
        try:
            selected_signals = resolve_signal_selection(args.signals, available_signals)
        except ValueError as exc:
            sys.exit(str(exc))
    else:
        selected_signals = choose_signal(df)
    if not selected_signals:
        sys.exit('No signal selected to plot.')

    plot_signals(df, selected_signals)

    print('\nInteractive mode: modify plotted signals live.')
    print("Commands: add <n|name>[,n...], remove <n|name>[,n...], set <list>, list, all, none, reload, quit")

    while True:
        cmd = input('\n> ').strip()
        if not cmd:
            continue
        parts = cmd.split(None, 1)
        op = parts[0].lower()

        if op in ('quit', 'q', 'exit'):
            print('Exiting interactive plotter.')
            break

        if op == 'list':
            print('Available signals:')
            for i, signal in enumerate(available_signals, start=1):
                mark = '*' if signal in selected_signals else ' '
                print(f'{i:3} {mark} {signal}')
            print('Currently plotted:', ', '.join(selected_signals) or '(none)')
            continue

        if op == 'all':
            selected_signals = available_signals.copy()
            plot_signals(df, selected_signals)
            continue

        if op == 'none':
            selected_signals = []
            print('No signals selected.')
            continue

        if op == 'reload':
            print('Reloading data...')
            df = clean_dataframe(load_log_dataframe(log_file, dbc_file))
            available_signals = signal_columns(df)
            selected_signals = [signal for signal in selected_signals if signal in available_signals]
            print('Reload complete.')
            if selected_signals:
                plot_signals(df, selected_signals)
            continue

        args_text = parts[1] if len(parts) > 1 else ''
        if op in ('add', 'remove', 'set') and args_text:
            try:
                resolved = resolve_signal_selection(args_text, available_signals)
            except ValueError as exc:
                print(exc)
                print('No valid signals in request.')
                continue

            if op == 'add':
                for signal in resolved:
                    if signal not in selected_signals:
                        selected_signals.append(signal)
                print('Added:', ', '.join(resolved))
                plot_signals(df, selected_signals)
                continue

            if op == 'remove':
                for signal in resolved:
                    if signal in selected_signals:
                        selected_signals.remove(signal)
                print('Removed:', ', '.join(resolved))
                if selected_signals:
                    plot_signals(df, selected_signals)
                else:
                    print('No signals selected to plot.')
                continue

            if op == 'set':
                selected_signals = resolved
                print('Set selection to:', ', '.join(selected_signals))
                plot_signals(df, selected_signals)
                continue

        print('Unknown command or missing arguments. Use: add/remove/set/list/all/none/reload/quit')


if __name__ == '__main__':
    main()
