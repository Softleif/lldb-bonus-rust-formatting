"""
LLDB debugging support for third-party Rust types
"""

from __future__ import annotations

import re
import sys
from typing import TYPE_CHECKING

import lldb
from lldb import SBError

if TYPE_CHECKING:
    from lldb import SBValue

PY3 = sys.version_info[0] == 3


def SmolStrSummaryProvider(valobj: SBValue, _dict) -> str:
    """
    Summary provider for smol_str::SmolStr

    SmolStr uses an internal Repr enum with three variants:
    - Inline (discriminant 0-23): small strings stored inline, discriminant is the length
    - Static (discriminant 0x18=24): reference to static string
    - Heap (discriminant >= 0x19=25): Arc-allocated string on heap

    Args:
        valobj: The SmolStr value to format
        _dict: LLDB internal bookkeeping parameter

    Returns:
        A string representation like "hello" with quotes
    """
    # Get the internal Repr enum
    valobj = valobj.GetNonSyntheticValue()
    repr_enum = valobj.GetChildAtIndex(0)

    # Get the $variants$ field (LLDB encoded enum)
    variants = repr_enum.GetChildMemberWithName("$variants$")
    if not variants.IsValid():
        return '""'

    # Get discriminant from $variant$24 (which contains $discr$ field)
    variant24 = variants.GetChildMemberWithName("$variant$24")
    if not variant24.IsValid():
        return '""'

    discr_field = variant24.GetChildMemberWithName("$discr$")
    if not discr_field.IsValid():
        return '""'

    discriminant = discr_field.GetValueAsUnsigned()

    # Inline variant: discriminant is 0-23 (the length)
    if discriminant <= 23:
        length = discriminant
        if length == 0:
            return '""'

        # Get the inline buffer from $variant$
        variant0 = variants.GetChildMemberWithName("$variant$")
        if not variant0.IsValid():
            return '""'

        value = variant0.GetChildMemberWithName("value")
        if not value.IsValid():
            return '""'

        buf = value.GetChildMemberWithName("buf")
        if not buf.IsValid():
            return '""'

        # Read bytes from the buffer
        error = SBError()
        process = buf.GetProcess()
        data = process.ReadMemory(buf.GetLoadAddress(), length, error)
        if error.Success():
            if PY3:
                try:
                    data = data.decode("utf-8", "replace")
                except Exception:
                    return '""'
            return '"%s"' % data
        return '""'

    # Static variant: discriminant is 0x18 (24)
    elif discriminant == 24:
        # Get &str from $variant$24.value.__0
        value = variant24.GetChildMemberWithName("value")
        if not value.IsValid():
            return '""'

        str_ref = value.GetChildMemberWithName("__0")
        if not str_ref.IsValid():
            return '""'

        data_ptr = str_ref.GetChildMemberWithName("data_ptr")
        length_field = str_ref.GetChildMemberWithName("length")

        if not data_ptr.IsValid() or not length_field.IsValid():
            return '""'

        length = length_field.GetValueAsUnsigned()
        if length == 0:
            return '""'

        ptr = data_ptr.GetValueAsUnsigned()
        error = SBError()
        process = data_ptr.GetProcess()
        data = process.ReadMemory(ptr, length, error)
        if error.Success():
            if PY3:
                try:
                    data = data.decode("utf-8", "replace")
                except Exception:
                    return '""'
            return '"%s"' % data
        return '""'

    # Heap variant: discriminant >= 0x19 (25)
    else:
        # Get Arc<str> from $variant$25.value.__0.ptr.pointer
        variant25 = variants.GetChildMemberWithName("$variant$25")
        if not variant25.IsValid():
            return '""'

        value = variant25.GetChildMemberWithName("value")
        if not value.IsValid():
            return '""'

        inner = value.GetChildMemberWithName("__0")
        if not inner.IsValid():
            return '""'

        ptr_field = inner.GetChildMemberWithName("ptr")
        if not ptr_field.IsValid():
            return '""'

        pointer = ptr_field.GetChildMemberWithName("pointer")
        if not pointer.IsValid():
            return '""'

        data_ptr = pointer.GetChildMemberWithName("data_ptr")
        length_field = pointer.GetChildMemberWithName("length")

        if not data_ptr.IsValid() or not length_field.IsValid():
            return '""'

        length = length_field.GetValueAsUnsigned()
        if length == 0:
            return '""'

        ptr = data_ptr.GetValueAsUnsigned()

        # Arc<str> pointer points to ArcInner which has:
        # - strong: AtomicUsize (8 bytes)
        # - weak: AtomicUsize (8 bytes)
        # - data: [u8] (the actual string)
        # So we need to skip 16 bytes to get to the string data
        arc_header_size = 16
        string_data_ptr = ptr + arc_header_size

        error = SBError()
        process = data_ptr.GetProcess()
        data = process.ReadMemory(string_data_ptr, length, error)
        if error.Success():
            if PY3:
                try:
                    data = data.decode("utf-8", "replace")
                except Exception:
                    return '""'
            return '"%s"' % data
        return '""'


class SmolStrSyntheticProvider:
    """
    Synthetic provider for smol_str::SmolStr

    Exposes internal structure as children:
    - variant: "Inline", "Static", or "Heap"
    - length: the string length
    - content: the string content
    - pointer: the pointer address (for Static and Heap variants)
    """

    def __init__(self, valobj: SBValue, _dict):
        self.valobj = valobj
        self.variant_name = ""
        self.length = 0
        self.content = ""
        self.pointer = 0
        self.content_address = 0  # Store address of string data
        self.update()

    def num_children(self):
        # Always show: variant, length, content
        # Show pointer for Static and Heap variants
        if self.variant_name in ("Static", "Heap"):
            return 4
        return 3

    def get_child_index(self, name: str):
        if name == "variant":
            return 0
        elif name == "length":
            return 1
        elif name == "content":
            return 2
        elif name == "pointer":
            return 3
        return -1

    def get_child_at_index(self, index: int):
        if index < 0:
            return None

        try:
            if index == 0:
                # variant field - return as string summary
                # Create a value that will display the variant name
                return self.valobj.CreateValueFromExpression(
                    "variant", '(const char*)"%s"' % self.variant_name
                )
            elif index == 1:
                # length field - create as unsigned integer
                return self.valobj.CreateValueFromExpression(
                    "length", "(unsigned long long)%d" % self.length
                )
            elif index == 2:
                # content field - create as char array pointing to actual data
                if self.content_address != 0 and self.length > 0:
                    # Create char[length] type
                    char_type = self.valobj.GetTarget().GetBasicType(
                        lldb.eBasicTypeChar
                    )
                    char_array_type = char_type.GetArrayType(self.length)

                    # Create value from address
                    return self.valobj.CreateValueFromAddress(
                        "content", self.content_address, char_array_type
                    )
                else:
                    # Empty string
                    return self.valobj.CreateValueFromExpression(
                        "content", '(const char*)""'
                    )
            elif index == 3 and self.variant_name in ("Static", "Heap"):
                # pointer field - create as hex pointer
                return self.valobj.CreateValueFromExpression(
                    "pointer", "(void*)0x%x" % self.pointer
                )
        except Exception:
            return None

        return None

    def update(self):
        self.variant_name = ""
        self.length = 0
        self.content = ""
        self.pointer = 0
        self.content_address = 0

        try:
            valobj = self.valobj.GetNonSyntheticValue()
            repr_enum = valobj.GetChildAtIndex(0)

            # Get the $variants$ field (LLDB encoded enum)
            variants = repr_enum.GetChildMemberWithName("$variants$")
            if not variants.IsValid():
                return

            # Get discriminant from $variant$24 (which contains $discr$ field)
            variant24 = variants.GetChildMemberWithName("$variant$24")
            if not variant24.IsValid():
                return

            discr_field = variant24.GetChildMemberWithName("$discr$")
            if not discr_field.IsValid():
                return

            discriminant = discr_field.GetValueAsUnsigned()

            # Inline variant: discriminant is 0-23 (the length)
            if discriminant <= 23:
                self.variant_name = "Inline"
                self.length = discriminant
                if self.length == 0:
                    self.content = ""
                    return

                # Get the inline buffer from $variant$
                variant0 = variants.GetChildMemberWithName("$variant$")
                if not variant0.IsValid():
                    return

                value = variant0.GetChildMemberWithName("value")
                if not value.IsValid():
                    return

                buf = value.GetChildMemberWithName("buf")
                if not buf.IsValid():
                    return

                # Store the address of the inline buffer
                self.content_address = buf.GetLoadAddress()

                # Read bytes from the buffer for summary
                error = SBError()
                process = buf.GetProcess()
                data = process.ReadMemory(self.content_address, self.length, error)
                if error.Success():
                    if PY3:
                        try:
                            self.content = data.decode("utf-8", "replace")
                        except Exception:
                            self.content = ""
                    else:
                        self.content = data

            # Static variant: discriminant is 0x18 (24)
            elif discriminant == 24:
                self.variant_name = "Static"

                # Get &str from $variant$24.value.__0
                value = variant24.GetChildMemberWithName("value")
                if not value.IsValid():
                    return

                str_ref = value.GetChildMemberWithName("__0")
                if not str_ref.IsValid():
                    return

                data_ptr = str_ref.GetChildMemberWithName("data_ptr")
                length_field = str_ref.GetChildMemberWithName("length")

                if not data_ptr.IsValid() or not length_field.IsValid():
                    return

                self.length = length_field.GetValueAsUnsigned()
                self.pointer = data_ptr.GetValueAsUnsigned()
                self.content_address = self.pointer

                if self.length == 0:
                    self.content = ""
                    return

                error = SBError()
                process = data_ptr.GetProcess()
                data = process.ReadMemory(self.pointer, self.length, error)
                if error.Success():
                    if PY3:
                        try:
                            self.content = data.decode("utf-8", "replace")
                        except Exception:
                            self.content = ""
                    else:
                        self.content = data

            # Heap variant: discriminant >= 0x19 (25)
            else:
                self.variant_name = "Heap"

                # Get Arc<str> from $variant$25.value.__0.ptr.pointer
                variant25 = variants.GetChildMemberWithName("$variant$25")
                if not variant25.IsValid():
                    return

                value = variant25.GetChildMemberWithName("value")
                if not value.IsValid():
                    return

                inner = value.GetChildMemberWithName("__0")
                if not inner.IsValid():
                    return

                ptr_field = inner.GetChildMemberWithName("ptr")
                if not ptr_field.IsValid():
                    return

                pointer = ptr_field.GetChildMemberWithName("pointer")
                if not pointer.IsValid():
                    return

                data_ptr = pointer.GetChildMemberWithName("data_ptr")
                length_field = pointer.GetChildMemberWithName("length")

                if not data_ptr.IsValid() or not length_field.IsValid():
                    return

                self.length = length_field.GetValueAsUnsigned()
                self.pointer = data_ptr.GetValueAsUnsigned()

                if self.length == 0:
                    self.content = ""
                    return

                # Arc<str> pointer points to ArcInner which has:
                # - strong: AtomicUsize (8 bytes)
                # - weak: AtomicUsize (8 bytes)
                # - data: [u8] (the actual string)
                # So we need to skip 16 bytes to get to the string data
                arc_header_size = 16
                string_data_ptr = self.pointer + arc_header_size
                self.content_address = string_data_ptr

                error = SBError()
                process = data_ptr.GetProcess()
                data = process.ReadMemory(string_data_ptr, self.length, error)
                if error.Success():
                    if PY3:
                        try:
                            self.content = data.decode("utf-8", "replace")
                        except Exception:
                            self.content = ""
                    else:
                        self.content = data

        except Exception:
            self.variant_name = ""
            self.length = 0
            self.content = ""
            self.pointer = 0
            self.content_address = 0

    def has_children(self):
        return True


def SmallVecSummaryProvider(valobj: SBValue, _dict) -> str:
    """
    Summary provider for smallvec::SmallVec<T, N>

    SmallVec stores up to N elements inline, larger collections on heap.
    Uses a discriminant bit in the len field:
    - len & 1 == 0: inline storage
    - len & 1 == 1: heap storage
    - Actual length is len >> 1

    Args:
        valobj: The SmallVec value to format
        _dict: LLDB internal bookkeeping parameter

    Returns:
        A string representation showing size like "size=4"
    """
    valobj = valobj.GetNonSyntheticValue()

    # Get the len field
    len_field = valobj.GetChildMemberWithName("len")
    if not len_field.IsValid():
        return "size=?"

    len_inner = len_field.GetChildMemberWithName("__0")
    if not len_inner.IsValid():
        return "size=?"

    len_value = len_inner.GetValueAsUnsigned()

    # Extract actual length (len >> 1)
    actual_length = len_value >> 1

    return "size=%d" % actual_length


class SmallVecSyntheticProvider:
    """
    Synthetic provider for smallvec::SmallVec<T, N>

    Provides access to individual elements as children in the debugger.
    """

    def __init__(self, valobj: SBValue, _dict):
        self.valobj = valobj
        self.length = 0
        self.is_heap = False
        self.heap_ptr = 0
        self.inline_data_address = 0
        self.element_size = 0
        self.element_type = None
        self.update()

    def num_children(self):
        return self.length

    def get_child_index(self, name: str):
        try:
            return int(name.lstrip("[").rstrip("]"))
        except Exception:
            return -1

    def get_child_at_index(self, index: int):
        if index < 0 or index >= self.length:
            return None

        if not self.element_type or not self.element_type.IsValid():
            return None

        if self.element_size == 0:
            return None

        try:
            if self.is_heap:
                # Read from heap - calculate address and create value
                if self.heap_ptr == 0:
                    return None
                address = self.heap_ptr + index * self.element_size
                element = self.valobj.CreateValueFromAddress(
                    "[%d]" % index, address, self.element_type
                )
                return element
            else:
                # Read from inline storage - calculate address from inline buffer
                if self.inline_data_address == 0:
                    return None
                address = self.inline_data_address + index * self.element_size
                element = self.valobj.CreateValueFromAddress(
                    "[%d]" % index, address, self.element_type
                )
                return element

        except Exception:
            return None

    def update(self):
        self.length = 0
        self.is_heap = False
        self.heap_ptr = 0
        self.inline_data_address = 0
        self.element_size = 0
        self.element_type = None

        try:
            valobj = self.valobj.GetNonSyntheticValue()

            # Get the len field
            len_field = valobj.GetChildMemberWithName("len")
            if not len_field.IsValid():
                return

            len_inner = len_field.GetChildMemberWithName("__0")
            if not len_inner.IsValid():
                return

            len_value = len_inner.GetValueAsUnsigned()

            # Check discriminant bit (bit 0)
            self.is_heap = (len_value & 1) == 1

            # Extract actual length (len >> 1)
            self.length = len_value >> 1

            # Get element type from SmallVec<T, N> template argument
            self.element_type = valobj.GetType().GetTemplateArgumentType(0)
            if not self.element_type.IsValid():
                self.length = 0
                return

            self.element_size = self.element_type.GetByteSize()
            if self.element_size == 0:
                self.length = 0
                return

            # Get raw union
            raw = valobj.GetChildMemberWithName("raw")
            if not raw.IsValid():
                self.length = 0
                return

            if self.is_heap:
                # Get heap pointer address
                heap = raw.GetChildMemberWithName("heap")
                if not heap.IsValid():
                    self.length = 0
                    return

                ptr_wrapper = heap.GetChildMemberWithName("__0")
                if not ptr_wrapper.IsValid():
                    self.length = 0
                    return

                pointer = ptr_wrapper.GetChildMemberWithName("pointer")
                if not pointer.IsValid():
                    self.length = 0
                    return

                self.heap_ptr = pointer.GetValueAsUnsigned()
                if self.heap_ptr == 0:
                    self.length = 0
                    return
            else:
                # Get inline storage address
                # Navigate to the inline array: raw.inline.value.value.value
                inline = raw.GetChildMemberWithName("inline")
                if not inline.IsValid():
                    self.length = 0
                    return

                value1 = inline.GetChildMemberWithName("value")
                if not value1.IsValid():
                    self.length = 0
                    return

                value2 = value1.GetChildMemberWithName("value")
                if not value2.IsValid():
                    self.length = 0
                    return

                value_array = value2.GetChildMemberWithName("value")
                if not value_array.IsValid():
                    self.length = 0
                    return

                # Get the address of the inline array
                self.inline_data_address = value_array.GetLoadAddress()
                if self.inline_data_address == 0:
                    self.length = 0
                    return

        except Exception as e:
            self.length = 0
            self.is_heap = False
            self.heap_ptr = 0
            self.inline_data_address = 0

    def has_children(self):
        return self.length > 0


def __lldb_init_module(debugger: lldb.SBDebugger, _internal_dict):
    """
    This function is called by LLDB when the module is loaded.
    It registers all the type summaries and synthetic providers.
    """
    # Get or create the "rust" category
    # The Rust toolchain already creates this category, so we'll add to it
    category_name = "rust"
    category = debugger.GetCategory(category_name)

    if not category.IsValid():
        # If for some reason the category doesn't exist, create it
        category = debugger.CreateCategory(category_name)
        category.SetEnabled(True)

    # Register SmolStr summary provider
    summary_options = lldb.SBTypeNameSpecifier(
        "smol_str::SmolStr", lldb.eFormatterMatchExact
    )
    summary = lldb.SBTypeSummary.CreateWithFunctionName(
        "rust_bonus_types.SmolStrSummaryProvider"
    )
    summary.SetOptions(lldb.eTypeOptionCascade)
    category.AddTypeSummary(summary_options, summary)

    # Register SmolStr synthetic provider
    synth_options = lldb.SBTypeNameSpecifier(
        "smol_str::SmolStr", lldb.eFormatterMatchExact
    )
    synth = lldb.SBTypeSynthetic.CreateWithClassName(
        "rust_bonus_types.SmolStrSyntheticProvider"
    )
    synth.SetOptions(lldb.eTypeOptionCascade)
    category.AddTypeSynthetic(synth_options, synth)

    # Register SmallVec summary provider
    summary_options = lldb.SBTypeNameSpecifier(
        "^smallvec::SmallVec<.+>$", lldb.eFormatterMatchRegex
    )
    summary = lldb.SBTypeSummary.CreateWithFunctionName(
        "rust_bonus_types.SmallVecSummaryProvider"
    )
    summary.SetOptions(lldb.eTypeOptionCascade)
    category.AddTypeSummary(summary_options, summary)

    # Register SmallVec synthetic provider
    synth_options = lldb.SBTypeNameSpecifier(
        "^smallvec::SmallVec<.+>$", lldb.eFormatterMatchRegex
    )
    synth = lldb.SBTypeSynthetic.CreateWithClassName(
        "rust_bonus_types.SmallVecSyntheticProvider"
    )
    synth.SetOptions(lldb.eTypeOptionCascade)
    category.AddTypeSynthetic(synth_options, synth)

    print("✓ Rust bonus types loaded: SmolStr, SmallVec")
