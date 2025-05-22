# translate/utils/parallel.py
import concurrent
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict

def batch_process(
    data: List[Dict],
    process_func,
    max_workers: int = 16,
    batch_size: int = 50
) -> List:
    """
    通用批处理并行执行框架
    :param data: 输入数据列表
    :param process_func: 处理函数 (row -> result)
    :param max_workers: 最大并行度
    :param batch_size: 单批处理量（平衡内存与效率）
    :return: 按原始顺序排列的结果列表
    """
    results = [None] * len(data)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = []
        for i, row in enumerate(data):
            futures.append((i, executor.submit(process_func, row)))

        for future in concurrent.futures.as_completed([f[1] for f in futures]):
            index = [f[0] for f in futures if f[1] == future][0]
            try:
                results[index] = future.result()
            except Exception as e:
                results[index] = f"Error processing row {index}: {str(e)}"

    return [res for res in results if res is not None]
