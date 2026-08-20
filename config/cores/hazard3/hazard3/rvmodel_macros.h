#ifndef _RVMODEL_MACROS_H
#define _RVMODEL_MACROS_H

// Hazard3 testbench (tb_cxxrtl) memory-mapped IO, from tb_constants.h:
//   IO_BASE  = 0xc0000000
//   IO_EXIT  = IO_BASE + 0x008  (write triggers sim exit; value is exit code)
//   IO_PRINT_CHAR = IO_BASE + 0x000
//   IO_MTIME     = IO_BASE + 0x100
//   IO_MTIMECMP0 = IO_BASE + 0x108
//
// The signature is captured from memory by the testbench, so the macros below
// are deliberately minimal stubs.

// Hazard3 has a standard (conforming) M-mode with normal trap handling.
#define STANDARD_SM_SUPPORTED

#define RVMODEL_DATA_SECTION

##### STARTUP #####

// Hazard3 resets to RESET_VECTOR = 0x80000040 (rvtest_entry_point), but its
// reset mtvec is 0x80000000 (MTVEC_INIT). Emit a 64-byte stub at 0x80000000
// so the flat binary loaded at RAM_ORIGIN has the entry point at offset 0x40,
// and a stray trap before the test installs mtvec reports a failure instead
// of executing garbage.
#define RVMODEL_BOOT \
  .pushsection .text.boot, "ax"   ;\
  .p2align 6                      ;\
  lui a0, 0xc0000                 ;\
  li a1, -1                       ;\
  sw a1, 8(a0)                    ;\
1:                                ;\
  j 1b                            ;\
  .p2align 6                      ;\
  .popsection                     ;

##### TERMINATION #####

// Write 0 (pass) / 1 (fail) to IO_EXIT and spin. The testbench detects the
// write and terminates simulation.
#define RVMODEL_HALT_PASS                 \
  lui x1, 0xc0000                         ;\
  sw zero, 8(x1)                          ;\
1:                                        ;\
  j 1b                                    ;

#define RVMODEL_HALT_FAIL                 \
  lui x1, 0xc0000                         ;\
  li x2, 1                                ;\
  sw x2, 8(x1)                            ;\
1:                                        ;\
  j 1b                                    ;

##### IO #####

#define RVMODEL_IO_INIT(_R1, _R2, _R3)

#define RVMODEL_IO_WRITE_STR(_R1, _R2, _R3, _STR_PTR)

##### Access Fault #####

#define RVMODEL_ACCESS_FAULT_ADDRESS 0x00000000

##### Interrupt Latency #####

#define RVMODEL_INTERRUPT_LATENCY 10

#define RVMODEL_TIMER_INT_SOON_DELAY 100

##### Machine Timer #####

#define RVMODEL_MTIME_ADDRESS  0xc0000100
#define RVMODEL_MTIMECMP_ADDRESS 0xc0000108

##### Machine Interrupts #####

#define RVMODEL_SET_MSW_INT(_R1, _R2)
#define RVMODEL_CLR_MSW_INT(_R1, _R2)
#define RVMODEL_SET_MEXT_INT(_R1, _R2)
#define RVMODEL_CLR_MEXT_INT(_R1, _R2)

##### Supervisor Interrupts #####

#define RVMODEL_SET_SEXT_INT(_R1, _R2)
#define RVMODEL_CLR_SEXT_INT(_R1, _R2)
#define RVMODEL_SET_SSW_INT(_R1, _R2)
#define RVMODEL_CLR_SSW_INT(_R1, _R2)

#endif // _RVMODEL_MACROS_H
