import nifgen

print("Self calibrating fgen...")
with nifgen.Session("PXI1Slot5") as fgen:
    fgen.self_cal()

