import inspect

from redis_ops import get_from_redis, save_to_redis


def get_from_redis_or_set(func):
    def wrapper(*args, **kwargs):
        current_frame = inspect.currentframe()
        _, _, _, values = inspect.getargvalues(current_frame)
        module_name = values["args"][1]
        content = get_from_redis(module_name)
        if content:
            return content
        else:
            content = func(*args, **kwargs)
            save_to_redis(module_name, content)
            return content

    return wrapper
