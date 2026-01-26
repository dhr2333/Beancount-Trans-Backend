"""
日历计算服务

使用 python-dateutil 的 relativedelta 处理日期计算。
"""
from datetime import date
from dateutil.relativedelta import relativedelta


class CycleCalculator:
    """日历计算服务
    
    使用 python-dateutil 的 relativedelta 处理日期计算，
    自动处理月末等边界情况（如 1月31日 + 1月 = 2月28/29日）
    
    重要：计算下一个待办日期时，基于当前待办的 scheduled_date（而非 completed_date），
    以保持周期性（如每月 1 号对账，即使 5 号才完成，下次仍为下月 1 号）
    """
    
    VALID_UNITS = {'days', 'weeks', 'months', 'years'}
    
    @classmethod
    def get_next_date(
        cls, 
        unit: str,           # 'days', 'weeks', 'months', 'years'
        interval: int = 1,   # 间隔数量
        from_date: date = None  # 基准日期（当前待办的 scheduled_date）
    ) -> date:
        """计算下一次执行日期
        
        Args:
            unit: 周期单位（days/weeks/months/years）
            interval: 间隔数量，默认为 1
            from_date: 基准日期（当前待办的 scheduled_date，而非 completed_date）
            
        Returns:
            下一次执行日期
            
        Raises:
            ValueError: 无效的周期单位或间隔数量
            
        示例：
            get_next_date('days', 3, date(2026, 1, 1))    → 2026-01-04（每 3 天）
            get_next_date('weeks', 2, date(2026, 1, 1))   → 2026-01-15（每 2 周）
            get_next_date('months', 1, date(2026, 1, 1))  → 2026-02-01（每 1 个月）
            
        注意：
            - 基于 scheduled_date 而非 completed_date，保持周期性
            - 如每月 1 号对账，即使 5 号才完成，下次仍为下月 1 号
        """
        if from_date is None:
            raise ValueError("from_date 不能为 None")
        
        if unit not in cls.VALID_UNITS:
            raise ValueError(f"无效的周期单位: {unit}，必须是 {', '.join(cls.VALID_UNITS)} 之一")
        if interval <= 0:
            raise ValueError("间隔数量必须大于 0")
        
        # 直接利用 relativedelta 的参数化能力
        # relativedelta(days=3) / relativedelta(weeks=2) / relativedelta(months=1)
        return from_date + relativedelta(**{unit: interval})
    
    @classmethod
    def is_valid_unit(cls, unit: str) -> bool:
        """检查周期单位是否有效
        
        Args:
            unit: 周期单位字符串
            
        Returns:
            如果是有效单位返回 True，否则返回 False
        """
        return unit in cls.VALID_UNITS
