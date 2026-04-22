from src.data_client.tushare.data_source import TuShareDataSource


class TestTuShareSymbolNormalization:
    def test_ss_suffix_normalizes_to_sh(self):
        assert TuShareDataSource._to_ts_code("512760.SS") == "512760.SH"

    def test_sh_suffix_remains_sh(self):
        assert TuShareDataSource._to_ts_code("512760.SH") == "512760.SH"

    def test_sz_suffix_remains_sz(self):
        assert TuShareDataSource._to_ts_code("159919.SZ") == "159919.SZ"
