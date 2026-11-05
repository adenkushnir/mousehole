# Checks we read the injected bits off the hook flags right, everything in milestone 2 leans on this.
from mousehole.hook import decode_flags

def test_real_mouse():
    assert decode_flags(0) == (False, False)

def test_injected():
    assert decode_flags(0x01) == (True, False)

def test_lower_il_injected():
    # windows sets both bits when a lower integrity process injects
    assert decode_flags(0x03) == (True, True)
    assert decode_flags(0x02) == (False, True)

def test_other_bits_ignored():
    assert decode_flags(0x10) == (False, False)
    assert decode_flags(0x11) == (True, False)
