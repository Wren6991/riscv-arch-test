#ifndef _RVMODEL_MACROS_H
#define _RVMODEL_MACROS_H

#define IO_BASE 0xc0000000
#define IO_PRINT_CHAR (IO_BASE + 0x0)
#define IO_PRINT_U32  (IO_BASE + 0x4)
#define IO_EXIT       (IO_BASE + 0x8)

// Hazard3 has a conforming M-mode with trap handling.
#define STANDARD_SM_SUPPORTED

#define RVMODEL_DATA_SECTION

// Empty default vector table: reset vector is straight after.
#define RVMODEL_BOOT \
  .pushsection .text.boot, "ax"   ;\
  .p2align 6                      ;\
  /* shouldn't be here */         ;\
  li a0, IO_EXIT                  ;\
  li a1, -1                       ;\
  sw a1, (a0)                     ;\
1:                                ;\
  j 1b                            ;\
  .p2align 6                      ;\
  .popsection                     ;

// Writing to IO_EXIT terminates the simulation and, if the --cpuret flag was
// passed to the tb invocation, also propagates the return code.
#define RVMODEL_HALT_PASS                 \
  li a0, IO_EXIT                          ;\
  li a1, 0                                ;\
  sw a1, (a0)                             ;\
1:                                        ;\
  j 1b                                    ;

#define RVMODEL_HALT_FAIL                 \
  li a0, IO_EXIT                          ;\
  li a1, 1                                ;\
  sw a1, (a0)                             ;\
1:                                        ;\
  j 1b                                    ;

##### IO #####

// Nothing to do: tb IO is stateless.
#define RVMODEL_IO_INIT(_R1, _R2, _R3)


#define RVMODEL_IO_WRITE_STR(_R1, _R2, _R3, _STR_PTR) \
  li _R1, IO_PRINT_CHAR      ;\
  j 2f                       ;\
1:                           ;\
  sb _R2, (_R1)              ;\
  addi _STR_PTR, _STR_PTR, 1 ;\
2:                           ;\
  lbu _R2, (_STR_PTR)        ;\
  bnez _R2, 1b               ;

##### Access Fault #####

#define RVMODEL_ACCESS_FAULT_ADDRESS 0x00000000

##### Interrupt Latency #####

#define RVMODEL_INTERRUPT_LATENCY 3

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
