# LLDB Rust Debugger Support - Agent Context

## Overview
This directory contains Python scripts that provide pretty-printing for Rust types in LLDB debuggers (VS Code, CLion, etc.).
The `rust_bonus_types.py` standalone module adds support for third-party crates beyond the standard library.

## Architecture
The standalone file uses `__lldb_init_module()` to self-register with LLDB's "rust" category using `SBTypeSummary` and `SBTypeSynthetic`.
Summary providers return formatted strings; synthetic providers expose element children via `get_child_at_index()`.

## Type Detection Pattern
Third-party types use discriminant bits, nested unions, or template arguments to determine internal layout.
Use `frame variable -R` in LLDB to inspect raw structure, look for `$variants$`, `$discr$`, or union fields.

## Adding New Types
Create summary function returning string (e.g., `"value"`), optional synthetic class with `num_children()`/`get_child_at_index()`/`update()`.
Register in `__lldb_init_module()` with type name pattern (exact or regex) and provider function name.

## Testing
There is a crate in `debug_test`.

Before adding a feature, add a test case in `debug_test/src/main.rs`.
Then, write `.lldb` scripts like

```lldb
file target/debug/debug_test
breakpoint set --line 22
run
frame variable -R inline_short
p sizeof(smol_str::SmolStr)
memory read -c 32 -f x `&inline_short`
quit
```

to discover what the type looks like and use it continuosly to prove your changes work.

## Approach
If possible, use crash or sequential thinking.
Make a plan first, then implement it step by step, starting with a test case.
