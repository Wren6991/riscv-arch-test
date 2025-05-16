#ifndef _COMPLIANCE_MODEL_H
#define _COMPLIANCE_MODEL_H
#if XLEN == 64
  #define ALIGNMENT 3
#else
  #define ALIGNMENT 2
#endif

#define RVMODEL_DATA_SECTION \
        .align 8; .global begin_regstate; begin_regstate:               \
        .word 128;                                                      \
        .align 8; .global end_regstate; end_regstate:                   \
        .word 4;

#define RVMODEL_HALT      ;\
__test_exit:              ;\
lui a0, 0x80000000 >> 12  ;\
li a1, 0                  ;\
sw a1, 8(a0)              ;\
1:                        ;\
  j 1b                    ;\

#define RVMODEL_BOOT \
.pushsection .text.init         ;\
  j __default_trap_handler      ;\
.p2align 6                      ;\
  j _start                      ;\
.global __default_trap_handler  ;\
__default_trap_handler:         ;\
lui a0, 0x80000000 >> 12        ;\
li a1, -1                       ;\
sw a1, 8(a0)                    ;\
1:                              ;\
  j 1b                          ;\
.popsection                     ;\
.global _start                  ;\
_start:                         ;\


//RV_COMPLIANCE_DATA_BEGIN
#define RVMODEL_DATA_BEGIN                                              \
  RVMODEL_DATA_SECTION                                                        \
  .pushsection .test_signature, "a" ; \
  .align ALIGNMENT;\
  .global begin_signature; begin_signature:

//RV_COMPLIANCE_DATA_END
#define RVMODEL_DATA_END                                                      \
  .global end_signature; end_signature: ; \
  .popsection

//RVTEST_IO_INIT
#define RVMODEL_IO_INIT
//RVTEST_IO_WRITE_STR
#define RVMODEL_IO_WRITE_STR(_R, _STR)
//RVTEST_IO_CHECK
#define RVMODEL_IO_CHECK()
//RVTEST_IO_ASSERT_GPR_EQ
#define RVMODEL_IO_ASSERT_GPR_EQ(_S, _R, _I)
//RVTEST_IO_ASSERT_SFPR_EQ
#define RVMODEL_IO_ASSERT_SFPR_EQ(_F, _R, _I)
//RVTEST_IO_ASSERT_DFPR_EQ
#define RVMODEL_IO_ASSERT_DFPR_EQ(_D, _R, _I)

#define RVMODEL_SET_MSW_INT

#define RVMODEL_CLEAR_MSW_INT

#define RVMODEL_CLEAR_MTIMER_INT

#define RVMODEL_CLEAR_MEXT_INT


#endif // _COMPLIANCE_MODEL_H
