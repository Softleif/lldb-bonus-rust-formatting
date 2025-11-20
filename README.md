This module provides pretty-printing support for popular third-party crates
that are not part of the Rust standard library.

## Currently supported

- `smol_str::SmolStr` - Summary and synthetic provider
- `smallvec::SmallVec<T, N>` - Summary and synthetic provider

## Features

### SmolStr

The `SmolStr` type provides both a summary provider (for quick display) and a synthetic provider (for inspecting internal structure).

**Summary Provider:**
- Displays the string content in quotes, e.g., `"hello"`
- Works for all three internal variants (Inline, Static, Heap)

**Synthetic Provider:**
Exposes the following child fields:
- `variant` - String showing the internal representation: "Inline", "Static", or "Heap"
- `length` - The string length as an unsigned integer
- `content` - The string content
- `pointer` - The memory address (only for Static and Heap variants)

**Example:**
```
(smol_str::SmolStr) inline_short = "hello" {
  variant = "Inline"
  length = 5
  content = "hello"
}

(smol_str::SmolStr) static_str = "static string" {
  variant = "Static"
  length = 13
  content = "static string"
  pointer = 0x000000010004197c
}

(smol_str::SmolStr) heap_long = "this is a very long string that will be heap allocated" {
  variant = "Heap"
  length = 54
  content = "this is a very long string that will be heap allocated"
  pointer = 0x00006000014640a0
}
```

### SmallVec

The `SmallVec` type provides both a summary provider and synthetic provider for inspecting inline vs heap storage.

## Usage:

To load this in LLDB, add to your `.lldbinit` or run in LLDB:

    command script import "/path/to/your/project/rust_bonus_types.py"

Or create a `.lldbinit` in your project directory with:

    command script import rust_bonus_types.py

## Testing

A test crate is provided in `debug_test/` with example values for all supported types. Build and run the tests with:

```bash
cd debug_test
cargo build
lldb -s lldb_scripts/test_smolstr_synthetic.lldb
```
