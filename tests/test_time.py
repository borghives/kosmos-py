import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
import polars as pl
import arrow

import kosmos.time as kt

def test_timezone_helpers():
    # Test naive datetime conversions
    naive = datetime(2025, 6, 1, 12, 0, 0)
    
    # to_utc_aware assumes naive is UTC and adds timezone
    utc_aware = kt.to_utc_aware(naive)
    assert utc_aware.tzinfo == timezone.utc
    assert utc_aware.hour == 12

    # to_offset_aware converts to target offset timezone
    # offset 3600 (1 hour east)
    offset_aware = kt.to_offset_aware(naive, 3600)
    assert offset_aware.tzinfo is not None
    assert offset_aware.utcoffset() == timedelta(hours=1)

    # to_eastern_aware converts assumed UTC naive datetime to America/New_York
    eastern_aware = kt.to_eastern_aware(naive)
    # 2025-06-01 is during daylight savings time (EDT = UTC-4)
    assert eastern_aware.tzinfo == ZoneInfo("America/New_York")
    assert eastern_aware.hour == 8  # 12 - 4

    # to_est_aware converts naive to EST (fixed UTC-5)
    est_aware = kt.to_est_aware(naive)
    assert est_aware.tzinfo is not None
    assert est_aware.utcoffset() == timedelta(hours=-5)
    assert est_aware.hour == 7  # 12 - 5

def test_current_time_helpers():
    now_utc = kt.get_current_time()
    assert now_utc.tzinfo == timezone.utc
    
    now_eastern = kt.get_current_event_time()
    assert now_eastern.tzinfo == ZoneInfo("America/New_York")

def test_pl_col_utc():
    expr = kt.pl_col_utc("timestamp")
    assert isinstance(expr, pl.Expr)

def test_timeframe_resolutions():
    tzone = timezone.utc
    
    # Test resolutions map to the correct TimeFrame classes
    hour_frame = kt.TimeFrameResolution.hourly.current(tzone)
    assert isinstance(hour_frame, kt.HourlyFrame)
    
    day_frame = kt.TimeFrameResolution.daily.current(tzone)
    assert isinstance(day_frame, kt.DailyFrame)
    
    week_frame = kt.TimeFrameResolution.weekly.current(tzone)
    assert isinstance(week_frame, kt.WeeklyFrame)

    month_frame = kt.TimeFrameResolution.monthly.current(tzone)
    assert isinstance(month_frame, kt.MonthlyFrame)

    quarter_frame = kt.TimeFrameResolution.quarterly.current(tzone)
    assert isinstance(quarter_frame, kt.QuarterlyFrame)

    year_frame = kt.TimeFrameResolution.yearly.current(tzone)
    assert isinstance(year_frame, kt.YearlyFrame)

    # Test from_name
    assert kt.TimeFrameResolution.from_name("hourly") == kt.TimeFrameResolution.hourly
    assert kt.TimeFrameResolution.from_name("invalid", kt.TimeFrameResolution.daily) == kt.TimeFrameResolution.daily
    assert kt.TimeFrameResolution.from_name("invalid") == kt.TimeFrameResolution.none

    # Test from_type
    assert kt.TimeFrameResolution.from_type(kt.DailyFrame) == kt.TimeFrameResolution.daily

def test_timeframe_bounds_and_navigation():
    moment = datetime(2025, 6, 15, 12, 30, 45, tzinfo=timezone.utc)
    
    # Hourly frame
    h_frame = kt.HourlyFrame.create(moment=moment, tzone=timezone.utc)
    assert h_frame.floor == datetime(2025, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
    assert h_frame.ceiling == datetime(2025, 6, 15, 13, 0, 0, tzinfo=timezone.utc)
    
    next_h = h_frame.get_next_frame()
    assert next_h.floor == h_frame.ceiling
    
    prev_h = h_frame.get_previous_frame()
    assert prev_h.ceiling == h_frame.floor

    # Daily frame
    d_frame = kt.DailyFrame.create(moment=moment, tzone=timezone.utc)
    assert d_frame.floor == datetime(2025, 6, 15, 0, 0, 0, tzinfo=timezone.utc)
    assert d_frame.ceiling == datetime(2025, 6, 16, 0, 0, 0, tzinfo=timezone.utc)

    # get_previous_x_frame
    prev_2d = d_frame.get_previous_x_frame(2)
    assert prev_2d.floor == datetime(2025, 6, 13, 0, 0, 0, tzinfo=timezone.utc)

    # elapsed, is_in_frame
    # since moment is in the past, has_passed should be true relative to current time
    assert h_frame.has_passed() is True
    assert h_frame.elapsed() == 1.0

def test_align_and_fit_timeframe():
    floor = datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    ceiling = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    
    # Should align to YearlyFrame
    frame = kt.align_to_human_timeframe(floor, ceiling)
    assert isinstance(frame, kt.YearlyFrame)

    # fit_timeframe
    generic_frame = kt.TimeFrame(floor=floor, ceiling=ceiling)
    fitted = kt.fit_timeframe(generic_frame)
    assert isinstance(fitted, kt.YearlyFrame)

def test_perf_timer_context():
    with kt.PerfTimer("test-timer") as timer:
        assert timer.name == "test-timer"
        assert timer._start_time is not None
    
    assert timer._start_time is None
    assert timer.count == 1
    assert timer.total_time > 0
    assert "test-timer" in str(timer)
    
    d = timer.to_dict()
    assert d["name"] == "test-timer"
    assert d["count"] == 1

def test_perf_timer_subtimer():
    timer = kt.PerfTimer("parent")
    with timer:
        with kt.sub_timed(timer, "child"):
            pass
            
    assert "child" in timer.child_timers
    assert timer.child_timers["child"].count == 1
    assert "parent" in str(timer)
    assert "child" in str(timer)

def test_timed_decorator_sync():
    timer_data = None
    
    @kt.timed(name="custom_sync_func")
    def my_func(ptimer=None):
        nonlocal timer_data
        timer_data = ptimer

    parent = kt.PerfTimer("parent")
    my_func(ptimer=parent)
    
    assert timer_data is not None
    assert timer_data.name == "custom_sync_func"
    assert "custom_sync_func" in parent.child_timers

def test_timed_decorator_async():
    timer_data = None
    
    @kt.timed(name="custom_async_func")
    async def my_async_func(ptimer=None):
        nonlocal timer_data
        timer_data = ptimer

    parent = kt.PerfTimer("parent")
    
    async def run_test():
        await my_async_func(ptimer=parent)
        
    asyncio.run(run_test())
    
    assert timer_data is not None
    assert timer_data.name == "custom_async_func"
    assert "custom_async_func" in parent.child_timers
