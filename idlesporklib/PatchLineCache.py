"""
WARNING!!
This file changes the behaviour of the module linecache
"""
import linecache
def extended_linecache_checkcache(filename=None,
                                  orig_checkcache=linecache.checkcache):
    """Extend linecache.checkcache to preserve the <pyshell#...> entries

    Rather than repeating the linecache code, patch it to save the
    <pyshell#...> entries, call the original linecache.checkcache()
    (which destroys them), and then restore the saved entries.

    orig_checkcache is bound at definition time to the original
    method, allowing it to be patched.

    """
    cache = linecache.cache
    save = {}
    for key in list(cache):
        if key[:1] + key[-1:] == '<>':
            save[key] = cache.pop(key)
    orig_checkcache(filename)
    cache.update(save)

# Patch linecache.checkcache():
def patch_linecache():
    global linecache
    linecache.checkcache = extended_linecache_checkcache

