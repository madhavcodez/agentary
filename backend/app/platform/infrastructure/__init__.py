"""Infrastructure adapters — SDK access, scheduling, and persistence shims.

Domain services depend on these via the provider protocols, never on
the SDKs directly. This keeps provider swaps surgical and makes mocking
trivial in tests.
"""
