

#include <stdio.h>
#include <stdlib.h>
#include <secp256k1_generator.h>
#include <secp256k1_rangeproof.h>


#ifdef DETERMINISTIC
#define TEST_FAILURE(msg) do { \
    fprintf(stderr, "%s\n", msg); \
    abort(); \
} while(0);
#else
#define TEST_FAILURE(msg) do { \
    fprintf(stderr, "%s:%d: %s\n", __FILE__, __LINE__, msg); \
    abort(); \
} while(0)
#endif

#ifdef HAVE_BUILTIN_EXPECT
#define EXPECT(x,c) __builtin_expect((x),(c))
#else
#define EXPECT(x,c) (x)
#endif

#ifdef DETERMINISTIC
#define CHECK(cond) do { \
    if (EXPECT(!(cond), 0)) { \
        TEST_FAILURE("test condition failed"); \
    } \
} while(0)
#else
#define CHECK(cond) do { \
    if (EXPECT(!(cond), 0)) { \
        TEST_FAILURE("test condition failed: " #cond); \
    } \
} while(0)
#endif

static void counting_illegal_callback_fn(const char* str, void* data) {
    /* Dummy callback function that just counts. */
    int32_t *p;
    printf("CICFN: %s\n", str );
    //(void)str;
    p = data;
    (*p)++;
}

typedef struct {

	//	Penderson commit vars and outcomes
	secp256k1_context 				*none_ctx;
	secp256k1_context 				*sign_ctx;
	secp256k1_context 				*verify_ctx;
	secp256k1_context 				*both_ctx;
	uint64_t 						value;
	unsigned char 					*blind_ptr;
	secp256k1_pedersen_commitment	commitment;

	//	Range proof vars and outcomes
	unsigned char 					*message_ptr;
	uint64_t 						message_len;
	uint64_t 						min_value;
	unsigned char 					*nonce;
	int 							exponent; // fixed 0 for most private
	int 							min_bits; // fixed 0 for auto
	unsigned char 					*extra_commit; // Fixed NULL for now
	size_t 							extra_commit_len; // fixed 0 for no extra
	size_t 							proof_len; // In buffer size, out length in buffer proof
	unsigned char 					proof[5134+1];

	//	Range proof verifies
	int 							mantissa;
	uint64_t 						verify_min;
	uint64_t 						verify_max;

} zkproof;

int create_commitment(zkproof *zkp) {
	int commit_res = secp256k1_pedersen_commit(
		zkp->both_ctx,
		&zkp->commitment,
		zkp->blind_ptr,
		zkp->value,
		&secp256k1_generator_const_g,
		&secp256k1_generator_const_h);
	return commit_res;
}

int create_proof(zkproof *zkp) {
	int proof_res = secp256k1_rangeproof_sign(
		zkp->both_ctx, 		//	Needs to be context that has both signing and verifying
		zkp->proof,
		&zkp->proof_len,
		zkp->min_value,
		&zkp->commitment,
		zkp->blind_ptr,
		zkp->nonce,
		zkp->exponent,
		zkp->min_bits,
		zkp->value,
		zkp->message_ptr,
		zkp->message_len,
		zkp->extra_commit,
		zkp->extra_commit_len,
		&secp256k1_generator_const_h);
	return proof_res;
}

int verify_proof(zkproof *zkp) {
	int verify_res = secp256k1_rangeproof_verify(
		zkp->both_ctx,
		&zkp->verify_min,
		&zkp->verify_max,
		&zkp->commitment,
		zkp->proof,
		zkp->proof_len,
		zkp->extra_commit,
		zkp->extra_commit_len,
		&secp256k1_generator_const_h);
	return verify_res;
}

int range_info(zkproof *zkp) {
	int info_res = secp256k1_rangeproof_info(
		zkp->none_ctx,
		&zkp->exponent,
		&zkp->mantissa,
		&zkp->verify_min,
		&zkp->verify_max,
		zkp->proof,
		zkp->proof_len);
	return info_res;
}

int main( int c , char *argv[]) {
	(void)c;
	(void)argv;
	zkproof 	test;
	test.none_ctx = secp256k1_context_create(SECP256K1_CONTEXT_NONE);
	test.sign_ctx = secp256k1_context_create(SECP256K1_CONTEXT_SIGN);
	test.verify_ctx = secp256k1_context_create(SECP256K1_CONTEXT_VERIFY);
    test.both_ctx = secp256k1_context_create(SECP256K1_CONTEXT_SIGN | SECP256K1_CONTEXT_VERIFY);
	int32_t ecount=0;

	secp256k1_context_set_error_callback(test.none_ctx, counting_illegal_callback_fn, &ecount);
	secp256k1_context_set_error_callback(test.sign_ctx, counting_illegal_callback_fn, &ecount);
	secp256k1_context_set_error_callback(test.verify_ctx, counting_illegal_callback_fn, &ecount);
	secp256k1_context_set_error_callback(test.both_ctx, counting_illegal_callback_fn, &ecount);
	secp256k1_context_set_illegal_callback(test.none_ctx, counting_illegal_callback_fn, &ecount);
    secp256k1_context_set_illegal_callback(test.sign_ctx, counting_illegal_callback_fn, &ecount);
    secp256k1_context_set_illegal_callback(test.verify_ctx, counting_illegal_callback_fn, &ecount);
    secp256k1_context_set_illegal_callback(test.both_ctx, counting_illegal_callback_fn, &ecount);

    const unsigned char blind[32];
    test.blind_ptr = blind;
    test.value = 65;

    // Create a signed commitment for value N
    int cresult = create_commitment(&test);
    printf("Commitment result = %i\nCommitment = ", cresult);
    for(uint64_t i=0; i < sizeof(test.commitment.data); i++)
    	printf("%x", test.commitment.data[i]);
    //printf("Commitment buffer = %s\n", test.commitment.data);
    printf("\nCommitment ecount = %i\n\n", ecount);

    unsigned char message[120] = "When I see my own likeness in the depths of someone else's consciousness,  I always experience a moment of panic.";
    test.message_ptr = message;
    test.message_len = sizeof(message);
    test.nonce = test.commitment.data;
    test.min_value = 30;
    test.min_bits = 8;
    test.exponent = 0;
    test.extra_commit = NULL;
    test.extra_commit_len = 0;
    test.proof_len = sizeof(test.proof);

    // Create a signed proof
    int presult = create_proof(&test);
    printf("Proof result = %i\n", presult);
    printf("Proof buffer size = %u\nProof = ", test.proof_len);
    for(uint64_t i=0; i < test.proof_len; i++)
    	printf("%x", test.proof[i]);
    printf("\nProof ecount = %i\n\n", ecount);

    //	Verify signed proof
    test.verify_min = test.verify_max = 0;

    int vresult = verify_proof(&test);
    printf("Verify result = %i\n", vresult);
    printf("Verify value = %i\n", test.value);
    printf("Verify min value = %i\n", test.verify_min);
    printf("Verify max value = %i\n", test.verify_max);
    printf("Verify ecount = %i\n\n", ecount);


    //	Some information
    test.verify_min = test.verify_max = 0;
    int iresult = range_info(&test);
    printf("Info result = %i\n", iresult);
    printf("Info value = %i\n", test.value);
    printf("Info exponent = %i\n", test.exponent);
    printf("Info mantissa = %i\n", test.mantissa);
    printf("Info min value = %i\n", test.verify_min);
    printf("Info max value = %i\n", test.verify_max);
    printf("Info ecount = %i\n\n", ecount);

    // Destroy these contexts
   	secp256k1_context_destroy(test.none_ctx);
    secp256k1_context_destroy(test.sign_ctx);
    secp256k1_context_destroy(test.verify_ctx);
    secp256k1_context_destroy(test.both_ctx);

	return 0;
}