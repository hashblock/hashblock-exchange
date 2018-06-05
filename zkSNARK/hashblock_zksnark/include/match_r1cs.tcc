#ifndef MATCH_R1CS_TCC__
#define MATCH_R1CS_TCC__

#include <cassert>
#include <stdexcept>
#include <libff/common/utils.hpp>

namespace libsnark {

template<typename FieldT>
match_r1cs<FieldT> generate_match_r1cs(
    // The match equation is Q_i * (Q_n/Q_d) = Q_r
    // Q = quantity, i = initiate, r = reciprocate, n = reciprocate ratio numerator, d = reciprocate ratio denominator
    // When expanded this is v_i * (v_n/v_d) = v_r && u_i * (u_n/u_d) = u_r && r_i * (r_n/r_d) = r_r
    // Where v = quantity value, u = asset unit, r = asset resource
    const int v_i,
    const int v_n,
    const int v_d,
    const int v_r,
    const int u_i,
    const int u_n,
    const int u_d,
    const int u_r,
    const int r_i,
    const int r_n,
    const int r_d,
    const int r_r)
{
    const size_t num_constraints = 14;
    const size_t num_inputs = 13;

    // libff::enter_block("Call to generate_hashblock_r1cs_example_with_field_input");

    assert(num_inputs <= num_constraints + 2);

    r1cs_constraint_system<FieldT> cs;
    cs.primary_input_size = num_inputs;
    cs.auxiliary_input_size = 13;

    r1cs_variable_assignment<FieldT> full_variable_assignment;
    FieldT i_0 = FieldT(v_i);
    FieldT n_0 = FieldT(v_n);
    FieldT d_0 = FieldT(v_d);
    FieldT r_0 = FieldT(v_r);

    FieldT i_1 = FieldT(u_i);
    FieldT n_1 = FieldT(u_n);
    FieldT d_1 = FieldT(u_d);
    FieldT r_1 = FieldT(u_r);

    FieldT i_2 = FieldT(r_i);
    FieldT n_2 = FieldT(r_n);
    FieldT d_2 = FieldT(r_d);
    FieldT r_2 = FieldT(r_r);

    FieldT out = FieldT::one();

    full_variable_assignment.push_back(i_0);
    full_variable_assignment.push_back(n_0);
    full_variable_assignment.push_back(d_0);
    full_variable_assignment.push_back(r_0);

    full_variable_assignment.push_back(i_1);
    full_variable_assignment.push_back(n_1);
    full_variable_assignment.push_back(d_1);
    full_variable_assignment.push_back(r_1);

    full_variable_assignment.push_back(i_2);
    full_variable_assignment.push_back(n_2);
    full_variable_assignment.push_back(d_2);
    full_variable_assignment.push_back(r_2);

    full_variable_assignment.push_back(out);

    size_t i = 1;

    size_t i_0_i = i++;
    size_t n_0_i = i++;
    size_t d_0_i = i++;
    size_t r_0_i = i++;

    size_t i_1_i = i++;
    size_t n_1_i = i++;
    size_t d_1_i = i++;
    size_t r_1_i = i++;

    size_t i_2_i = i++;
    size_t n_2_i = i++;
    size_t d_2_i = i++;
    size_t r_2_i = i++;

    size_t out_i = i++;

    // i_0 * n_0 = in_0
    linear_combination<FieldT> A_0, B_0, C_0;
    A_0.add_term(i_0_i, 1);
    B_0.add_term(n_0_i, 1);
    size_t in_0_i = i++;
    C_0.add_term(in_0_i, 1);
    FieldT in_0 = i_0 * n_0;
    full_variable_assignment.push_back(in_0);
    cs.add_constraint(r1cs_constraint<FieldT>(A_0, B_0, C_0));

    // d_0 * r_0 = dr_0
    linear_combination<FieldT> A_1, B_1, C_1;
    A_1.add_term(d_0_i, 1);
    B_1.add_term(r_0_i, 1);
    size_t dr_0_i = i++;
    C_1.add_term(dr_0_i, 1);
    FieldT dr_0 = d_0 * r_0;
    full_variable_assignment.push_back(dr_0);
    cs.add_constraint(r1cs_constraint<FieldT>(A_1, B_1, C_1));

    // in_0 - dr_0 = indr_0
    linear_combination<FieldT> A_2, B_2, C_2;
    B_2.add_term(0, 1);
    A_2.add_term(in_0_i, 1);
    A_2.add_term(dr_0_i, -1);
    size_t indr_0_i = i++;
    C_2.add_term(indr_0_i, 1);
    FieldT indr_0 = in_0 - dr_0;
    full_variable_assignment.push_back(indr_0);
    cs.add_constraint(r1cs_constraint<FieldT>(A_2, B_2, C_2));

    // indr_0 + 1 = s_0
    linear_combination<FieldT> A_3, B_3, C_3;
    B_3.add_term(0, 1);
    A_3.add_term(indr_0_i, 1);
    A_3.add_term(0, 1);
    size_t s_0_i = i++;
    C_3.add_term(s_0_i, 1);
    FieldT s_0 = indr_0 + 1;
    full_variable_assignment.push_back(s_0);
    cs.add_constraint(r1cs_constraint<FieldT>(A_3, B_3, C_3));

    // =======

    // i_1 * n_1 = in_1
    linear_combination<FieldT> A_4, B_4, C_4;
    A_4.add_term(i_1_i, 1);
    B_4.add_term(n_1_i, 1);
    size_t in_1_i = i++;
    C_4.add_term(in_1_i, 1);
    FieldT in_1 = i_1 * n_1;
    full_variable_assignment.push_back(in_1);
    cs.add_constraint(r1cs_constraint<FieldT>(A_4, B_4, C_4));

    // d_1 * r_1 = dr_1
    linear_combination<FieldT> A_5, B_5, C_5;
    A_5.add_term(d_1_i, 1);
    B_5.add_term(r_1_i, 1);
    size_t dr_1_i = i++;
    C_5.add_term(dr_1_i, 1);
    FieldT dr_1 = d_1 * r_1;
    full_variable_assignment.push_back(dr_1);
    cs.add_constraint(r1cs_constraint<FieldT>(A_5, B_5, C_5));

    // in_1 - dr_1 = indr_1
    linear_combination<FieldT> A_6, B_6, C_6;
    B_6.add_term(0, 1);
    A_6.add_term(in_1_i, 1);
    A_6.add_term(dr_1_i, -1);
    size_t indr_1_i = i++;
    C_6.add_term(indr_1_i, 1);
    FieldT indr_1 = in_1 - dr_1;
    full_variable_assignment.push_back(indr_1);
    cs.add_constraint(r1cs_constraint<FieldT>(A_6, B_6, C_6));

    // indr_1 + 1 = s_1
    linear_combination<FieldT> A_7, B_7, C_7;
    B_7.add_term(0, 1);
    A_7.add_term(indr_1_i, 1);
    A_7.add_term(0, 1);
    size_t s_1_i = i++;
    C_7.add_term(s_1_i, 1);
    FieldT s_1 = indr_1 + 1;
    full_variable_assignment.push_back(s_1);
    cs.add_constraint(r1cs_constraint<FieldT>(A_7, B_7, C_7));

    // ===

    // i_2 * n_2 = in_2
    linear_combination<FieldT> A_8, B_8, C_8;
    A_8.add_term(i_2_i, 1);
    B_8.add_term(n_2_i, 1);
    size_t in_2_i = i++;
    C_8.add_term(in_2_i, 1);
    FieldT in_2 = i_2 * n_2;
    full_variable_assignment.push_back(in_2);
    cs.add_constraint(r1cs_constraint<FieldT>(A_8, B_8, C_8));

    // d_2 * r_2 = dr_2
    linear_combination<FieldT> A_9, B_9, C_9;
    A_9.add_term(d_2_i, 1);
    B_9.add_term(r_2_i, 1);
    size_t dr_2_i = i++;
    C_9.add_term(dr_2_i, 1);
    FieldT dr_2 = d_2 * r_2;
    full_variable_assignment.push_back(dr_2);
    cs.add_constraint(r1cs_constraint<FieldT>(A_9, B_9, C_9));

    // in_2 - dr_2 = indr_2
    linear_combination<FieldT> A_10, B_10, C_10;
    B_10.add_term(0, 1);
    A_10.add_term(in_2_i, 1);
    A_10.add_term(dr_2_i, -1);
    size_t indr_2_i = i++;
    C_10.add_term(indr_2_i, 1);
    FieldT indr_2 = in_2 - dr_2;
    full_variable_assignment.push_back(indr_2);
    cs.add_constraint(r1cs_constraint<FieldT>(A_10, B_10, C_10));

    // indr_2 + 1 = s_2
    linear_combination<FieldT> A_11, B_11, C_11;
    B_11.add_term(0, 1);
    A_11.add_term(indr_2_i, 1);
    A_11.add_term(0, 1);
    size_t s_2_i = i++;
    C_11.add_term(s_2_i, 1);
    FieldT s_2 = indr_2 + 1;
    full_variable_assignment.push_back(s_2);
    cs.add_constraint(r1cs_constraint<FieldT>(A_11, B_11, C_11));

    // ===

    // s_0 * s_1 = ss
    linear_combination<FieldT> A_12, B_12, C_12;
    A_12.add_term(s_0_i, 1);
    B_12.add_term(s_1_i, 1);
    size_t ss_i = i++;
    C_12.add_term(ss_i, 1);
    FieldT ss = s_0 * s_1;
    full_variable_assignment.push_back(ss);
    cs.add_constraint(r1cs_constraint<FieldT>(A_12, B_12, C_12));

    // s_2 * ss = out
    linear_combination<FieldT> A_13, B_13, C_13;
    A_13.add_term(s_2_i, 1);
    B_13.add_term(ss_i, 1);
    C_13.add_term(out_i, 1);
    out = s_2 * ss;
    cs.add_constraint(r1cs_constraint<FieldT>(A_13, B_13, C_13));

    /* split variable assignment */
    r1cs_primary_input<FieldT> primary_input(full_variable_assignment.begin(), full_variable_assignment.begin() + num_inputs);
    r1cs_primary_input<FieldT> auxiliary_input(full_variable_assignment.begin() + num_inputs, full_variable_assignment.end());

    /* sanity checks */
    assert(cs.num_variables() == full_variable_assignment.size());
    assert(cs.num_variables() >= num_inputs);
    assert(cs.num_inputs() == num_inputs);
    assert(cs.num_constraints() == num_constraints);
    assert(cs.is_satisfied(primary_input, auxiliary_input));
    // libff::leave_block("Call to generate_hashblock_r1cs_example_with_field_input");
    if (cs.is_satisfied(primary_input, auxiliary_input))
        return match_r1cs<FieldT>(std::move(cs), std::move(primary_input), std::move(auxiliary_input));
    else {
        throw std::invalid_argument("CS not valid");
    }

}

} // libsnark

#endif // MATCH_R1CS_TCC_