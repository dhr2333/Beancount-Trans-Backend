"""
CycleCalculator 周期计算服务测试
"""
import pytest
from datetime import date
from project.apps.reconciliation.services.cycle_calculator import CycleCalculator


class TestCycleCalculator:
    """CycleCalculator 周期计算服务测试"""
    
    def test_calculate_next_date_days(self):
        """测试每 N 天：1 月 1 日 + 15 天 = 1 月 16 日"""
        from_date = date(2026, 1, 1)
        next_date = CycleCalculator.get_next_date('days', 15, from_date)
        assert next_date == date(2026, 1, 16)
    
    def test_calculate_next_date_weeks(self):
        """测试每 N 周：1 月 1 日 + 2 周 = 1 月 15 日"""
        from_date = date(2026, 1, 1)
        next_date = CycleCalculator.get_next_date('weeks', 2, from_date)
        assert next_date == date(2026, 1, 15)
    
    def test_calculate_next_date_months(self):
        """测试每 N 月：1 月 1 日 + 1 月 = 2 月 1 日"""
        from_date = date(2026, 1, 1)
        next_date = CycleCalculator.get_next_date('months', 1, from_date)
        assert next_date == date(2026, 2, 1)
    
    def test_calculate_next_date_years(self):
        """测试每 N 年：2025-01-01 + 1 年 = 2026-01-01"""
        from_date = date(2025, 1, 1)
        next_date = CycleCalculator.get_next_date('years', 1, from_date)
        assert next_date == date(2026, 1, 1)
    
    def test_month_end_boundary_non_leap_year(self):
        """测试月末边界情况：1 月 31 日 + 1 月 = 2 月 28 日（非闰年）"""
        from_date = date(2025, 1, 31)  # 2025 年不是闰年
        next_date = CycleCalculator.get_next_date('months', 1, from_date)
        assert next_date == date(2025, 2, 28)
    
    def test_month_end_boundary_leap_year(self):
        """测试月末边界情况：1 月 31 日 + 1 月 = 2 月 29 日（闰年）"""
        from_date = date(2024, 1, 31)  # 2024 年是闰年
        next_date = CycleCalculator.get_next_date('months', 1, from_date)
        assert next_date == date(2024, 2, 29)
    
    def test_month_end_boundary_jan_30(self):
        """测试月末边界情况：1 月 30 日 + 1 月 = 2 月 28 日（非闰年）"""
        from_date = date(2025, 1, 30)
        next_date = CycleCalculator.get_next_date('months', 1, from_date)
        assert next_date == date(2025, 2, 28)
    
    def test_month_end_boundary_march_31(self):
        """测试月末边界情况：3 月 31 日 + 1 月 = 4 月 30 日（不存在 4 月 31 日）"""
        from_date = date(2026, 3, 31)
        next_date = CycleCalculator.get_next_date('months', 1, from_date)
        assert next_date == date(2026, 4, 30)
    
    def test_cross_year_boundary_dec_31(self):
        """测试跨年边界：12 月 31 日 + 1 月 = 次年 1 月 31 日"""
        from_date = date(2025, 12, 31)
        next_date = CycleCalculator.get_next_date('months', 1, from_date)
        assert next_date == date(2026, 1, 31)
    
    def test_cross_year_boundary_dec_1(self):
        """测试跨年边界：12 月 1 日 + 2 月 = 次年 2 月 1 日"""
        from_date = date(2025, 12, 1)
        next_date = CycleCalculator.get_next_date('months', 2, from_date)
        assert next_date == date(2026, 2, 1)
    
    def test_calculate_next_date_method(self):
        """测试 calculate_next_date 方法正确计算下一个日期"""
        from_date = date(2026, 1, 15)
        
        # 测试不同周期单位
        assert CycleCalculator.get_next_date('days', 10, from_date) == date(2026, 1, 25)
        assert CycleCalculator.get_next_date('weeks', 1, from_date) == date(2026, 1, 22)
        assert CycleCalculator.get_next_date('months', 1, from_date) == date(2026, 2, 15)
        assert CycleCalculator.get_next_date('years', 1, from_date) == date(2027, 1, 15)
    
    def test_invalid_unit_raises_error(self):
        """测试传入无效周期单位时抛出异常"""
        from_date = date(2026, 1, 1)
        
        with pytest.raises(ValueError, match="无效的周期单位"):
            CycleCalculator.get_next_date('invalid', 1, from_date)
    
    def test_none_unit_raises_error(self):
        """测试传入 None 周期单位时抛出异常"""
        from_date = date(2026, 1, 1)
        
        with pytest.raises(ValueError, match="无效的周期单位"):
            CycleCalculator.get_next_date(None, 1, from_date)
    
    def test_zero_interval_raises_error(self):
        """测试间隔为 0 时抛出异常"""
        from_date = date(2026, 1, 1)
        
        with pytest.raises(ValueError, match="间隔数量必须大于 0"):
            CycleCalculator.get_next_date('days', 0, from_date)
    
    def test_negative_interval_raises_error(self):
        """测试间隔为负数时抛出异常"""
        from_date = date(2026, 1, 1)
        
        with pytest.raises(ValueError, match="间隔数量必须大于 0"):
            CycleCalculator.get_next_date('days', -1, from_date)
    
    def test_none_from_date_raises_error(self):
        """测试 from_date 为 None 时抛出异常"""
        with pytest.raises(ValueError, match="from_date 不能为 None"):
            CycleCalculator.get_next_date('days', 1, None)
    
    def test_is_valid_unit(self):
        """测试 is_valid_unit 方法"""
        assert CycleCalculator.is_valid_unit('days') is True
        assert CycleCalculator.is_valid_unit('weeks') is True
        assert CycleCalculator.is_valid_unit('months') is True
        assert CycleCalculator.is_valid_unit('years') is True
        assert CycleCalculator.is_valid_unit('invalid') is False
        assert CycleCalculator.is_valid_unit(None) is False
    
    def test_multiple_intervals(self):
        """测试多个间隔单位"""
        from_date = date(2026, 1, 1)
        
        # 每 3 天
        assert CycleCalculator.get_next_date('days', 3, from_date) == date(2026, 1, 4)
        
        # 每 2 周
        assert CycleCalculator.get_next_date('weeks', 2, from_date) == date(2026, 1, 15)
        
        # 每 3 月
        assert CycleCalculator.get_next_date('months', 3, from_date) == date(2026, 4, 1)
        
        # 每 2 年
        assert CycleCalculator.get_next_date('years', 2, from_date) == date(2028, 1, 1)

