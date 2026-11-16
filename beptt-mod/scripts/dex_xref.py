"""用 androguard 分析 dex:找出引用指定字串的方法,並可反組譯指定方法。

用法:
  python dex_xref.py <dex_dir> str  <regex>          # 找引用字串的「方法」
  python dex_xref.py <dex_dir> meth <類別名regex> [方法名regex]   # 反組譯方法
  python dex_xref.py <dex_dir> cls  <類別名regex>     # 列出類別的欄位/方法簽名
  python dex_xref.py <dex_dir> callers <類別名regex> <方法名regex>  # 誰呼叫這個方法
"""
import re
import sys
import glob
import pickle
import os
from loguru import logger

logger.remove()

from androguard.core.dex import DEX
from androguard.core.analysis.analysis import Analysis

dex_dir, mode = sys.argv[1], sys.argv[2]
args = sys.argv[3:]
cache = os.path.join(os.environ.get("CACHE_DIR", "/tmp"), "dex_analysis.pkl")


def load():
    dx = Analysis()
    for f in sorted(glob.glob(os.path.join(dex_dir, "classes*.dex"))):
        d = DEX(open(f, "rb").read())
        dx.add(d)
    dx.create_xref()
    return dx


dx = load()


def disasm(m):
    em = m.get_method()
    print(f"\n##### {em.get_class_name()}->{em.get_name()}{em.get_descriptor()}")
    if m.is_external():
        print("  (external)")
        return
    code = em.get_code()
    if not code:
        print("  (no code)")
        return
    print(f"  .registers {code.get_registers_size()}")
    idx = 0
    for ins in em.get_instructions():
        print(f"  {idx:05x}  {ins.get_name()} {ins.get_output()}")
        idx += ins.get_length()


if mode == "str":
    pat = re.compile(args[0])
    for s in dx.get_strings():
        val = s.get_value()
        if pat.search(val):
            print(f"\n=== STRING: {val[:160]!r}")
            for c, m in s.get_xref_from():
                print(f"   <- {m.class_name}->{m.name}{m.descriptor}")
elif mode == "meth":
    cpat = re.compile(args[0])
    mpat = re.compile(args[1]) if len(args) > 1 else None
    for m in dx.get_methods():
        em = m.get_method()
        if cpat.search(em.get_class_name()) and (mpat is None or mpat.search(em.get_name())):
            disasm(m)
elif mode == "cls":
    cpat = re.compile(args[0])
    for c in dx.get_classes():
        if cpat.search(c.name) and not c.is_external():
            vm = c.get_vm_class()
            print(f"\n=== {c.name} extends {vm.get_superclassname()} implements {vm.get_interfaces()}")
            for f in vm.get_fields():
                print(f"   field {f.get_name()} : {f.get_descriptor()}")
            for m in vm.get_methods():
                print(f"   meth  {m.get_name()}{m.get_descriptor()}")
elif mode == "callers":
    cpat, mpat = re.compile(args[0]), re.compile(args[1])
    for m in dx.get_methods():
        em = m.get_method()
        if cpat.search(em.get_class_name()) and mpat.search(em.get_name()):
            print(f"\n=== {em.get_class_name()}->{em.get_name()}{em.get_descriptor()}")
            for c, caller, off in m.get_xref_from():
                print(f"   <- {caller.class_name}->{caller.name}{caller.descriptor}")
