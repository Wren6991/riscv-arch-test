// RISC-V Compliance Test Header File
// Copyright (c) 2017, Codasip Ltd. All Rights Reserved.
// See LICENSE for license details.
//
// Description: Common header file for RV32I tests

#ifndef _HAZARD3_MODEL_TEST_H
#define _HAZARD3_MODEL_TEST_H

#include "riscv_test.h"

//-----------------------------------------------------------------------
// RV Compliance Macros
//-----------------------------------------------------------------------

// Hazard3 testbench IO defines
#define IO_BASE 0x80000000
#define IO_PRINT_CHAR  (IO_BASE + 0x000)
#define IO_PRINT_U32   (IO_BASE + 0x004)
#define IO_EXIT        (IO_BASE + 0x008)
#define IO_SET_SOFTIRQ (IO_BASE + 0x010)
#define IO_CLR_SOFTIRQ (IO_BASE + 0x014)

// Just kill the sim, software environment is unimportant now that the
// signature has been written into memory. The tb will dump the signature
// section for comparison.
#define RVMODEL_HALT                                                   \
        li a0, IO_EXIT                                               ; \
        li a1, 0                                                     ; \
        sw a1, (a0)                                                  ; \

#define RV_COMPLIANCE_RV32M                                            \
        RVTEST_RV32M                                                   \

#define RV_COMPLIANCE_CODE_BEGIN                                       \
        RVTEST_CODE_BEGIN_OLD                                          \

#define RV_COMPLIANCE_CODE_END                                         \
        RVMODEL_HALT                                                   \

#define RVMODEL_DATA_BEGIN                                             \
        .section .testdata, "aw";                                      \
        RVTEST_DATA_BEGIN_OLD                                          \

#define RVMODEL_DATA_END                                               \
        RVTEST_DATA_END_OLD                                            \

// TODO defining these as empty macros to shut up the warning -- not clear how
// they should be implemented as we need registers to to a store, and no
// documentation of which registers we may use
#define RVMODEL_SET_MSW_INT
#define RVMODEL_CLEAR_MSW_INT
#define RVMODEL_CLEAR_MTIMER_INT
#define RVMODEL_CLEAR_MEXT_INT


#endif
// RISC-V Compliance IO Test Header File

/*
 * Copyright (c) 2005-2018 Imperas Software Ltd., www.imperas.com
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
 * either express or implied.
 *
 * See the License for the specific language governing permissions and
 * limitations under the License.
 *
 */

#ifndef _COMPLIANCE_IO_H
#define _COMPLIANCE_IO_H

//-----------------------------------------------------------------------
// RV IO Macros (Non-functional)
//-----------------------------------------------------------------------

#define RVTEST_IO_INIT
#define RVMODEL_IO_WRITE_STR(_SP, _STR)
#define RVMODEL_IO_CHECK()
#define RVMODEL_IO_ASSERT_GPR_EQ(_SP, _R, _I)
#define RVMODEL_IO_ASSERT_SFPR_EQ(_F, _R, _I)
#define RVMODEL_IO_ASSERT_DFPR_EQ(_D, _R, _I)

#endif // _COMPLIANCE_IO_H
