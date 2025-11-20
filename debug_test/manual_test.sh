#!/bin/bash
echo "Building with optimizations disabled..."
cargo build

echo ""
echo "Starting LLDB session..."
echo "Instructions:"
echo "1. Wait for the breakpoint to hit"
echo "2. Test these commands:"
echo "   frame variable inline_short"
echo "   frame variable inline_short.variant"  
echo "   frame variable inline_short.length"
echo "   frame variable inline_short.content"
echo "   frame variable static_str.pointer"
echo "3. Type 'quit' to exit"
echo ""

lldb target/debug/smolstr_debug_test \
  -o "b std::io::stdio::_print" \
  -o "run" \
  -o "up 2"
