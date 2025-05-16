MEMORY
  {
    RAM   (wx) : ORIGIN = 0x00000000, LENGTH = 4M
    RESULT (w) : ORIGIN = ORIGIN(RAM) + LENGTH(RAM), LENGTH = 256k
  }

OUTPUT_FORMAT("elf32-littleriscv", "elf32-littleriscv", "elf32-littleriscv")
OUTPUT_ARCH(riscv)
ENTRY(_start)

SECTIONS
{
  .text : {
    KEEP(*(.text.init .text.init.*))
    *(.text*)
  } > RAM

  .data : {
    *(.data) *(.data.*)
  } > RAM

  .rodata : {
    *(.rodata) *(.rodata.*)
  } > RAM

  .bss : {
    *(.bss)
  } > RAM

  .test_signature : {
    PROVIDE(__testdata_start = .);
    *(.test_signature .test_signature.*)
  } > RESULT

}

