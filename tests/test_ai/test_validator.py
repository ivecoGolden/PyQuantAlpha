# tests/test_ai/test_validator.py
"""策略代码校验器测试"""

import pytest
from src.ai.validator import validate_strategy_code, execute_strategy_code


class TestValidateStrategyCode:
    """validate_strategy_code 测试"""
    
    def test_valid_strategy(self):
        """测试有效策略代码"""
        code = '''
class Strategy:
    def init(self):
        self.ema = EMA(20)
    
    def on_bar(self, bar):
        self.ema.update(bar.close)
'''
        is_valid, msg = validate_strategy_code(code)
        assert is_valid
        assert msg == "验证通过"
    
    def test_empty_code(self):
        """测试空代码"""
        is_valid, msg = validate_strategy_code("")
        assert not is_valid
        assert "不能为空" in msg
    
    def test_missing_class(self):
        """测试缺少类定义"""
        code = "x = 1"
        is_valid, msg = validate_strategy_code(code)
        assert not is_valid
        assert "未找到 Strategy" in msg
    
    def test_wrong_class_name(self):
        """测试错误的类名"""
        code = '''
class MyStrategy:
    def init(self): pass
    def on_bar(self, bar): pass
'''
        is_valid, msg = validate_strategy_code(code)
        assert not is_valid
        assert "Strategy" in msg
    
    def test_multiple_classes(self):
        """测试多个类定义"""
        code = '''
class Strategy:
    def init(self): pass
    def on_bar(self, bar): pass

class Helper:
    pass
'''
        is_valid, msg = validate_strategy_code(code)
        assert not is_valid
        assert "只能定义一个类" in msg
    
    def test_missing_init(self):
        """测试缺少 init 方法"""
        code = '''
class Strategy:
    def on_bar(self, bar): pass
'''
        is_valid, msg = validate_strategy_code(code)
        assert not is_valid
        assert "init()" in msg
    
    def test_missing_on_bar(self):
        """测试缺少 on_bar 方法"""
        code = '''
class Strategy:
    def init(self): pass
'''
        is_valid, msg = validate_strategy_code(code)
        assert not is_valid
        assert "on_bar()" in msg
    
    def test_import_not_allowed(self):
        """测试禁止 import"""
        code = '''
import os
class Strategy:
    def init(self): pass
    def on_bar(self, bar): pass
'''
        is_valid, msg = validate_strategy_code(code)
        assert not is_valid
        assert "Import" in msg
    
    def test_from_import_not_allowed(self):
        """测试禁止 from import"""
        code = '''
from os import path
class Strategy:
    def init(self): pass
    def on_bar(self, bar): pass
'''
        is_valid, msg = validate_strategy_code(code)
        assert not is_valid
        assert "ImportFrom" in msg
    
    def test_exec_not_allowed(self):
        """测试禁止 exec"""
        code = '''
class Strategy:
    def init(self): pass
    def on_bar(self, bar):
        exec("print(1)")
'''
        is_valid, msg = validate_strategy_code(code)
        assert not is_valid
        assert "exec" in msg
    
    def test_eval_not_allowed(self):
        """测试禁止 eval"""
        code = '''
class Strategy:
    def init(self): pass
    def on_bar(self, bar):
        eval("1+1")
'''
        is_valid, msg = validate_strategy_code(code)
        assert not is_valid
        assert "eval" in msg
    
    def test_syntax_error(self):
        """测试语法错误"""
        code = '''
class Strategy:
    def init(self)
        pass
'''
        is_valid, msg = validate_strategy_code(code)
        assert not is_valid
        assert "语法错误" in msg


class TestExecuteStrategyCode:
    """execute_strategy_code 测试"""
    
    def test_execute_valid_code(self):
        """测试执行有效代码"""
        code = '''
class Strategy:
    def init(self):
        self.value = 0
    
    def on_bar(self, bar):
        self.value += 1
'''
        strategy = execute_strategy_code(code)
        assert strategy is not None
        assert hasattr(strategy, 'init')
        assert hasattr(strategy, 'on_bar')
    
    def test_execute_invalid_code_raises(self):
        """测试执行无效代码抛出异常"""
        code = "x = 1"  # 没有 Strategy 类
        with pytest.raises(RuntimeError) as exc_info:
            execute_strategy_code(code)
        assert "未找到 Strategy 类" in str(exc_info.value)
