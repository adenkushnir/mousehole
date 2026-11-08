# reading the injected bits off the hook flags, the recorder's injected columns depend on it
from mousehole.hook import decode_flags

# a real mouse sets neither bit
def test_real_mouse():
    assert decode_flags(0) == (False, False)

# software input sets the injected bit
def test_injected():
    assert decode_flags(0x01) == (True, False)

# windows sets both bits when a lower integrity process injects
def test_lower_il_injected():
    assert decode_flags(0x03) == (True, True)
    assert decode_flags(0x02) == (False, True)

# other bits don't matter
def test_other_bits_ignored():
    assert decode_flags(0x10) == (False, False)
    assert decode_flags(0x11) == (True, False)
