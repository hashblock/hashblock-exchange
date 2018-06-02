/*
# Copyright 2018 Frank V. Castellucci and Arthur Greef
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
*/

#ifndef _HBUTILS_HPP
#define _HBUTILS_HPP

#include <libff/common/profiling.hpp>
#include <libsnark/common/default_types/r1cs_ppzksnark_pp.hpp>
#include <libsnark/zk_proof_systems/ppzksnark/r1cs_ppzksnark/r1cs_ppzksnark.hpp>
#include <match_r1cs.hpp>

namespace hbutil {
	extern const std::string VERIFY_KEYNAME;
	extern const std::string PROOVE_KEYNAME;
}

std::vector<int> extract_ints(std::string const&);

#endif /* _HBUTILS_HPP */