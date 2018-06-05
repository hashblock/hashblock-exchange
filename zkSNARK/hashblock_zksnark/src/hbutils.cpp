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

#include <fstream>
#include <vector>
#include <regex>


using namespace std;

namespace hbutil {
	extern const string VERIFY_KEYNAME("hashblock_zkSNARK.vk");
	extern const string PROOVE_KEYNAME("hashblock_zkSNARK.pk");
}

static const regex INT_TYPE("[+-]?[0-9]+");
int toInt(const string& sval)
{
    int val;
    if(std::regex_match(sval, INT_TYPE))
        val = atoi(sval.c_str());
    else
        throw invalid_argument("Not valid integer: " + sval);
    return val;
}

vector<int> extract_ints(string const& input_str)  {
    size_t num_inputs = 12;
    vector<int> ints;
    istringstream input(input_str);

    string number;
    while (getline(input, number, ',')) {
        int i = toInt(number);
        ints.push_back(i);
    }
    if(ints.size() != num_inputs)
        throw invalid_argument("12 comma separated integers required, got: "
            + input_str);

    return ints;
}


