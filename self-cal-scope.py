import niscope

print("Self calibrating scope...")
with niscope.Session("PXI1Slot7") as scope:
    scope.self_cal()

