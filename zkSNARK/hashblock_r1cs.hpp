#ifndef R1CS_EXAMPLES_HPP_
#define R1CS_EXAMPLES_HPP_

#include <libsnark/relations/constraint_satisfaction_problems/r1cs/r1cs.hpp>

namespace libsnark {

    template<typename FieldT>
    struct hashblock_r1cs {
        r1cs_constraint_system<FieldT> constraint_system;
        r1cs_primary_input<FieldT> primary_input;
        r1cs_auxiliary_input<FieldT> auxiliary_input;

        hashblock_r1cs<FieldT>() = default;
        hashblock_r1cs<FieldT>(const hashblock_r1cs<FieldT> &other) = default;
        hashblock_r1cs<FieldT>(const r1cs_constraint_system<FieldT> &constraint_system,
                            const r1cs_primary_input<FieldT> &primary_input,
                            const r1cs_auxiliary_input<FieldT> &auxiliary_input) :
            constraint_system(constraint_system),
            primary_input(primary_input),
            auxiliary_input(auxiliary_input)
        {};
        hashblock_r1cs<FieldT>(r1cs_constraint_system<FieldT> &&constraint_system,
                            r1cs_primary_input<FieldT> &&primary_input,
                            r1cs_auxiliary_input<FieldT> &&auxiliary_input) :
            constraint_system(std::move(constraint_system)),
            primary_input(std::move(primary_input)),
            auxiliary_input(std::move(auxiliary_input))
        {};
    };

    template<typename FieldT>
    hashblock_r1cs<FieldT> generate_hashblock_r1cs();

} // libsnark

#include <hashblock_r1cs.tcc>

#endif // R1CS_EXAMPLES_HPP_
