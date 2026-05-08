import numpy as np

import nifgen
import niscope
import nitclk

from plot import Plotter
from profiling import Profiler

import argparse
import time

parser = argparse.ArgumentParser()
parser.add_argument("--scope-name")
parser.add_argument("--fgen-name")
parser.add_argument("--mode")
parser.add_argument("--profile", action="store_true")
args = parser.parse_args()

if args.scope_name:
    scope_name = args.scope_name
else:
    scope_name = "PXI1Slot7"

if args.fgen_name:
    fgen_name = args.fgen_name
else:
    fgen_name = "PXI1Slot5"

if args.mode:
    demo_mode = args.mode
else:
    demo_mode = "immediate"

min_num_samples = 100_000
num_channels = 2
num_records = 2
min_sample_rate = 1_100_000
trigger_delay = 6.5e-7
route_arm_trig = False
use_tclk = False

fgen_channels = 2
fgen_sample_rate = 200_000_000
fgen_wait_sample_count = int(0.005 * fgen_sample_rate) # 5 ms

if demo_mode == "immediate":
    min_sample_rate = 125_000
elif demo_mode == "sw_trig":
    min_sample_rate = 1_250_000
elif demo_mode == "routing":
    min_sample_rate = 250_000_000
    route_arm_trig = True
elif demo_mode == "nitclk":
    min_sample_rate = 250_000_000
    use_tclk = True

# Wfm 0
# Ch 0 Charging curve
# Ch 1 DC low level
arb_wfm0_ch0 = 0.5 * (1.0 - np.exp(-0.001 * np.linspace(0, 10000, 10000, endpoint=False)))
arb_wfm0_ch1 = np.full(10000, -1.0)

# Wfm 1
# Ch 0 Sine
# Ch 1 DC mid level
arb_wfm1_ch0 = 0.5 + 0.5 * np.sin(np.linspace(0, 2.0 * np.pi, 100))
arb_wfm1_ch1 = np.full(100, 0.0)

# Wfm 2
# Ch 0 DC mid level
# Ch 1 DC low level
arb_wfm2_ch0 = np.full(10000, 0.5)
arb_wfm2_ch1 = np.full(10000, -1.0)

# Wfm 3
# Ch 0 Discharge curve
# Ch 1 DC low level
arb_wfm3_ch0 = 0.5 * np.exp(-0.001 * np.linspace(0, 10000, 10000, endpoint=False))
arb_wfm3_ch1 = np.full(10000, -1.0)

arb_wfm0 = np.vstack((arb_wfm0_ch0, arb_wfm0_ch1)).T.flatten()
arb_wfm1 = np.vstack((arb_wfm1_ch0, arb_wfm1_ch1)).T.flatten()
arb_wfm2 = np.vstack((arb_wfm2_ch0, arb_wfm2_ch1)).T.flatten()
arb_wfm3 = np.vstack((arb_wfm3_ch0, arb_wfm3_ch1)).T.flatten()


with niscope.Session(scope_name) as scope, nifgen.Session(fgen_name) as fgen:
    scope.channels[:num_channels].configure_vertical(range=1.0, coupling=niscope.VerticalCoupling.DC)
    scope.allow_more_records_than_memory = True
    scope.configure_horizontal_timing(
        min_sample_rate=min_sample_rate,
        min_num_pts=min_num_samples,
        ref_position=50.0,
        num_records=2**31 - 1,
        enforce_realtime=True,
    )
    scope.configure_chan_characteristics(
        input_impedance=1_000_000,
        max_input_frequency=-1,
    )
    scope.acq_arm_source = "VAL_SW_TRIG_FUNC"
    scope.trigger_delay_time = trigger_delay

    scope.trigger_type = niscope.TriggerType.DIGITAL
    scope.trigger_source = f"/{fgen_name}/0/Marker0Event"
    
    fgen.output_mode = nifgen.OutputMode.SCRIPT
    fgen.load_impedance = 1_000_000
    fgen.arb_sample_rate = fgen_sample_rate
    fgen.channels[0].arb_gain = 0.5
    fgen.channels[1].arb_gain = 0.5
    fgen.idle_behavior = nifgen.IdleBehavior.JUMP_TO
    fgen.idle_value = 0
    fgen.script_triggers[0].script_trigger_type = nifgen.ScriptTriggerType.DIGITAL_EDGE
    fgen.script_triggers[0].digital_edge_script_trigger_source = scope.ready_for_ref_event_terminal_name


    fgen.allocate_named_waveform("Wfm0", 10000)
    fgen.allocate_named_waveform("Wfm1", 100)
    fgen.allocate_named_waveform("Wfm2", 10000)
    fgen.allocate_named_waveform("Wfm3", 10000)
    fgen.write_waveform("Wfm0", arb_wfm0)
    fgen.write_waveform("Wfm1", arb_wfm1)
    fgen.write_waveform("Wfm2", arb_wfm2)
    fgen.write_waveform("Wfm3", arb_wfm3)
    fgen.write_script(f"""
        script Script0
            repeat forever
                wait until scriptTrigger0
                generate Wfm0 
                repeat 200
                    generate Wfm1
                end repeat
                generate Wfm1 marker0(0)
                repeat 199
                    generate Wfm1
                end repeat
                generate Wfm2 
                generate Wfm3
                wait {fgen_wait_sample_count}
            end repeat
        end script
    """)

    session_list = [scope, fgen]
    if use_tclk:
        nitclk.configure_for_homogeneous_triggers(session_list)
        nitclk.synchronize(session_list, 2.0e-7)
    if route_arm_trig:
        fgen.start_trigger_type = nifgen.StartTriggerType.DIGITAL_EDGE
        fgen.digital_edge_start_trigger_source = scope.start_trigger_terminal_name


    scope.commit()
    fgen.commit()

    num_samples = scope.horz_record_length
    buffer = np.zeros(num_samples * num_channels * num_records)
    data_sources = buffer.reshape((num_records * num_channels, num_samples), copy=False)

    plotter = Plotter(scope.horz_sample_rate, scope.horz_record_length)

    if args.profile:
        profiler = Profiler()

    record_number = 0
    with scope.initiate(), fgen.initiate():
        scope.send_software_trigger_edge(niscope.WhichTrigger.START)
        while plotter.is_open():
            if args.profile:
                profiler.tick()

            scope.channels[:num_channels].fetch_into(buffer, record_number=record_number, num_records=num_records, timeout=1.0)
            plotter.update_plot(data_sources)
            record_number += num_records

