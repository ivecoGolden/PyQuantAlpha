# src/ai/validator.py
"""策略代码安全校验"""

import ast

from src.messages import ErrorMessage


# 允许的内置名称
ALLOWED_BUILTINS = {
    'True', 'False', 'None',
    'abs', 'max', 'min', 'len', 'range', 'round',
    'int', 'float', 'str', 'bool', 'list', 'dict',
    'print', 'sum', 'sorted', 'enumerate', 'zip'
}

# 允许的自定义名称（内置指标 + 策略接口）
ALLOWED_NAMES = {
    'Strategy', 'self', 'bar',
    # 内置指标
    'EMA', 'SMA', 'RSI', 'MACD', 'ATR', 'BollingerBands',
    # 指标结果类
    'MACDResult', 'BollingerResult',
    # 策略接口
    'order', 'close', 'get_position', 'equity'
}

# 禁止的 AST 节点类型
FORBIDDEN_NODES = {
    ast.Import,
    ast.ImportFrom,
    ast.Global,
    ast.Nonlocal,
    ast.AsyncFunctionDef,
    ast.AsyncFor,
    ast.AsyncWith,
    ast.Await,
}

# 禁止的函数调用
FORBIDDEN_CALLS = {
    'exec', 'eval', 'compile', 'open', 'input',
    '__import__', 'globals', 'locals', 'vars',
    'getattr', 'setattr', 'delattr', 'hasattr',
    'exit', 'quit', 'breakpoint'
}


def _collect_defined_names(tree: ast.Module) -> set:
    """收集代码中定义的类名和函数名
    
    支持 AI 自定义指标类，不受白名单限制。
    
    Args:
        tree: AST 语法树
        
    Returns:
        代码中定义的名称集合
    """
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            names.add(node.name)
        elif isinstance(node, ast.FunctionDef):
            names.add(node.name)
    return names



def validate_strategy_code(code: str) -> tuple[bool, str]:
    """验证策略代码安全性
    
    Args:
        code: 策略代码字符串
        
    Returns:
        (是否通过, 错误消息)
        
    Example:
        >>> is_valid, msg = validate_strategy_code("class Strategy: ...")
        >>> if not is_valid:
        ...     print(f"校验失败: {msg}")
    """
    if not code or not code.strip():
        return False, ErrorMessage.STRATEGY_CODE_EMPTY
    
    # 1. 语法检查
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return False, ErrorMessage.STRATEGY_SYNTAX_ERROR.format(msg=e.msg, line=e.lineno)
    
    # 2. 收集代码中定义的名称（支持自定义指标类）
    defined_names = _collect_defined_names(tree)
    
    # 3. 检查是否存在 Strategy 类
    classes = [node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
    strategy_classes = [c for c in classes if c.name == "Strategy"]
    
    if len(strategy_classes) == 0:
        return False, ErrorMessage.STRATEGY_CLASS_NOT_FOUND
    if len(strategy_classes) > 1:
        return False, ErrorMessage.STRATEGY_ONLY_ONE_CLASS
    
    strategy_class = strategy_classes[0]
    
    # 4. 检查必要方法
    methods = {node.name for node in strategy_class.body if isinstance(node, ast.FunctionDef)}
    if "init" not in methods:
        return False, ErrorMessage.STRATEGY_MISSING_INIT
    if "on_bar" not in methods:
        return False, ErrorMessage.STRATEGY_MISSING_ON_BAR
    
    # 5. 检查禁止的节点
    for node in ast.walk(tree):
        if type(node) in FORBIDDEN_NODES:
            node_name = type(node).__name__
            return False, ErrorMessage.STRATEGY_FORBIDDEN_NODE.format(node=node_name)
    
    # 6. 检查禁止的函数调用
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                if node.func.id in FORBIDDEN_CALLS:
                    return False, ErrorMessage.STRATEGY_FORBIDDEN_CALL.format(func=node.func.id)
    
    return True, "验证通过"


def execute_strategy_code(code: str) -> object:
    """安全执行策略代码并返回策略实例
    
    Args:
        code: 已验证的策略代码
        
    Returns:
        Strategy 类实例
        
    Raises:
        RuntimeError: 执行失败
        
    Example:
        >>> code = "class Strategy: ..."
        >>> is_valid, _ = validate_strategy_code(code)
        >>> if is_valid:
        ...     strategy = execute_strategy_code(code)
    """
    # 创建受限的执行环境
    # 注意：这里需要在回测引擎实现后注入指标类
    import builtins
    
    # 必须包含 __build_class__ 才能定义类
    safe_builtins = {
        '__build_class__': builtins.__build_class__,
        '__name__': '__main__',
    }
    
    # 添加允许的内置函数
    for name in ALLOWED_BUILTINS:
        if hasattr(builtins, name):
            safe_builtins[name] = getattr(builtins, name)
    
    safe_globals = {
        '__builtins__': safe_builtins,
    }
    safe_locals = {}
    
    # 注入指标类
    try:
        from src.indicators.ma import SMA, EMA
        from src.indicators.oscillator import RSI, MACD
        from src.indicators.volatility import ATR, BollingerBands
        
        indicators = {
            'SMA': SMA, 'EMA': EMA,
            'RSI': RSI, 'MACD': MACD,
            'ATR': ATR, 'BollingerBands': BollingerBands
        }
        safe_globals.update(indicators)
    except ImportError as e:
        # 如果回测引擎还没就绪，可能会失败，但在集成测试环境应该有了
        pass

    try:
        # 使用同一个字典作为 globals 和 locals
        # 这样定义的辅助类（如 VIXIndicator）会进入 globals
        # 使得 Strategy 类的方法可以访问到它们
        exec(code, safe_globals, safe_globals)
        strategy_class = safe_globals.get('Strategy')
        if strategy_class is None:
            raise RuntimeError(ErrorMessage.STRATEGY_CLASS_NOT_FOUND)
        return strategy_class()
    except RuntimeError:
        raise
    except Exception as e:
        raise RuntimeError(ErrorMessage.STRATEGY_EXECUTE_FAILED.format(error=str(e)))
