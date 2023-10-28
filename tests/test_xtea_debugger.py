import utils.extraction.network.debugger as debugger


class TestDebugger:
    def setup_method(self):
        self.debugger = debugger.XteaDebugger(-1)

    def test_FindBreakpointAddress_FindsAddress(self):
        # Act
        self.debugger.find_breakpoint_address()

        # Assert
        assert self.debugger.breakpoint_address
