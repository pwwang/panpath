async def async_generator_to_list(async_gen):
    """Convert an async generator to a list."""
    result = []
    async for item in async_gen:
        result.append(item)
    return result
