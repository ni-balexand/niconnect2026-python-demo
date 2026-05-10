import numpy as np

class DemoWaveforms():
    def __init__(self):
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

        self.arb_wfm0 = np.vstack((arb_wfm0_ch0, arb_wfm0_ch1)).T.flatten()
        self.arb_wfm1 = np.vstack((arb_wfm1_ch0, arb_wfm1_ch1)).T.flatten()
        self.arb_wfm2 = np.vstack((arb_wfm2_ch0, arb_wfm2_ch1)).T.flatten()
        self.arb_wfm3 = np.vstack((arb_wfm3_ch0, arb_wfm3_ch1)).T.flatten()
