# project/apps/translate/utils/__init__.py
"""
解析工具模块
"""

# 从父目录的 utils.py 导入所有内容以保持向后兼容
# 使用延迟导入避免循环依赖
import sys
import os

# 获取父目录路径
_parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 缓存已加载的模块
_utils_py_module = None

def _load_utils_py():
    """加载 utils.py 模块（延迟加载）"""
    global _utils_py_module
    if _utils_py_module is None:
        import importlib.util
        utils_py_path = os.path.join(_parent_dir, 'utils.py')
        if os.path.exists(utils_py_path):
            spec = importlib.util.spec_from_file_location("translate_utils_py", utils_py_path)
            _utils_py_module = importlib.util.module_from_spec(spec)
            _utils_py_module.__package__ = 'project.apps.translate'
            spec.loader.exec_module(_utils_py_module)
            
            # 将所有公共属性添加到当前模块的命名空间
            for name in dir(_utils_py_module):
                if not name.startswith('_'):
                    setattr(sys.modules[__name__], name, getattr(_utils_py_module, name))
            
            # 设置 __all__ 以支持 import *
            if hasattr(_utils_py_module, '__all__'):
                sys.modules[__name__].__all__ = _utils_py_module.__all__
            else:
                # 如果没有定义 __all__，使用所有公共属性
                public_names = [name for name in dir(_utils_py_module) if not name.startswith('_')]
                sys.modules[__name__].__all__ = public_names
    return _utils_py_module

def __getattr__(name):
    """延迟导入 utils.py 中的内容"""
    _load_utils_py()
    if _utils_py_module and hasattr(_utils_py_module, name):
        return getattr(_utils_py_module, name)
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

def __dir__():
    """支持 dir() 和 import *"""
    _load_utils_py()
    if _utils_py_module:
        # 返回所有公共属性
        return [name for name in dir(_utils_py_module) if not name.startswith('_')]
    return []

