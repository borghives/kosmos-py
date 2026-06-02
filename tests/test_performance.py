import timeit
import pytest
from tests.performance_test_model import PerformanceTestModel

def test_benchmark(capsys):
    # Time the legacy method
    legacy_time = timeit.timeit(
        "detector=km.detect(PerformanceTestModel)\ndf=detector._load_dataframe_legacy()\ndf.groupby('name').value.mean()",
        setup="from tests.performance_test_model import PerformanceTestModel\nimport kosmos as km\nkm.ignite(\"test.env\")",
        number=10
    )

    # Time the new Arrow-based method
    arrow_time = timeit.timeit(
        "detector=km.detect(PerformanceTestModel)\ndf=detector.load_dataframe()\ndf.groupby('name').value.mean()",
        setup="from tests.performance_test_model import PerformanceTestModel\nimport kosmos as km\nkm.ignite(\"test.env\")",
        number=10
    )

    with capsys.disabled():
        print(f"\nLegacy implementation: {legacy_time:.4f} seconds")
        print(f"Arrow implementation:  {arrow_time:.4f} seconds")
        
        improvement = ((legacy_time - arrow_time) / legacy_time) * 100
        print(f"Improvement: {improvement:.2f}%")

    assert arrow_time  < legacy_time
