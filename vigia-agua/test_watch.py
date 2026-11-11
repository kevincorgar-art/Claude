from watch import in_window

assert in_window(23, 22, 6) and in_window(3, 22, 6)  # ventana que cruza medianoche
assert not in_window(12, 22, 6) and not in_window(6, 22, 6)
assert in_window(9, 8, 17) and not in_window(17, 8, 17)  # ventana normal
print("ok")
