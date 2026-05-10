import numpy as np

import nifgen
import niscope

from plot import Plotter
from profiling import Profiler
from waveforms import DemoWaveforms

import time

scope_name = "PXI1Slot7"
fgen_name = "PXI1Slot5"

min_num_samples = 100_000
num_channels = 2
num_records = 2
min_sample_rate = 250_000_000
trigger_delay = 6.5e-7
route_arm_trig = False
use_tclk = False

fgen_channels = 2
fgen_sample_rate = 200_000_000
fgen_wait_sample_count = int(0.005 * fgen_sample_rate) # 5 ms

wfms = DemoWaveforms()

with niscope.Session(scope_name) as scope, nifgen.Session(fgen_name) as fgen:

    # Configure channels
    scope.channels[:num_channels].configure_vertical(range=1.0, coupling=niscope.VerticalCoupling.DC)
    scope.configure_chan_characteristics(
        input_impedance=1_000_000,
        max_input_frequency=-1,
    )

    # Configure timing and acquisition
    scope.allow_more_records_than_memory = True
    scope.configure_horizontal_timing(
        min_sample_rate=min_sample_rate,
        min_num_pts=min_num_samples,
        ref_position=50.0,
        num_records=2**31 - 1,
        enforce_realtime=True,
    )

    # Configure start (acq. arm) trigger as software trigger
    scope.acq_arm_source = "VAL_SW_TRIG_FUNC"

    # Configure scope reference trigger to be routed from Marker0 on the FGEN
    scope.trigger_type = niscope.TriggerType.DIGITAL
    scope.trigger_source = f"/{fgen_name}/0/Marker0Event"  # <------- String-based routing sytax
    scope.trigger_delay_time = trigger_delay

    # FGEN parameters
    fgen.output_mode = nifgen.OutputMode.SCRIPT
    fgen.load_impedance = 1_000_000
    fgen.arb_sample_rate = fgen_sample_rate
    fgen.channels[0].arb_gain = 0.5
    fgen.channels[1].arb_gain = 0.5
    fgen.idle_behavior = nifgen.IdleBehavior.JUMP_TO
    fgen.idle_value = 0

    # Configure script trigger to be routed from ready for ref event on the scope
    fgen.script_triggers[0].script_trigger_type = nifgen.ScriptTriggerType.DIGITAL_EDGE
    fgen.script_triggers[0].digital_edge_script_trigger_source = (
        scope.ready_for_ref_event_terminal_name  # <------- Terminal name attribute (string-based)
    )

    # Start the FGEN when the scope starts
    fgen.start_trigger_type = nifgen.StartTriggerType.DIGITAL_EDGE
    fgen.digital_edge_start_trigger_source = (
        scope.start_trigger_terminal_name  # <------- Terminal name attribute (string-based)
    )

    # Write 4 arbitrary waveforms to the FGEN
    fgen.allocate_named_waveform("Wfm0", 10000)
    fgen.allocate_named_waveform("Wfm1", 100)
    fgen.allocate_named_waveform("Wfm2", 10000)
    fgen.allocate_named_waveform("Wfm3", 10000)
    fgen.write_waveform("Wfm0", wfms.arb_wfm0)
    fgen.write_waveform("Wfm1", wfms.arb_wfm1)
    fgen.write_waveform("Wfm2", wfms.arb_wfm2)
    fgen.write_waveform("Wfm3", wfms.arb_wfm3)

    # Write scripted sequence
    fgen.write_script(f"""
        script Script0
            repeat forever
                wait until scriptTrigger0  // signaled by scope once it is ready
                generate Wfm0 
                repeat 200
                    generate Wfm1
                end repeat
                generate Wfm1 marker0(0)  // used for the scope reference trigger
                repeat 199
                    generate Wfm1
                end repeat
                generate Wfm2 
                generate Wfm3
                wait {fgen_wait_sample_count}  // pace setter
            end repeat
        end script
    """)

    # Program hardware with selected options
    scope.commit()
    fgen.commit()

    # Fetch buffer
    num_samples = scope.horz_record_length
    buffer = np.zeros(num_samples * num_channels * num_records)

    # Reshaped buffer for plotter (2D array)
    data_sources = buffer.reshape((num_records * num_channels, num_samples), copy=False)

    plotter = Plotter(scope.horz_sample_rate, scope.horz_record_length)

    record_number = 0
    with scope.initiate(), fgen.initiate():
        scope.send_software_trigger_edge(niscope.WhichTrigger.START)
        while plotter.is_open():
            scope.channels[:num_channels].fetch_into(buffer, record_number=record_number, num_records=num_records, timeout=1.0)
            plotter.update_plot(data_sources)
            record_number += num_records

