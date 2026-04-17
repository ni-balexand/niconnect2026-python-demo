import numpy as np

import nifgen
import niscope
import nitclk

from plot import Plotter
from profiling import Profiler

import argparse

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

min_num_samples = 80
num_channels = 2
num_records = 4
min_sample_rate = 250_000_000
sw_trig = False
routing_trig = False
use_tclk = False

if demo_mode == "immediate":
    min_sample_rate = 125_000
elif demo_mode == "sw_trig":
    min_sample_rate = 1_250_000
    sw_trig = True
elif demo_mode == "routing":
    min_sample_rate = 250_000_000
    routing_trig = True
elif demo_mode == "nitclk":
    min_sample_rate = 250_000_000
    use_tclk = True


with niscope.Session(scope_name) as scope, nifgen.Session(fgen_name) as fgen:
    scope.channels[:num_channels].configure_vertical(range=1.0, coupling=niscope.VerticalCoupling.DC)
    # scope.allow_more_records_than_memory = True
    scope.configure_horizontal_timing(
        min_sample_rate=min_sample_rate,
        min_num_pts=min_num_samples,
        ref_position=0.0,
        num_records=num_records,
        enforce_realtime=True,
    )
    scope.configure_chan_characteristics(
        input_impedance=1_000_000,
        max_input_frequency=-1,
    )

    if sw_trig:
        scope.acq_arm_source = "VAL_SW_TRIG_FUNC"
    elif routing_trig:
        scope.acq_arm_source = f"/{fgen_name}/0/StartedEvent"
    
    fgen.output_mode = nifgen.OutputMode.FUNC
    fgen.load_impedance = 1_000_000
    fgen.channels[0].func_waveform = nifgen.Waveform.SINE
    fgen.channels[0].func_amplitude = 1.0
    fgen.channels[0].func_frequency = 100_000
    fgen.channels[1].func_waveform = nifgen.Waveform.SQUARE
    fgen.channels[1].func_amplitude = 1.0
    fgen.channels[1].func_frequency = 10_000
    fgen.channels[1].func_start_phase = -0.2 # Delay the edge slightly
    fgen.start_trigger_type = nifgen.StartTriggerType.SOFTWARE_EDGE

    scope.commit()
    fgen.commit()

    session_list = [scope, fgen]
    if use_tclk:
        nitclk.configure_for_homogeneous_triggers(session_list)
        nitclk.synchronize(session_list, 2.0e-7)

    num_samples = scope.horz_record_length
    buffer = np.zeros(num_samples * num_channels * num_records)
    data_sources = buffer.reshape((num_records * num_channels, num_samples), copy=False)

    plotter = Plotter(scope.horz_sample_rate, scope.horz_record_length)

    if args.profile:
        profiler = Profiler()

    while plotter.is_open():
        if args.profile:
            profiler.tick()

        if use_tclk:
            nitclk.initiate(session_list)
            fgen.send_software_edge_trigger(nifgen.Trigger.START)
            scope.channels[:num_channels].fetch_into(buffer, record_number=0, num_records=num_records)
            fgen.abort()
            scope.abort()
        else:
            with scope.initiate(), fgen.initiate():
                # Uncomment for variation in the FGEN output
                # fgen.channels[0].digital_gain = abs(frame % 30 - 15) / 15.0

                if sw_trig:
                    scope.send_software_trigger_edge(niscope.WhichTrigger.START)
 
                fgen.send_software_edge_trigger(nifgen.Trigger.START)
                scope.channels[:num_channels].fetch_into(buffer, record_number=0, num_records=num_records)

        plotter.update_plot(data_sources)

