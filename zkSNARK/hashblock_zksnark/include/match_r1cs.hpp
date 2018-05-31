#ifndef MATCH_R1CS_HPP_
#define MATCH_R1CS_HPP_

#include <libsnark/relations/constraint_satisfaction_problems/r1cs/r1cs.hpp>

namespace libsnark {

    template<typename FieldT>
    struct match_r1cs {
        r1cs_constraint_system<FieldT> constraint_system;
        r1cs_primary_input<FieldT> primary_input;
        r1cs_auxiliary_input<FieldT> auxiliary_input;

        match_r1cs<FieldT>() = default;
        match_r1cs<FieldT>(const match_r1cs<FieldT> &other) = default;
        match_r1cs<FieldT>(const r1cs_constraint_system<FieldT> &constraint_system,
                            const r1cs_primary_input<FieldT> &primary_input,
                            const r1cs_auxiliary_input<FieldT> &auxiliary_input) :
            constraint_system(constraint_system),
            primary_input(primary_input),
            auxiliary_input(auxiliary_input)
        {};
        match_r1cs<FieldT>(r1cs_constraint_system<FieldT> &&constraint_system,
                            r1cs_primary_input<FieldT> &&primary_input,
                            r1cs_auxiliary_input<FieldT> &&auxiliary_input) :
            constraint_system(std::move(constraint_system)),
            primary_input(std::move(primary_input)),
            auxiliary_input(std::move(auxiliary_input))
        {};
    };

    template<typename FieldT>
    match_r1cs<FieldT> generate_match_r1cs(
        const int _i_0,
        const int _n_0,
        const int _d_0,
        const int _r_0,
        const int _i_1,
        const int _n_1,
        const int _d_1,
        const int _r_1,
        const int _i_2,
        const int _n_2,
        const int _d_2,
        const int _r_2
    );

} // libsnark

#include "match_r1cs.tcc"

#endif // MATCH_R1CS_HPP_
